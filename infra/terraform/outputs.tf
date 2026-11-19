output "kyc_bucket_name" {
  description = "Upload KYC images to kyc/<userId>/id-document.jpg and kyc/<userId>/selfie.jpg."
  value       = aws_s3_bucket.kyc.bucket
}

output "kyc_state_machine_arn" {
  value = aws_sfn_state_machine.kyc_pipeline.arn
}

output "transaction_processor_function_name" {
  value = aws_lambda_function.this["transaction-processor"].function_name
}

output "flagged_transactions_queue_url" {
  value = aws_sqs_queue.flagged.url
}

output "risk_alerts_topic_arn" {
  value = aws_sns_topic.risk_alerts.arn
}
