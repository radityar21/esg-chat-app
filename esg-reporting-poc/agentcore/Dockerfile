# AgentCore Runtime container for the ESG orchestrator (ARM64).
# Build context MUST be esg-reporting-poc/ (the CDK stack does this for you):
#   docker buildx build --platform linux/arm64 -f agentcore/Dockerfile -t esg-orchestrator .
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 AWS_REGION=us-east-1
WORKDIR /app

COPY agentcore/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY agentcore/app.py ./app.py
COPY agentcore/orchestrator ./orchestrator
COPY lambda/_shared ./_shared

RUN useradd -m -u 1000 agent && chown -R agent /app
USER agent

EXPOSE 8080
# opentelemetry-instrument enables AgentCore observability traces (aws-opentelemetry-distro)
CMD ["opentelemetry-instrument", "python", "app.py"]
