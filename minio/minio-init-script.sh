#!/bin/sh
# minio-init-script.sh (Improved Version)

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Waiting for MinIO service to be ready..."

# Loop until the 'mc alias set' command succeeds.
# This is more reliable than a fixed 'sleep'.
until mc alias set myminio http://minio.minio.svc.cluster.local:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD; do
  echo "MinIO not ready yet, retrying in 5 seconds..."
  sleep 5
done

echo "MinIO is ready. Setting up client complete."

echo "Creating default folders..."

# Create each folder. The -p flag ensures parent directories are also created.
mc mb -p myminio/lakehouse/iceberg
mc mb -p myminio/airflow/dags
mc mb -p myminio/risingwave/data
mc mb -p myminio/kafka/data
mc mb -p myminio/spark-logs/logs

echo "Folder creation complete."
