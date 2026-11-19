data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "kyc_pipeline" {
  name               = "${var.name_prefix}-kyc-pipeline"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

resource "aws_iam_role_policy" "kyc_pipeline" {
  name = "invoke-kyc-lambdas-and-log"
  role = aws_iam_role.kyc_pipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          for k in ["kyc-validate-uploads", "kyc-compare-faces", "kyc-update-status"] :
          aws_lambda_function.this[k].arn
        ]
      },
      {
        # Step Functions log delivery APIs do not support resource-level permissions
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
        ]
        Resource = ["*"]
      },
    ]
  })
}

resource "aws_cloudwatch_log_group" "kyc_pipeline" {
  name              = "/aws/vendedlogs/states/${var.name_prefix}-kyc-pipeline"
  retention_in_days = var.log_retention_days
}

resource "aws_sfn_state_machine" "kyc_pipeline" {
  name     = "${var.name_prefix}-kyc-pipeline"
  role_arn = aws_iam_role.kyc_pipeline.arn

  definition = templatefile("${path.module}/../../step-functions/kuda-kyc-pipeline.json", {
    validate_uploads_arn = aws_lambda_function.this["kyc-validate-uploads"].arn
    compare_faces_arn    = aws_lambda_function.this["kyc-compare-faces"].arn
    update_status_arn    = aws_lambda_function.this["kyc-update-status"].arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.kyc_pipeline.arn}:*"
    include_execution_data = false # keep customer PII out of logs
    level                  = "ERROR"
  }

  depends_on = [aws_iam_role_policy.kyc_pipeline]
}
