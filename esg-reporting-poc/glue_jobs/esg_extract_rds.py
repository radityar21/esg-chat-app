"""Glue job: extract one table for one reporting year from the source database (RDS PostgreSQL) into the raw zone.

    --TABLE            one of the keys of esg_contracts.CONTRACTS
    --REPORTING_YEAR   e.g. 2024
    --RUN_ID           Step Functions execution name (groups the reports of one sync)

Order of work (nothing is written to the raw zone unless the contract has no blocking violation):
    1. read  esg.<table> through the Glue connection (read-only database user) and keep reporting_year = <year>
    2. gather statistics, evaluate the data contract, write the report to s3://<report bucket>/etl-reports/
    3. blocking violation -> fail with "DATA_CONTRACT_FAILED: ..." (the AgentCore orchestrator triages the failure)
    4. otherwise write Parquet to s3://<raw bucket>/raw/<table>/reporting_year=<year>/ (same layout as the Athena tables)
"""
import json
import sys
from datetime import datetime, timezone

import boto3
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

import esg_contracts as C

args = getResolvedOptions(sys.argv, ["TABLE", "REPORTING_YEAR", "RUN_ID", "CONNECTION_NAME", "SCHEMA", "OUT_BUCKET", "REPORT_BUCKET"])
table, year, run_id = args["TABLE"], int(args["REPORTING_YEAR"]), args["RUN_ID"]
if table not in C.CONTRACTS:  # the name goes into SQL: only contract tables are allowed
    raise ValueError(f"Unknown table {table!r}")
if not 2000 <= year <= 2100:
    raise ValueError("REPORTING_YEAR out of range")
spec = C.CONTRACTS[table]
sc = SparkContext.getOrCreate()
glue = GlueContext(sc)

# Glue treats "dbtable" as a table name (a subquery is quoted as an identifier), so read schema.table and filter in Spark.
# The source tables are small (thousands of rows), so reading the whole table is cheap.
dyf = glue.create_dynamic_frame.from_options(
    connection_type="postgresql",
    connection_options={"useConnectionProperties": "true", "connectionName": args["CONNECTION_NAME"], "dbtable": f"{args['SCHEMA']}.{table}"})
src = dyf.toDF()
if "reporting_year" not in src.columns:
    raise RuntimeError(f"DATA_CONTRACT_FAILED: {table} {year}: Column 'reporting_year' is not present in the source table.")
df = src.filter(F.col("reporting_year") == year).drop("reporting_year").cache()

# ── statistics ─────────────────────────────────────────────────────────────────────────────────
rows = df.count()
types = dict(df.dtypes)
aggs = []
for c, t in types.items():
    aggs.append(F.sum(F.col(c).isNull().cast("int")).alias(f"{c}__nulls"))
    if t in ("double", "float", "int", "bigint", "smallint") or t.startswith("decimal") or t == "date":
        aggs.append(F.min(c).cast("string").alias(f"{c}__min"))
        aggs.append(F.max(c).cast("string").alias(f"{c}__max"))
agg = df.agg(*aggs).first().asDict() if rows else {}
columns = {}
for c, t in types.items():
    entry = {"type": t, "nulls": int(agg.get(f"{c}__nulls") or 0)}
    for k in ("min", "max"):
        v = agg.get(f"{c}__{k}")
        entry[k] = (float(v) if t != "date" else v) if v is not None else None
    if c in spec["columns"] and spec["columns"][c].get("enum"):
        entry["distinct"] = [r[0] for r in df.select(c).distinct().limit(21).collect()]
    columns[c] = entry
keys = [k for k in spec["unique"] if k in types]
dup = df.groupBy(*keys).count().filter("count > 1").count() if (keys and rows) else 0
stats = {"row_count": rows, "columns": columns, "duplicate_keys": dup}

violations = C.evaluate(table, stats)
summary = C.summarize(violations)
report = {"table": table, "reporting_year": year, "run_id": run_id, "generated_at": datetime.now(timezone.utc).isoformat(),
          **summary, "rows": rows, "violations": violations, "wrote_raw": False}

s3 = boto3.client("s3")


def put_report():
    body = json.dumps(report, default=str).encode()
    for key in (f"etl-reports/{run_id}/{table}_{year}.json", f"etl-reports/latest/{table}_{year}.json"):
        s3.put_object(Bucket=args["REPORT_BUCKET"], Key=key, Body=body, ContentType="application/json")


if summary["blocking"]:
    put_report()
    first = "; ".join(v["detail"] for v in violations if v["level"] == "blocking")[:600]
    raise RuntimeError(f"DATA_CONTRACT_FAILED: {table} {year}: {first}")

out = f"s3://{args['OUT_BUCKET']}/raw/{table}/reporting_year={year}/"
writer = df.write.mode("overwrite")
if spec["partitions"]:
    writer = writer.partitionBy(*spec["partitions"])
writer.option("compression", "snappy").parquet(out)
report["wrote_raw"] = True
report["output"] = out
put_report()
print(json.dumps({"table": table, "year": year, "rows": rows, "status": summary["status"]}))
