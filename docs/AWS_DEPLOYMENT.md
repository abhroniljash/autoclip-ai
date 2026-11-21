# AWS deployment plan

This repository now has a container build and a local PostgreSQL-backed Compose stack. These are deployment foundations, not a completed AWS deployment.

## Target AWS architecture

- **Amazon ECS on EC2** for the API and video-processing worker containers. Video encoding is CPU- and memory-intensive; EC2 gives more predictable control over instance sizing and FFmpeg workloads than a small serverless task.
- **Application Load Balancer** with HTTPS and an ACM certificate in front of the API.
- **Amazon RDS for PostgreSQL** for durable application metadata.
- **Amazon S3 private buckets** for original uploads, extracted audio, generated clips, subtitles, and exports. Use presigned upload/download URLs; do not make the bucket public.
- **Amazon SQS** for durable processing jobs, with a separate worker service consuming jobs. The current application still uses FastAPI in-process background tasks and is not yet wired to SQS.
- **AWS Secrets Manager** for Gemini/OpenAI keys and database credentials.
- **CloudWatch Logs and alarms** for API/worker logs, queue depth, failures, CPU, memory, and disk pressure.

## Important release blockers

Do not expose this application to the public internet yet. The current codebase still has no authentication or project ownership enforcement, and the `/storage` static mount exposes local media paths. These need to be replaced with authenticated access and private S3 presigned URLs before a public launch.

The current processing pipeline also needs a durable queue/worker split. FastAPI's in-process background tasks can be lost on a restart or deployment. A single API container must not be treated as a reliable video-processing platform.

The current database initialization uses `create_all`; production needs versioned migrations (Alembic) before schema changes are deployed.

## Container configuration

The Docker image installs FFmpeg and fonts, runs as a non-root user, and uses the application's `/health` endpoint for container health checks.

For local integration testing:

1. Copy `.env.example` to `.env`.
2. Set a strong `POSTGRES_PASSWORD` and your optional AI provider key.
3. Run `docker compose up --build`.
4. Open `http://localhost:8000` and verify `/health`.

The Compose volumes are for local testing only. They are not a substitute for S3 and RDS backups in AWS.

## AWS release checklist

- [ ] Implement user authentication and per-user authorization for every project, clip, and export endpoint.
- [ ] Remove public `/storage` serving and migrate media I/O to private S3.
- [ ] Implement SQS-backed jobs, idempotency, retries, dead-letter queue, and worker concurrency limits.
- [ ] Add Alembic migrations and a tested PostgreSQL upgrade path.
- [ ] Add API rate limits, upload quotas, malware/container validation, and retention/deletion policies.
- [ ] Add CI tests and container vulnerability scanning.
- [ ] Provision ECS, ALB, RDS, S3, SQS, Secrets Manager, IAM roles, and CloudWatch with least-privilege permissions.
- [ ] Deploy to a staging environment, run end-to-end upload/transcribe/render/export tests, then review before production.

## Cost and safety

Keep S3 buckets private, restrict inbound traffic to the load balancer, keep database access inside the VPC, and set AWS Budgets/alerts before provisioning. Video workloads can generate substantial compute, storage, and data-transfer costs. Do not commit credentials or deploy using root AWS access keys.
