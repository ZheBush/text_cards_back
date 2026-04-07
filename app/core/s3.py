import boto3
from botocore.config import Config
from app.core.config import settings

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name=settings.S3_REGION,
)


def upload_file_to_s3(file_content: bytes, bucket: str, key: str, content_type: str) -> None:
    s3_client.put_object(Bucket=bucket, Key=key, Body=file_content, ContentType=content_type)


def generate_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )