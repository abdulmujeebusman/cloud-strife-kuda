import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
sns = boto3.client('sns')
table = dynamodb.Table('kuda-transactions')

SQS_QUEUE_URL = 'https://sqs.eu-west-1.amazonaws.com/650270877421/kuda-flagged-transactions'
SNS_TOPIC_ARN = 'arn:aws:sns:eu-west-1:650270877421:kuda-risk-alerts'
HIGH_RISK_THRESHOLD = 500000  # NGN


def lambda_handler(event, context):
    # 1. Safely extract or generate the transaction values
    amount = float(event.get('amount', 0))
    user_id = event.get('userId', 'unknown')

    # Generate unique 8-character uppercase transaction ID
    txn_id = str(uuid.uuid4())[:8].upper()

    # Fallback timestamp logic to completely prevent KeyErrors
    txn_timestamp = event.get('timestamp') or event.get(
        'time_stamp') or datetime.utcnow().isoformat()

    # 2. Risk Evaluation Logic
    is_high_risk = amount >= HIGH_RISK_THRESHOLD
    status = "FLAGGED" if is_high_risk else "PROCESSED"

    # 3. Consolidated Database Write (Matches your DynamoDB Key Schema perfectly)
    table.put_item(Item={
        'transaction_Id': txn_id,                      # Primary Partition Key
        'userId': user_id,
        # Safely converted for DynamoDB
        'amount': Decimal(str(amount)),
        'time_stamp': txn_timestamp,                    # Safe timestamp
        'status': status
    })

    # 4. Downstream Event Alert Routing
    if is_high_risk:
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({
                'transactionId': txn_id,
                'amount': amount,
                'userId': user_id,
                'timestamp': txn_timestamp
            })
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Kuda Risk Alert",
            Message=(
                f"[KUDA FRAUD ALERT]\n"
                f"High-risk transaction detected!\n"
                f"Amount: NGN {amount:,.0f}\n"
                f"User: {user_id}\n"
                f"Txn ID: {txn_id}\n"
                f"Status: FLAGGED FOR REVIEW"
            )
        )

    return {'transactionId': txn_id, 'status': status, 'isHighRisk': is_high_risk}
