import os

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "minio.minio.svc.cluster.local:9000")
S3_SSL_ENABLE = os.getenv("S3_SSL_ENABLE", "false")
S3_PATH_STYLE_ACCESS = os.getenv("S3_PATH_STYLE_ACCESS", "true")
S3_ATTEMPTS_MAXIMUM = os.getenv("S3_ATTEMPTS_MAXIMUM", "1")
S3_CONNECTION_ESTABLISH_TIMEOUT = os.getenv("S3_CONNECTION_ESTABLISH_TIMEOUT", "5000")
S3_CONNECTION_TIMEOUT = os.getenv("S3_CONNECTION_TIMEOUT", "10000")

SPARK_EVENT_LOG_DIR = os.getenv("SPARK_EVENT_LOG_DIR", "s3a://spark-logs/logs")
S3_WAREHOUSE = os.getenv("S3_WAREHOUSE", "s3a://lakehouse/")
S3_HTTP_ENDPOINT = (
    f"https://{S3_ENDPOINT}" if S3_SSL_ENABLE == "true" else f"http://{S3_ENDPOINT}"
)
ICEBERG_REST_CATALOG_URI = os.getenv("ICEBERG_REST_CATALOG_URI", "http://iceberg-rest-catalog.catalog.svc.cluster.local:8181")