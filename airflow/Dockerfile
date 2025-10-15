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
RUN uv pip install --system --no-cache -r requirements.txt

# RUN python3 -m pip install --upgrade pip
# RUN python3 -m pip install --no-cache-dir -r requirements.txt
USER airflow