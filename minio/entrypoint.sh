#!/bin/sh
set -e

echo "MinIO is confirmed to be healthy. Proceeding with setup."

# The 'mc' alias needs to be set once for the commands to work.
/usr/bin/mc config host add minio http://minio:9000 admin password

echo "Creating default folders..."
/usr/bin/mc mb minio/lakehouse/iceberg
/usr/bin/mc mb minio/airflow/logs
/usr/bin/mc mb minio/risingwave/data
/usr/bin/mc mb minio/kafka/data
/usr/bin/mc mb minio/spark-logs/logs

echo "Setup complete. Tailing /dev/null to keep container alive."
tail -f /dev/null
