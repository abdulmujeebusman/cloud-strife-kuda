import boto3

# Initialize the Amazon Rekognition client
rekognition = boto3.client('rekognition', region_name='eu-west-1')

def lambda_handler(event, context):
    bucket_name = event['bucket']
    
    # Steps 5 & 6: Switched from camelCase to snake_case to match incoming event payload
    id_key      = event['id_key']      
    selfie_key  = event['selfie_key']
    
    # Call Rekognition to compare the face on the ID card with the selfie image
    response = rekognition.compare_faces(
        SourceImage={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': id_key
            }
        },
        TargetImage={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': selfie_key
            }
        },
        SimilarityThreshold=80
    )
    
    # Extract the similarity score safely
    face_matches = response.get('FaceMatches', [])
    similarity = face_matches[0]['Similarity'] if face_matches else 0
    
    # Return payload containing similarity score for subsequent evaluation steps
    return {
        **event,
        "similarity": similarity
    }