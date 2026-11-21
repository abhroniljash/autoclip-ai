# AWS deployment plan

Target region: **Asia Pacific (Mumbai), `ap-south-1`**.

This branch now includes authentication endpoints, per-user API scoping, private S3 helpers, SQS producers and a worker entry point, plus Terraform for the S3 bucket, SQS queue/DLQ and ECS task role. This is not yet a deployed AWS environment.

## Application architecture

- **Amazon ECS on EC2** runs the FastAPI API service and a separate video/export worker service.
- **Amazon EFS is required as a shared working volume** mounted at the same container path by API and worker tasks. Uploads are staged on EFS before SQS dispatch; FFmpeg reads/writes there. Without the shared filesystem, worker jobs cannot see the API's local source file. Configure EFS encryption, access points, VPC mount targets and security groups.
- **Amazon S3** stores the original source and generated project/clip media privately. The API returns short-lived presigned redirects for S3-backed previews/downloads. The bucket is encrypted, versioned, and public access is blocked by the Terraform in `infra/aws`.
- **Amazon SQS** carries project-processing and export jobs. A dead-letter queue is configured after repeated receives. The worker is `worker.py`.
- **Amazon RDS for PostgreSQL** stores application metadata. Use a private subnet group and TLS.
- **Application Load Balancer + ACM** terminates HTTPS in front of the API.
- **AWS Secrets Manager** should provide `JWT_SECRET`, database credentials and AI provider keys.
- **CloudWatch** should collect API/worker logs, SQS depth, DLQ messages, CPU, memory, EFS throughput and disk pressure.

## What is implemented

- JWT authentication with Argon2 password hashing, registration/login, HttpOnly session cookie and bearer-token support.
- Project, clip, export and download queries are scoped to the authenticated project owner.
- Local `/storage` is no longer mounted publicly. Media previews use authenticated endpoints; S3 objects are served through short-lived presigned URLs.
- Original uploads are copied to the private S3 bucket when `S3_BUCKET` is configured.
- Project and export jobs are sent to SQS when `SQS_QUEUE_URL` is configured. Without SQS, local development falls back to in-process tasks.
- Worker uploads generated project thumbnails, clip MP4s, thumbnails and subtitle files to S3.
- Export background work uses a fresh SQLAlchemy session instead of a request-scoped session.
- Terraform provisions a private encrypted/versioned S3 bucket, SQS queue + DLQ, and an ECS task role with scoped S3/SQS permissions.
- Alembic is configured and a migration adds the user password hash column for existing databases.

## Important integration requirements

1. **EFS must be mounted by both API and worker at the same path.** The current pipeline uses filesystem paths internally. S3 stores durable copies, while EFS is the shared scratch/work directory. Do not run API and worker on isolated container filesystems.
2. Configure `S3_BUCKET`, `SQS_QUEUE_URL`, `AWS_REGION=ap-south-1`, `JWT_SECRET`, `COOKIE_SECURE=true`, `DATABASE_URL`, and AI provider keys through ECS task definitions/Secrets Manager. Do not commit secrets.
3. Attach the Terraform output `ecs_task_role_arn` as the ECS task role. The execution role for pulling images and writing logs is separate.
4. Configure SQS visibility timeout and worker heartbeats to exceed the maximum expected video duration. The current worker uses a 900-second visibility timeout and still needs heartbeat extension for jobs that run longer.
5. The current Alembic revision covers the new password-hash column. The rest of the legacy schema is still initially created by SQLAlchemy `create_all`; a complete baseline migration and a tested PostgreSQL upgrade from the existing schema are still required.
6. Legacy projects with no `user_id` remain unowned and are intentionally not visible to newly registered accounts. Create an explicit, audited data migration if any legacy data must be assigned.
7. The YouTube import path, export ZIP media lifecycle, retries/idempotency, rate limits, upload quotas, virus scanning, retention/deletion policies, and worker concurrency controls need additional tests and hardening.

## Provision S3 and SQS

From the repository root, with Terraform installed and an AWS identity configured for the target account:

```bash
cd infra/aws
terraform init
terraform plan -var="media_bucket_name=YOUR-GLOBALLY-UNIQUE-BUCKET-NAME"
terraform apply -var="media_bucket_name=YOUR-GLOBALLY-UNIQUE-BUCKET-NAME"
```

Review the plan and expected AWS costs before applying. Terraform provisions S3, SQS and an ECS task role only. It does not yet create the VPC, EFS, RDS, ECS cluster/services, ALB, ACM certificate, Secrets Manager entries, CloudWatch alarms or DNS.

## Local development

1. Copy `.env.example` to `.env`.
2. Set a long random `JWT_SECRET`, `POSTGRES_PASSWORD`, and optional AI provider key.
3. Run `docker compose up --build`.
4. Open `http://localhost:8000`, register an account, and verify `/health`.

To start the optional worker profile, configure AWS credentials using a local AWS profile or another supported credential provider, set `S3_BUCKET` and `SQS_QUEUE_URL`, then run `docker compose --profile aws up --build`.

## Release checklist

- [ ] Complete baseline Alembic migrations and validate PostgreSQL schema upgrade from a copy of production data.
- [ ] Add SQS visibility heartbeats, idempotency keys, retry classification, DLQ replay tooling and concurrency limits.
- [ ] Add media range/streaming tests and confirm presigned URL expiry behavior.
- [ ] Add authentication, ownership, upload, S3, SQS and export integration tests.
- [ ] Add rate limiting, quotas, malware scanning, retention policies and account deletion.
- [ ] Provision VPC, EFS, RDS, ECS, ALB, ACM, Secrets Manager, CloudWatch and DNS.
- [ ] Run staging end-to-end tests for registration, upload, processing, editing, preview and ZIP export.
- [ ] Review AWS Budgets and alarms before production traffic.

## Cost and safety

Video processing consumes CPU, memory, EFS throughput, S3 storage and data transfer. Set AWS Budgets and alerts before provisioning. Keep the bucket private, database private, and only expose HTTPS through the ALB. Do not deploy with root access keys.
