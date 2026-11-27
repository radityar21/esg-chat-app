"""Self-healing supervisor: AgentCore (outer orchestrator) driving Step Functions (inner execution engine).

Flow for one execution:

    start()      sfn:StartExecution on the right state machine, write execution metadata + ledger
    supervise()  poll until the execution is terminal, then
                   SUCCEEDED + esg_report : find every section that failed the 21-rule validation (or was never
                                            generated), regenerate ONLY those with a corrective prompt, re-validate,
                                            and re-assemble the DOCX if anything changed
                   FAILED                 : diagnose from the execution history, restart once if the cause is
                                            transient, otherwise record an explanation for the user
                   SUCCEEDED + ghg        : record the inventory location

Design choices:
  * The correction loop is deterministic Python, not an LLM loop: reproducible, cheap, and unit-tested. The LLM
    is used for routing and for explaining results to the user.
  * Only ``generation`` rules are repaired. Source-data inconsistencies (VAL-NUM-02/06) are escalated, because
    regenerating text cannot fix bad ETL output.
  * At most ``max_correction_attempts`` regenerations per section (default 2) and at most one pipeline restart.
  * Every step is written to the ledger so the UI can show the timeline.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from .aws import AwsGateway, iso, short_id
from .config import Settings
from .diagnose import diagnose
from .ledger import Ledger
from .pipelines import build_input, section_name_to_id, state_machine_for
from .rules import classify

TERMINAL = {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}
GOOD = {"PASS", "WARN"}


class SelfHealingSupervisor:
    def __init__(self, aws: AwsGateway, settings: Settings, sleep: Callable[[float], None] = time.sleep) -> None:
        self.aws = aws
        self.s = settings
        self.ledger = Ledger(aws, settings)
        self.sleep = sleep

    # ── start ──────────────────────────────────────────────────────────────────────────────────
    def start(self, pipeline: str, params: dict[str, Any], *, subsidiary: str = "bank", requested_by: str = "agent",
              auto_heal: bool = True) -> dict[str, Any]:
        sfn_input = build_input(pipeline, params, self.s)
        arn = self.aws.sfn_start(state_machine_for(pipeline, self.s), sfn_input)
        eid = short_id(arn)
        doc = self.ledger.load(arn)
        doc.update({"pipeline": pipeline, "status": "running", "params": {k: v for k, v in sfn_input.items() if k != "section_templates"},
                    "execution_arn": arn, "auto_heal": auto_heal, "subsidiary": subsidiary})
        self.ledger.event(arn, doc, "pipeline_started", f"Started the {pipeline} pipeline for {sfn_input['reporting_year']}.",
                          pipeline=pipeline, framework=sfn_input.get("framework"))
        self.ledger.write_meta(arn, {"pipeline": pipeline, "subsidiary": subsidiary, "requested_by": requested_by, "execution_arn": arn,
                                     "state_machine_arn": state_machine_for(pipeline, self.s),
                                     "started_at": iso(self.aws.now()), "params": doc["params"], "auto_heal": auto_heal})
        return {"execution_id": eid, "execution_arn": arn, "pipeline": pipeline, "auto_heal": auto_heal}

    # ── status ─────────────────────────────────────────────────────────────────────────────────
    def status(self, execution: str) -> dict[str, Any]:
        arn = self._arn(execution)
        d = self.aws.sfn_describe(arn)
        doc = self.ledger.load(arn)
        elapsed = int((d["stopDate"] or self.aws.now()) - (d["startDate"] or self.aws.now()))
        out = {"execution_id": short_id(arn), "sfn_status": d["status"], "elapsed_seconds": elapsed,
               "agent_status": doc["status"], "pipeline": doc.get("pipeline"), "result": doc.get("result"),
               "recent_events": doc["events"][-8:]}
        return out

    # ── supervise ──────────────────────────────────────────────────────────────────────────────
    def supervise(self, execution: str, *, force: bool = False) -> dict[str, Any]:
        arn = self._arn(execution)
        doc = self.ledger.load(arn)
        if doc["status"] in ("completed", "escalated", "failed") and not force:
            return {"state": doc["status"], "already_done": True, "result": doc.get("result"), "execution_id": short_id(arn)}
        if not self.ledger.claim(arn):
            return {"state": "already_supervised", "execution_id": short_id(arn)}
        try:
            return self._supervise_locked(arn)
        finally:
            self.ledger.release(arn)

    def _supervise_locked(self, arn: str) -> dict[str, Any]:
        doc = self.ledger.load(arn)
        d = self._wait(arn, doc)
        if d["status"] not in TERMINAL:
            self.ledger.event(arn, doc, "still_running", "The pipeline is still running; the orchestrator will check again later.")
            return {"state": "running", "execution_id": short_id(arn)}

        pipeline = doc.get("pipeline") or self._pipeline_from(d)
        doc["pipeline"] = pipeline

        if d["status"] != "SUCCEEDED":
            return self._handle_failure(arn, doc, d)

        if pipeline == "esg_report" and doc.get("auto_heal", True):
            return self._heal_report(arn, doc, d)

        doc["status"] = "completed"
        result = {"pipeline": pipeline, "output": d.get("output")}
        if pipeline == "esg_report":
            result.update(self._download_info((d.get("output") or {}).get("assembly_result")))
        doc["result"] = result
        self.ledger.event(arn, doc, "pipeline_succeeded", "The pipeline finished successfully.")
        return {"state": "completed", "execution_id": short_id(arn), "result": result}

    # ── waiting ────────────────────────────────────────────────────────────────────────────────
    def _wait(self, arn: str, doc: dict[str, Any]) -> dict[str, Any]:
        waited = 0
        while True:
            d = self.aws.sfn_describe(arn)
            if d["status"] in TERMINAL or waited >= self.s.max_wait_seconds:
                return d
            self.sleep(self.s.poll_seconds)
            waited += self.s.poll_seconds

    # ── failure path ───────────────────────────────────────────────────────────────────────────
    def _handle_failure(self, arn: str, doc: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        info = diagnose(d, self.aws.sfn_history(arn))
        doc["diagnosis"] = info
        self.ledger.event(arn, doc, "pipeline_failed", f"The pipeline failed in state '{info['failed_state'] or 'unknown'}': {info['error']}.", **info)
        restarts = int(doc.get("restarts", 0))
        if info["retryable"] and restarts < self.s.max_restarts and doc.get("pipeline"):
            new_arn = self.aws.sfn_start(d.get("stateMachineArn") or state_machine_for(doc["pipeline"], self.s), d["input"])
            doc["restarts"] = restarts + 1
            doc["restarted_as"] = short_id(new_arn)
            doc["status"] = "failed"
            self.ledger.event(arn, doc, "pipeline_restarted", "The cause looks transient, so the pipeline was restarted once automatically.",
                              new_execution_id=short_id(new_arn))
            # carry the ledger over so the new execution is supervised with the same context
            new_doc = self.ledger.load(new_arn)
            new_doc.update({"pipeline": doc["pipeline"], "status": "running", "params": doc.get("params"), "execution_arn": new_arn,
                            "auto_heal": doc.get("auto_heal", True), "subsidiary": doc.get("subsidiary", "bank"), "restarts": restarts + 1,
                            "restart_of": short_id(arn)})
            self.ledger.event(new_arn, new_doc, "pipeline_started", f"Restarted automatically after {short_id(arn)} failed.")
            self.ledger.write_meta(new_arn, {"pipeline": doc["pipeline"], "subsidiary": doc.get("subsidiary", "bank"), "restart_of": short_id(arn),
                                             "execution_arn": new_arn})
            return {"state": "restarted", "execution_id": short_id(arn), "new_execution_id": short_id(new_arn), "diagnosis": info}
        doc["status"] = "failed"
        doc["result"] = {"diagnosis": info}
        self.ledger.event(arn, doc, "escalated", "Automatic recovery is not possible for this failure. See the diagnosis for next steps.")
        return {"state": "failed", "execution_id": short_id(arn), "diagnosis": info}

    # ── self-correction path ───────────────────────────────────────────────────────────────────
    def _heal_report(self, arn: str, doc: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
        inp, out = d["input"], d.get("output") or {}
        year = int(inp["reporting_year"])
        metrics = out.get("athena_query_result") or {}
        generated = out.get("generated_sections") or []
        included = list((out.get("filtered_sections") or {}).get("included") or [])

        by_tid: dict[str, dict[str, Any]] = {}
        for e in generated:
            tid = e.get("template_id") or e.get("section_id")
            if tid:
                by_tid[tid] = e

        todo: list[dict[str, Any]] = []
        notes: list[str] = []
        for t in inp.get("section_templates", []):
            tid, fw = t["template_id"], t["framework"]
            full_id = section_name_to_id(fw, tid, year)
            entry = by_tid.get(tid) or next((e for e in generated if e.get("section_id") == full_id), None)
            plan = self._plan_for(entry)
            doc["sections"][tid] = {"status": plan["action"], "section_id": full_id}
            if plan["action"] in ("generate", "repair", "revalidate"):
                todo.append({"tid": tid, "fw": fw, "full_id": full_id, "entry": entry, **plan})
            elif plan["action"] == "escalate_data":
                notes.append(f"{tid}: source data problem")
                doc["sections"][tid]["explanations"] = plan["explanations"]

        total = len(inp.get("section_templates", []))
        self.ledger.event(arn, doc, "validation_review",
                          f"Reviewed {total} sections: {len(todo)} need repair, "
                          f"{sum(1 for v in doc['sections'].values() if v['status'] == 'escalate_data')} have source-data problems, rest are fine.",
                          to_repair=[x["tid"] for x in todo])

        healed, unresolved = [], []
        replaced: dict[str, dict[str, Any]] = {}
        for item in todo:
            res = self._repair_section(arn, doc, inp, metrics, item)
            doc["sections"][item["tid"]].update({k: res[k] for k in ("status", "attempts", "final_outcome")})
            if res["status"] == "healed":
                healed.append(item["tid"])
                replaced[item["tid"]] = res["entry"]
            else:
                unresolved.append({"template_id": item["tid"], "reason": res["status"], "explanations": res.get("explanations", []),
                                   "last_outcome": res.get("final_outcome")})
                if res.get("entry"):
                    replaced[item["tid"]] = res["entry"]  # still better than nothing: newest content

        for u in [v for v in doc["sections"].items() if v[1]["status"] == "escalate_data"]:
            unresolved.append({"template_id": u[0], "reason": "source_data", "explanations": u[1].get("explanations", [])})

        assembly = (out.get("assembly_result") or {})
        if replaced:
            assembly = self._reassemble(arn, doc, inp, included, replaced, by_tid)
        result = {"pipeline": "esg_report", "healed": healed, "unresolved": unresolved, "assembly_result": assembly,
                  "reassembled": bool(replaced), **self._download_info(assembly)}
        doc["result"] = result
        doc["status"] = "escalated" if unresolved else "completed"
        self.ledger.event(arn, doc, "completed" if not unresolved else "escalated",
                          f"Done. {len(healed)} section(s) repaired automatically" + (f", {len(unresolved)} need human attention." if unresolved else "."))
        return {"state": doc["status"], "execution_id": short_id(arn), "result": result}

    def _plan_for(self, entry: dict[str, Any] | None) -> dict[str, Any]:
        if entry is None or entry.get("status") in ("ERROR", "EXCLUDED") or not entry.get("section_result"):
            return {"action": "generate", "cls": None, "explanations": ["The section was not generated."]}
        if entry.get("status") == "INCLUDED":
            return {"action": "ok", "cls": None, "explanations": []}
        val = entry.get("validation_result")
        if not val:
            return {"action": "revalidate", "cls": None, "explanations": ["Validation did not complete for this section."]}
        c = classify(val)
        if c["needs_repair"]:
            return {"action": "repair", "cls": c, "explanations": c["explanations"]}
        if c["data_issues"]:
            return {"action": "escalate_data", "cls": c, "explanations": c["explanations"]}
        return {"action": "ok", "cls": c, "explanations": []}

    def _repair_section(self, arn: str, doc: dict[str, Any], inp: dict[str, Any], metrics: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        tid, fw, full_id = item["tid"], item["fw"], item["full_id"]
        year = int(inp["reporting_year"])
        eid = short_id(arn)
        cls = item.get("cls") or classify(None)
        last_val = (item.get("entry") or {}).get("validation_result")
        last_sr = (item.get("entry") or {}).get("section_result") or {}
        outcome = (last_val or {}).get("validation_outcome")
        explanations = list(item.get("explanations") or [])
        entry: dict[str, Any] | None = None

        if item["action"] == "revalidate" and last_sr.get("content_s3_key"):
            val = self._validate(arn, inp, metrics, fw, last_sr, full_id, retry_count=1)
            outcome = val["validation_outcome"]
            self.ledger.event(arn, doc, "revalidated", f"Re-validated {tid}: {outcome}.", section=tid, outcome=outcome)
            if outcome in GOOD:
                return {"status": "healed", "attempts": 0, "final_outcome": outcome, "entry": self._entry(tid, fw, full_id, last_sr, val)}
            cls = classify(val)
            last_val = val
            explanations = cls["explanations"]
            if not cls["needs_repair"]:
                return {"status": "source_data" if cls["data_issues"] else "unresolved", "attempts": 0, "final_outcome": outcome,
                        "explanations": explanations, "entry": self._entry(tid, fw, full_id, last_sr, val, warn=True)}

        if item["action"] == "generate":
            cls = {"instructions": ["Return one valid JSON object that matches the output contract exactly."], "offending_values": [], "explanations": explanations}

        attempts = 0
        for attempt in range(1, self.s.max_correction_attempts + 1):
            attempts = attempt
            correction = {"attempt": attempt, "instructions": list(cls.get("instructions") or []), "offending_values": cls.get("offending_values") or []}
            first_failed = (last_val or {}).get("errors") or []
            self.ledger.event(arn, doc, "regenerating",
                              f"Regenerating {tid} with a corrected prompt (attempt {attempt}/{self.s.max_correction_attempts}).",
                              section=tid, rules=[e.get("rule") for e in first_failed], attempt=attempt)
            if last_sr.get("content_s3_key") and attempt == 1:
                self._archive(last_sr, eid, full_id)
            try:
                gen = self.aws.lambda_invoke(self.s.section_gen_function, {
                    "section_id": tid, "framework": fw, "reporting_year": year, "metrics_json": metrics,
                    "kb_id": inp.get("kb_id", self.s.kb_id), "execution_id": arn, "correction": correction})
            except Exception as exc:  # noqa: BLE001
                self.ledger.event(arn, doc, "regeneration_error", f"Generation of {tid} failed: {str(exc)[:200]}", section=tid)
                continue
            if not (gen.get("content_s3_key") or gen.get("content_json")):
                self.ledger.event(arn, doc, "regeneration_error", f"The model returned no usable content for {tid}.", section=tid)
                continue
            if gen.get("content_json") and not gen.get("content_s3_key"):
                # inline fallback (S3 write failed in SectionGenFn): persist so validation and assembly can read it
                key = f"sections/{eid}/{full_id}.json"
                self.aws.s3_put_json(self.s.output_bucket, key, gen["content_json"])
                gen.update({"content_s3_key": key, "content_s3_bucket": self.s.output_bucket})
            last_sr = gen
            val = self._validate(arn, inp, metrics, fw, gen, gen.get("section_id", full_id), retry_count=attempt)
            outcome = val["validation_outcome"]
            self.ledger.event(arn, doc, "revalidated", f"{tid} after attempt {attempt}: {outcome}.", section=tid, outcome=outcome,
                              rules=[e.get("rule") for e in val.get("errors", [])])
            entry = self._entry(tid, fw, full_id, gen, val, warn=outcome not in GOOD)
            if outcome in GOOD:
                return {"status": "healed", "attempts": attempt, "final_outcome": outcome, "entry": entry}
            cls = classify(val)
            last_val = val
            explanations = cls["explanations"]
            if not cls["needs_repair"]:  # only data issues left: another regeneration cannot help
                break
        status = "source_data" if (cls.get("data_issues")) else "unresolved"
        return {"status": status, "attempts": attempts, "final_outcome": outcome, "explanations": explanations, "entry": entry}

    # ── helpers ────────────────────────────────────────────────────────────────────────────────
    def _validate(self, arn: str, inp: dict[str, Any], metrics: dict[str, Any], fw: str, gen: dict[str, Any], section_id: str, retry_count: int) -> dict[str, Any]:
        return self.aws.lambda_invoke(self.s.validation_function, {
            "content_s3_key": gen.get("content_s3_key", ""), "content_s3_bucket": gen.get("content_s3_bucket", self.s.output_bucket),
            "source_metrics": metrics, "framework": fw, "section_id": section_id, "execution_id": arn, "retry_count": retry_count})

    def _entry(self, tid: str, fw: str, full_id: str, gen: dict[str, Any], val: dict[str, Any], warn: bool = False) -> dict[str, Any]:
        return {"section_id": gen.get("section_id", full_id), "template_id": tid, "section_result": gen, "validation_result": val,
                "framework": fw, "status": "INCLUDED_WITH_WARNINGS" if warn or val.get("validation_outcome") != "PASS" else "INCLUDED"}

    def _archive(self, sr: dict[str, Any], eid: str, full_id: str) -> None:
        try:
            self.aws.s3_copy(sr.get("content_s3_bucket", self.s.output_bucket), sr["content_s3_key"], f"sections/{eid}/history/{full_id}.attempt0.json")
        except Exception:  # noqa: BLE001 - archiving is best effort
            pass

    def _reassemble(self, arn: str, doc: dict[str, Any], inp: dict[str, Any], included: list[dict[str, Any]],
                    replaced: dict[str, dict[str, Any]], by_tid: dict[str, dict[str, Any]]) -> dict[str, Any]:
        sections: list[dict[str, Any]] = []
        seen: set[str] = set()
        for e in included:
            tid = e.get("template_id") or e.get("section_id")
            sections.append(replaced.get(tid, e))
            seen.add(tid)
        for tid, e in replaced.items():  # sections that were missing before are now added
            if tid not in seen:
                sections.append(e)
        self.ledger.event(arn, doc, "reassembling", f"Re-assembling the report with {len(sections)} sections.")
        res = self.aws.lambda_invoke(self.s.assembly_function, {
            "sections": sections, "output_bucket": inp.get("output_bucket", self.s.output_bucket), "reporting_year": inp["reporting_year"],
            "bank_id": inp.get("bank_id", self.s.bank_id), "framework": inp.get("framework", "MULTI_FRAMEWORK"),
            "execution_id": arn, "generation_timestamp": iso(self.aws.now())})
        self.ledger.event(arn, doc, "reassembled", "A corrected report was assembled.", s3_path=res.get("s3_path"))
        return res

    def _download_info(self, assembly: dict[str, Any] | None) -> dict[str, Any]:
        path = (assembly or {}).get("s3_path", "")
        if not path.startswith("s3://"):
            return {}
        bucket, _, key = path[5:].partition("/")
        info = {"download_url": self.aws.s3_presign(bucket, key)}
        pptx = (assembly or {}).get("s3_path_pptx", "")
        if pptx.startswith("s3://"):
            b2, _, k2 = pptx[5:].partition("/")
            info["download_url_pptx"] = self.aws.s3_presign(b2, k2)
        return info

    def _arn(self, execution: str) -> str:
        if execution.startswith("arn:"):
            return execution
        meta = self.aws.s3_get_json(self.s.output_bucket, self.ledger.meta_key(execution)) or {}
        if meta.get("execution_arn"):
            return meta["execution_arn"]
        sm = self.s.report_state_machine_arn  # executions started outside the orchestrator are report runs
        return f"{sm.replace(':stateMachine:', ':execution:')}:{execution}"

    def _pipeline_from(self, d: dict[str, Any]) -> str:
        arn = d.get("stateMachineArn") or ""
        return "ghg_inventory" if self.s.ghg_state_machine_arn and arn == self.s.ghg_state_machine_arn else "esg_report"
