"""Writes immutable Parquet objects to the local MinIO service."""

import os
from io import BytesIO

import boto3
import polars as pl
from botocore.exceptions import ClientError


def write_parquet_if_absent(frame: pl.DataFrame, bucket: str, object_key: str) -> bool:
    buffer = BytesIO()
    frame.write_parquet(buffer)

    client = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )

    try:
        client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=buffer.getvalue(),
            ContentType="application/vnd.apache.parquet",
            IfNoneMatch="*",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] in {"PreconditionFailed", "412"}:
            return False
        raise

    return True
