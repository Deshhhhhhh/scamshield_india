# Infrastructure — IaC without an AWS account (LocalStack) or with one

Two ways to use this Terraform. Only the second touches real AWS, and it's optional.

## A. LocalStack (default, $0, no card)

LocalStack emulates S3/DynamoDB/Lambda/API Gateway on your machine; Terraform's AWS
provider talks to it via `AWS_ENDPOINT_URL`.

```bash
localstack start -d                # or: docker compose --profile aws up -d localstack
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
export AWS_ENDPOINT_URL=http://localhost:4566
cd infra/terraform
terraform init
terraform apply -auto-approve
curl "$(terraform output -raw api_url)/v1/health"
```

What it proves: IAM least-privilege works, S3 write succeeds with AES-256 + public block,
DynamoDB write succeeds with TTL + PITR, API Gateway → Lambda proxy integration responds.
Tear down with `terraform destroy -auto-approve`.

## B. Real AWS (optional; needs a card — not required for this project)

Same files, no `AWS_ENDPOINT_URL`. Region defaults to **ap-south-1 (Mumbai)** for data
residency. Cost guards already in place: PAY_PER_REQUEST DynamoDB (no idle cost), zero NAT
gateways, 30-day S3 lifecycle expiry on `raw/`, TTL on records. Everything is tagged.

## C. Production deployment shape (the honest path)

The repo `Dockerfile` builds a container that runs the full FastAPI app
(`/v1/analyze`, `/v1/stats`, …). On AWS you run that as a **Lambda container image**
(`aws lambda create-function --package-type Image`) or on ECS/Fargate behind the same
HTTP API. `infra/lambda_src/handler.py` in this folder is only a smoke-test stub for the
Terraform wiring — it is not the app.

## Why Terraform and not console-clicking

Every property above (encryption, TTL, lifecycle, public-access block, IAM scoping) is
reviewable, diffable and reproducible in code — exactly what an infra review looks for.
