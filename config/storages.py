import uuid

from django.core.files.storage import FileSystemStorage
from .constants import (
    AWS_S3_REGION_NAME,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
)
import boto3

# Custom local storage backend
local_storage = FileSystemStorage(location='local_files/', base_url='/local_files/')


def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_S3_REGION_NAME,
    )


# Initialize S3 client
def get_s3_object(file_name):
    s3 = get_s3_client()
    return s3.get_object(Bucket=AWS_STORAGE_BUCKET_NAME, Key=file_name)


def generate_presigned_upload_url(folder: str, file_extension: str, content_type: str, expires_in: int = 3600):
    """
    Generate a presigned URL for direct S3 upload.
    Returns the presigned URL and the S3 key where the file will be stored.
    """
    s3 = get_s3_client()
    file_key = f"{folder}/{uuid.uuid4()}.{file_extension}"

    presigned_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': AWS_STORAGE_BUCKET_NAME,
            'Key': file_key,
            'ContentType': content_type,
        },
        ExpiresIn=expires_in,
    )

    return {
        'upload_url': presigned_url,
        'file_key': file_key,
    }
