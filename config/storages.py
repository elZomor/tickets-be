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


# Initialize S3 client
def get_s3_object(file_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_S3_REGION_NAME,
    )
    return s3.get_object(Bucket=AWS_STORAGE_BUCKET_NAME, Key=file_name)
