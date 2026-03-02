"""Vendor/dependency classification database for lock-in sentinel."""

VENDOR_MAP = {
    # Gumdrop / OpenAI Ecosystem
    "openai": "OpenAI",
    "tiktoken": "OpenAI",
    "langchain-openai": "OpenAI",
    # AWS Ecosystem
    "boto3": "AWS",
    "botocore": "AWS",
    "s3transfer": "AWS",
    "aws-cdk-lib": "AWS",
    "chalice": "AWS",
    # Google Cloud Ecosystem
    "google-cloud-storage": "Google",
    "google-cloud-vision": "Google",
    "firebase-admin": "Google",
    # Microsoft Ecosystem
    "azure-storage-blob": "Microsoft",
    "azure-identity": "Microsoft",
    "microsoft-graph-core": "Microsoft",
    # Vercel / Next.js (JS用だが概念として)
    "vercel": "Vercel",
}

LOW_RISK_OSS = {
    "protobuf",
    "requests",
    "numpy",
}

TOXIC_REQS = {
    "openai",
    "tiktoken",
    "langchain-openai",
}

# "Frictionless" (摩擦なし＝依存) とみなす閾値
DEFAULT_THRESHOLD = 0.3  # 30%以上が特定ベンダーならロックインとみなす
