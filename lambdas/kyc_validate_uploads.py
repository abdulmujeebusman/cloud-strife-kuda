import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # Fix for Line 9: Extract the bucket name and user ID passed by Step Functions
    bucket_name = event['bucket']
    user_id     = event['userId'] 
    
    # Dynamically build the exact paths based on your clean S3 folder structure
    id_key      = f"kyc/{user_id}/id-document.jpg"      
    selfie_key  = f"kyc/{user_id}/selfie.jpg"   
    
    try:
        s3.head_object(Bucket=bucket_name, Key=id_key)
        s3.head_object(Bucket=bucket_name, Key=selfie_key)
    except Exception as e:
        raise Exception(f"Required KYC documents missing for user: {user_id}")
        
    # Pass the keys forward so the next state (kuda-kyc-compare-faces) can use them!
    return {**event, "id_key": id_key, "selfie_key": selfie_key}