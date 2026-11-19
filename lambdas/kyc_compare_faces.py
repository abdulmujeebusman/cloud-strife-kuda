import os

import boto3

rekognition = boto3.client('rekognition')

# Single source of truth for the match threshold. The state machine and the
# status Lambda both read the boolean `faceMatch` produced here.
SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', '80'))


def lambda_handler(event, context):
    bucket_name = event['bucket']
    id_key      = event['id_key']
    selfie_key  = event['selfie_key']

    try:
        response = rekognition.compare_faces(
            SourceImage={'S3Object': {'Bucket': bucket_name, 'Name': id_key}},
            TargetImage={'S3Object': {'Bucket': bucket_name, 'Name': selfie_key}},
            SimilarityThreshold=SIMILARITY_THRESHOLD,
        )
    except rekognition.exceptions.InvalidParameterException:
        # Rekognition raises this when it cannot find a face in one of the
        # images. That is a failed verification, not a system error.
        return {
            **event,
            "similarity": 0,
            "faceMatch": False,
            "reason": "NO_FACE_DETECTED",
        }

    # Take the best match if Rekognition found several faces
    similarity = max(
        (m['Similarity'] for m in response.get('FaceMatches', [])),
        default=0,
    )
    face_match = similarity >= SIMILARITY_THRESHOLD

    return {
        **event,
        "similarity": similarity,
        "faceMatch": face_match,
        "reason": "FACE_MATCH_VERIFIED" if face_match else "IDENTITY_MISMATCH_FLAGGED",
    }
