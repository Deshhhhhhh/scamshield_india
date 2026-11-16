"""LocalStack/AWS smoke-test stub for the ScamShield Lambda.

Purpose: verify IAM, S3 and DynamoDB wiring in Terraform without deploying the full
FastAPI image. The production deployment of the analyze pipeline is a Lambda
CONTAINER built from the repo Dockerfile (see infra/README.md); this stub only
implements /v1/health and an S3/DynamoDB round-trip so `terraform apply` + curl
proves the wiring end-to-end.
"""

import json
import os
import time

import boto3


def lambda_handler(event, context):
    table = os.environ.get("DYNAMODB_TABLE", "")
    bucket = os.environ.get("S3_BUCKET", "")
    result = {"service": "scamshield-lambda-stub", "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    if table:
        try:
            boto3.resource("dynamodb").Table(table).put_item(
                Item={"id": f"stub-{int(time.time())}", "pk": "health", 
                      "created_at": str(int(time.time())), "expires_at": int(time.time()) + 3600}
            )
            result["dynamodb"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result["dynamodb"] = f"error: {type(exc).__name__}"
    if bucket:
        try:
            boto3.client("s3").put_object(
                Bucket=bucket, Key=f"health/{int(time.time())}.json",
                Body=json.dumps(result).encode(), ContentType="application/json",
            )
            result["s3"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result["s3"] = f"error: {type(exc).__name__}"

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
