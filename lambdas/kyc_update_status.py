import boto3
from datetime import datetime
from decimal import Decimal

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('kuda-kyc-records')

def lambda_handler(event, context):
    # Flexible extraction: handles 'userId' or 'user_Id' from the state machine input
    user_id = event.get('userId') or event.get('user_Id')
    
    # Fail early with a clear message if the Step Function didn't pass the ID
    if not user_id:
        raise KeyError("Validation Failed: 'userId' or 'user_Id' was not found in the incoming execution event.")

    similarity = event.get('similarity', 0)
    status     = "APPROVED" if similarity >= 80 else "REJECTED"
    reason     = "FACE_MATCH_VERIFIED" if status == "APPROVED" else "IDENTITY_MISMATCH_FLAGGED"
    
    # Write to DynamoDB
    table.put_item(Item={
        'user_Id': str(user_id),       # Partition Key (Schema matched)
        'time_stamp': datetime.utcnow().isoformat(), # Sort Key (Fixed from 'timestamp' to 'time_stamp')
        'kycStatus': status,
        'similarityScore': Decimal(str(round(similarity, 2))),
        'reason': reason,
        'auditLog': f"KYC {status} — similarity: {similarity:.2f}%"
    })
    
    return {**event, "kycStatus": status, "reason": reason}