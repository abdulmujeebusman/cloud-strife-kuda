# ---------- S3: KYC uploads (kyc/<userId>/id-document.jpg, kyc/<userId>/selfie.jpg) ----------

resource "aws_s3_bucket" "kyc" {
  bucket_prefix = "cloud-strife-${var.name_prefix}-kyc-"
}

resource "aws_s3_bucket_public_access_block" "kyc" {
  bucket                  = aws_s3_bucket.kyc.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kyc" {
  bucket = aws_s3_bucket.kyc.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "kyc" {
  bucket = aws_s3_bucket.kyc.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Identity documents are sensitive: deny any request that isn't over TLS
resource "aws_s3_bucket_policy" "kyc_tls_only" {
  bucket = aws_s3_bucket.kyc.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.kyc.arn, "${aws_s3_bucket.kyc.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.kyc]
}

# ---------- DynamoDB ----------

resource "aws_dynamodb_table" "kyc_records" {
  name         = "${var.name_prefix}-kyc-records"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_Id"
  range_key    = "time_stamp"

  attribute {
    name = "user_Id"
    type = "S"
  }

  attribute {
    name = "time_stamp"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_dynamodb_table" "transactions" {
  name         = "${var.name_prefix}-transactions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "transaction_Id"

  attribute {
    name = "transaction_Id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

# ---------- Messaging: flagged-transaction queue + fraud alerts ----------

resource "aws_sqs_queue" "flagged_dlq" {
  name                      = "${var.name_prefix}-flagged-transactions-dlq"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "flagged" {
  name                    = "${var.name_prefix}-flagged-transactions"
  sqs_managed_sse_enabled = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.flagged_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sns_topic" "risk_alerts" {
  name = "${var.name_prefix}-risk-alerts"
}

resource "aws_sns_topic_subscription" "fraud_team_email" {
  count     = var.fraud_alert_email == null ? 0 : 1
  topic_arn = aws_sns_topic.risk_alerts.arn
  protocol  = "email"
  endpoint  = var.fraud_alert_email
}
