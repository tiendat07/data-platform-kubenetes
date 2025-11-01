FROM apache/airflow:3.1.0
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    curl \
    wget \
    unzip \
    git \
 && rm -rf /var/lib/apt/lists/*
 RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt \
    --target /home/airflow/.local/lib/python3.12/site-packages

USER airflow
ENV PYTHONPATH=/home/airflow/.local/lib/python3.12/site-packages:$PYTHONPATH