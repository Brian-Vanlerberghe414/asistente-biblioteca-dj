"""Cliente S3-compatible para Cloudflare R2.

R2 expone una API idéntica a S3 — se usa `boto3` apuntando al endpoint de
R2 del proyecto, en vez de a AWS. Las URLs firmadas (presigned) dejan que
el cliente (la app de escritorio, más adelante Android/web) suba o baje el
archivo *directo* a R2, sin que los bytes pasen por este backend.
"""
from __future__ import annotations

import os

import boto3
from botocore.config import Config

R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]

_cliente = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def url_subida(r2_key: str, expira_seg: int = 3600) -> str:
    """URL firmada para que el cliente suba el archivo directo a R2 (PUT)."""
    return _cliente.generate_presigned_url(
        "put_object",
        Params={"Bucket": R2_BUCKET_NAME, "Key": r2_key},
        ExpiresIn=expira_seg,
    )


def url_descarga(r2_key: str, expira_seg: int = 3600) -> str:
    """URL firmada para que el cliente descargue/escuche el archivo (GET)."""
    return _cliente.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET_NAME, "Key": r2_key},
        ExpiresIn=expira_seg,
    )
