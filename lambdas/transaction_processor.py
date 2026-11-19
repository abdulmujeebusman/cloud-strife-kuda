import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import boto3

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
sns = boto3.client('sns')

# Configuration comes from the Lambda environment (set by Terraform),
# so no account IDs or ARNs are hardcoded in source.
table = dynamodb.Table(os.environ.get('TRANSACTIONS_TABLE_NAME', 'kuda-transactions'))
SQS_QUEUE_URL = os.environ['FLAGGED_QUEUE_URL']
SNS_TOPIC_ARN = os.environ['RISK_ALERTS_TOPIC_ARN']
HIGH_RISK_THRESHOLD = Decimal(os.environ.get('HIGH_RISK_THRESHOLD_NGN', '500000'))


class InvalidTransaction(Exception):
    """Raised for malformed input, e.g. a missing, zero or negative amount."""


def parse_amount(raw):
    # Decimal, not float: money must not pick up binary rounding errors
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        raise InvalidTransaction(f"Amount is not a number: {raw!r}")
    if not amount.is_finite() or amount <= 0:
        raise InvalidTransaction(f"Amount must be a positive number: {raw!r}")
    return amount.quantize(Decimal('0.01'))


def lambda_handler(event, context):
    # 1. Validate input
    if 'amount' not in event:
        raise InvalidTransaction("Missing required field: amount")
    amount = parse_amount(event['amount'])
    user_id = event.get('userId', 'unknown')

    # Full UUID: a short prefix would eventually collide and overwrite records
    txn_id = uuid.uuid4().hex.upper()

    txn_timestamp = (event.get('timestamp') or event.get('time_stamp')
                     or datetime.now(timezone.utc).isoformat())

    # 2. Risk evaluation
    is_high_risk = amount >= HIGH_RISK_THRESHOLD
    status = "FLAGGED" if is_high_risk else "PROCESSED"

    # 3. Persist (attribute names match the DynamoDB key schema)
    table.put_item(Item={
        'transaction_Id': txn_id,          # Partition key
        'userId': user_id,
        'amount': amount,
        'time_stamp': txn_timestamp,
        'status': status,
    })

    # 4. Route high-risk transactions for review and alert the fraud team
    if is_high_risk:
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({
                'transactionId': txn_id,
                'amount': str(amount),
                'userId': user_id,
                'timestamp': txn_timestamp,
            }),
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Kuda Risk Alert",
            Message=(
                f"[KUDA FRAUD ALERT]\n"
                f"High-risk transaction detected!\n"
                f"Amount: NGN {amount:,.2f}\n"
                f"User: {user_id}\n"
                f"Txn ID: {txn_id}\n"
                f"Status: FLAGGED FOR REVIEW"
            ),
        )

    return {'transactionId': txn_id, 'status': status, 'isHighRisk': is_high_risk}
