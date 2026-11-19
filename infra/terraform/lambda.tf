locals {
  lambda_src_dir = "${path.module}/../../lambdas"

  # One entry per Lambda: source file, environment and least-privilege permissions
  lambdas = {
    kyc-validate-uploads = {
      source = "kyc_validate_uploads"
      env    = {}
      statements = [
        {
          # ListBucket lets HeadObject return 404 (missing) instead of 403
          Effect   = "Allow"
          Action   = ["s3:ListBucket"]
          Resource = [aws_s3_bucket.kyc.arn]
        },
        {
          Effect   = "Allow"
          Action   = ["s3:GetObject"]
          Resource = ["${aws_s3_bucket.kyc.arn}/kyc/*"]
        },
      ]
    }

    kyc-compare-faces = {
      source = "kyc_compare_faces"
      env = {
        SIMILARITY_THRESHOLD = tostring(var.similarity_threshold)
      }
      statements = [
        {
          Effect   = "Allow"
          Action   = ["rekognition:CompareFaces"]
          Resource = ["*"] # CompareFaces does not support resource-level permissions
        },
        {
          Effect   = "Allow"
          Action   = ["s3:GetObject"]
          Resource = ["${aws_s3_bucket.kyc.arn}/kyc/*"]
        },
      ]
    }

    kyc-update-status = {
      source = "kyc_update_status"
      env = {
        KYC_TABLE_NAME = aws_dynamodb_table.kyc_records.name
      }
      statements = [
        {
          Effect   = "Allow"
          Action   = ["dynamodb:PutItem"]
          Resource = [aws_dynamodb_table.kyc_records.arn]
        },
      ]
    }

    transaction-processor = {
      source = "transaction_processor"
      env = {
        TRANSACTIONS_TABLE_NAME = aws_dynamodb_table.transactions.name
        FLAGGED_QUEUE_URL       = aws_sqs_queue.flagged.url
        RISK_ALERTS_TOPIC_ARN   = aws_sns_topic.risk_alerts.arn
        HIGH_RISK_THRESHOLD_NGN = tostring(var.high_risk_threshold_ngn)
      }
      statements = [
        {
          Effect   = "Allow"
          Action   = ["dynamodb:PutItem"]
          Resource = [aws_dynamodb_table.transactions.arn]
        },
        {
          Effect   = "Allow"
          Action   = ["sqs:SendMessage"]
          Resource = [aws_sqs_queue.flagged.arn]
        },
        {
          Effect   = "Allow"
          Action   = ["sns:Publish"]
          Resource = [aws_sns_topic.risk_alerts.arn]
        },
      ]
    }
  }
}

data "archive_file" "lambda" {
  for_each = local.lambdas

  type        = "zip"
  source_file = "${local.lambda_src_dir}/${each.value.source}.py"
  output_path = "${path.module}/build/${each.key}.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  for_each = local.lambdas

  name               = "${var.name_prefix}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "lambda" {
  for_each = local.lambdas

  name = "least-privilege"
  role = aws_iam_role.lambda[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(each.value.statements, [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["${aws_cloudwatch_log_group.lambda[each.key].arn}:*"]
      },
    ])
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.lambdas

  name              = "/aws/lambda/${var.name_prefix}-${each.key}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "this" {
  for_each = local.lambdas

  function_name    = "${var.name_prefix}-${each.key}"
  role             = aws_iam_role.lambda[each.key].arn
  runtime          = "python3.13"
  handler          = "${each.value.source}.lambda_handler"
  filename         = data.archive_file.lambda[each.key].output_path
  source_code_hash = data.archive_file.lambda[each.key].output_base64sha256
  timeout          = 15
  memory_size      = 256

  dynamic "environment" {
    for_each = length(each.value.env) > 0 ? [1] : []
    content {
      variables = each.value.env
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda, aws_iam_role_policy.lambda]
}
