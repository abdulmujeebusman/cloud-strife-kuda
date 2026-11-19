import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')


class KYCDocumentsMissing(Exception):
    """Raised when the ID document or selfie has not been uploaded yet.

    Step Functions matches on this class name to route to the UploadError state.
    """


def lambda_handler(event, context):
    bucket_name = event['bucket']
    user_id     = event['userId']

    # Uploads follow a fixed per-user folder layout in S3
    id_key      = f"kyc/{user_id}/id-document.jpg"
    selfie_key  = f"kyc/{user_id}/selfie.jpg"

    for key in (id_key, selfie_key):
        try:
            s3.head_object(Bucket=bucket_name, Key=key)
        except ClientError as e:
            # Only a genuine "not found" means the customer hasn't uploaded yet.
            # Anything else (AccessDenied, throttling, ...) is re-raised so it
            # surfaces as a processing error instead of being misreported.
            if e.response['Error']['Code'] in ('404', 'NoSuchKey', 'NotFound'):
                raise KYCDocumentsMissing(
                    f"Required KYC document missing for user {user_id}: {key}"
                ) from e
            raise

    # Pass the keys forward so the CompareFaces state can use them
    return {**event, "id_key": id_key, "selfie_key": selfie_key}
