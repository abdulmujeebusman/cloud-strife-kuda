import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('KYC_TABLE_NAME', 'kuda-kyc-records'))


def lambda_handler(event, context):
    # Accept 'userId' or 'user_Id' from the state machine input
    user_id = event.get('userId') or event.get('user_Id')
    if not user_id:
        raise KeyError("Validation Failed: 'userId' or 'user_Id' was not found in the incoming execution event.")

    # The match decision is made once, in kyc_compare_faces
    similarity = float(event.get('similarity', 0))
    status     = "APPROVED" if event.get('faceMatch') else "REJECTED"
    reason     = event.get('reason') or (
        "FACE_MATCH_VERIFIED" if status == "APPROVED" else "IDENTITY_MISMATCH_FLAGGED"
    )

    table.put_item(Item={
        'user_Id': str(user_id),                                  # Partition key
        'time_stamp': datetime.now(timezone.utc).isoformat(),     # Sort key
        'kycStatus': status,
        'similarityScore': Decimal(str(round(similarity, 2))),
        'reason': reason,
        'auditLog': f"KYC {status} ({reason}) - similarity: {similarity:.2f}%",
    })

    return {**event, "kycStatus": status, "reason": reason}
