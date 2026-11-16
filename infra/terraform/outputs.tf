output "api_url" {
  description = "HTTP API base URL (LocalStack: http://localhost:4566/restapis/<id>/$default)"
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "dynamodb_table" { value = aws_dynamodb_table.analyses.name }
output "s3_bucket"      { value = aws_s3_bucket.data.bucket }
output "lambda_name"    { value = aws_lambda_function.api.function_name }
