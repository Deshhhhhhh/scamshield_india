provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
      Purpose   = "scam-detection-demo"
    }
  }
}

# ---------- storage ----------
resource "aws_s3_bucket" "data" {
  bucket_prefix = "${var.project_name}-data-"
  force_destroy = true # demo stack: easy teardown, no orphaned cost
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    id     = "expire-raw"
    status = "Enabled"
    filter { prefix = "raw/" }
    expiration { days = var.retention_days }
  }
}

resource "aws_dynamodb_table" "analyses" {
  name         = "${var.project_name}-analyses"
  billing_mode = "PAY_PER_REQUEST" # no idle cost — matches the zero-rupee constraint
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true # old records expire automatically — data minimisation
  }

  point_in_time_recovery { enabled = true }

  server_side_encryption { enabled = true }
}

# ---------- IAM: least privilege ----------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_inline" {
  statement {
    sid       = "DynamoDBWrite"
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query"]
    resources = [aws_dynamodb_table.analyses.arn]
  }
  statement {
    sid       = "S3Scoped"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.data.arn}/health/*", "${aws_s3_bucket.data.arn}/scans/*"]
  }
}

resource "aws_iam_role_policy" "lambda_inline" {
  name   = "${var.project_name}-lambda-inline"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_inline.json
}

# ---------- Lambda (smoke-test stub; see infra/README.md for the container build) ----------
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda_src"
  output_path = "${path.module}/build/lambda.zip"
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.project_name}-api"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 10
  memory_size      = 256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.analyses.name
      S3_BUCKET      = aws_s3_bucket.data.id
    }
  }
}

# ---------- HTTP API ----------
resource "aws_apigatewayv2_api" "http" {
  name          = "${var.project_name}-http-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"] # public read API; writes are rate-limited at the app layer
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
    max_age       = 86400
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
