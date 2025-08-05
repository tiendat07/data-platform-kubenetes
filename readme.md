Of course. That's an excellent idea. Consolidating all your commands and configurations into a well-structured `README.md` file is the best way to document your project, making it easy for you or anyone else to recreate it.

Here is a complete `README.md` file based on the notes and commands you've provided. It's organized logically from infrastructure setup to application deployment.

---

# Personal Data Platform on K3s

This project documents the step-by-step process of building a modern, personal data platform on a multi-node K3s cluster. The platform includes MinIO for object storage, Apache Iceberg with a REST Catalog for table formatting, and Trino as the distributed SQL query engine.

## Table of Contents

1.  [Architecture Overview](#1-architecture-overview)
2.  [Prerequisites](#2-prerequisites)
3.  [Cluster Installation (K3s)](#3-cluster-installation-k3s)
    *   [Master Node Setup](#master-node-setup)
    *   [Worker Nodes Setup](#worker-nodes-setup)
    *   [Cluster Cleanup](#cluster-cleanup)
4.  [Core Infrastructure Deployment](#4-core-infrastructure-deployment)
    *   [NGINX Ingress Controller](#nginx-ingress-controller)
    *   [External NGINX Load Balancer](#external-nginx-load-balancer)
5.  [Application Deployment](#5-application-deployment)
    *   [MinIO Object Storage](#minio-object-storage)
    *   [Iceberg REST Catalog with PostgreSQL](#iceberg-rest-catalog-with-postgresql)
    *   [Trino SQL Engine](#trino-sql-engine)
6.  [Client Configuration](#6-client-configuration)

---

### 1. Architecture Overview

The platform consists of several layers running on a K3s cluster:

-   **Infrastructure:** A 5-VM setup on Hyper-V (1 Load Balancer, 1 K3s Master, 3 K3s Workers).
-   **Networking:** An external NGINX load balancer directs traffic to an NGINX Ingress Controller within the cluster, which handles routing to services.
-   **Storage:** MinIO provides an S3-compatible object store for our data lake, using persistent volumes.
-   **Catalog:** An Iceberg REST Catalog, backed by a PostgreSQL database, manages table metadata.
-   **Compute:** A Trino cluster provides a distributed SQL engine to query the data.

### 2. Prerequisites

-   **5 Virtual Machines** with Ubuntu installed.
-   **Static IP addresses** configured for all VMs.
-   **Local `hosts` file** configured to resolve hostnames to the external load balancer's IP.

**VM IP Allocation:**
```
192.168.1.20   vm-lb             # External NGINX Load Balancer
192.168.1.7    hyper-vm-b        # K3s Master Node
192.168.1.10   hyper-vm-1        # K3s Worker Node 1
192.168.1.11   hyper-vm-2        # K3s Worker Node 2
192.168.1.12   hyper-vm-3        # K3s Worker Node 3
```

### 3. Cluster Installation (K3s)

We will install K3s version `v1.31` and disable the default Traefik ingress controller in favor of NGINX.

#### Master Node Setup

Run the following command on the master node (`hyper-vm-b`):

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL=v1.31 sh -s - --cluster-init --token k3scluster --disable traefik --disable servicelb
```

After installation, copy the kubeconfig file to your home directory to use `kubectl`:

```bash
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
# If accessing from an external machine, edit ~/.kube/config and
# replace the server IP from 127.0.0.1 to the master node's actual IP (192.168.1.7).
```

#### Worker Nodes Setup

Run the following command on each worker node (`hyper-vm-1`, `hyper-vm-2`, `hyper-vm-3`):

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL=v1.31 K3S_URL=https://192.168.1.7:6443 K3S_TOKEN=k3scluster sh -
```

#### Cluster Cleanup

To uninstall K3s completely:
-   **On the master node:** `/usr/local/bin/k3s-uninstall.sh`
-   **On each worker node:** `/usr/local/bin/k3s-agent-uninstall.sh`

### 4. Core Infrastructure Deployment

#### NGINX Ingress Controller

This controller will manage traffic routing inside the Kubernetes cluster.

```bash
# Install the NGINX Ingress Controller via Helm
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=30080 \
  --set controller.service.nodePorts.https=30443
```

#### External NGINX Load Balancer

On the dedicated load balancer VM (`vm-lb`), configure NGINX to distribute traffic to the K3s worker nodes' `NodePort`.

Create `/etc/nginx/conf.d/k3s-ingress.conf`:
```nginx
upstream k3s_nodes {
    server 192.168.1.7:30080;
    server 192.168.1.10:30080;
    server 192.168.1.11:30080;
    server 192.168.1.12:30080;
}

server {
    listen 80;
    server_name _; # Listen for any hostname

    # Allow large file uploads for MinIO
    client_max_body_size 1G;

    location / {
        proxy_pass http://k3s_nodes;

        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Headers required for WebSocket support (for MinIO Console)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
Then test and reload NGINX: `sudo nginx -t && sudo systemctl reload nginx`.

### 5. Application Deployment

#### MinIO Object Storage

1.  **Add Helm repository:**
    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo update
    ```2.  **Deploy MinIO** using a `minio-values.yaml` file and an `minio-ingress.yaml` file.
    ```bash
    # Deploy MinIO
    helm upgrade --install minio -n minio bitnami/minio \
      --create-namespace \
      -f minio/minio-values.yaml \
      --version 14.6.0

    # Apply Ingress rules
    kubectl apply -f minio/minio-ingress.yaml
    ```

#### Iceberg REST Catalog with PostgreSQL

1.  **Deploy PostgreSQL** for the catalog's backend using a `postgres-values.yaml` file.
    ```bash
    helm upgrade --install postgres bitnami/postgresql \
      --namespace catalog \
      --create-namespace \
      -f postgres/postgres-values.yaml
    ```2.  **Deploy the Iceberg REST Catalog** and its Ingress using Kubernetes manifests.
    ```bash
    kubectl apply -f iceberg/iceberg.yaml
    kubectl apply -f iceberg/iceberg-ingress.yaml
    ```

#### Trino SQL Engine

1.  **Add Helm repository:**
    ```bash
    helm repo add trino https://trinodb.github.io/charts/
    helm repo update
    ```
2.  **Deploy Trino** using a `trino-values.yaml` file and a `trino-ingress.yaml` file.
    ```bash
    # Deploy Trino
    helm upgrade --install trino trino/trino \
      --namespace trino \
      --create-namespace \
      -f trino/trino-values.yaml

    # Apply Ingress rules
    kubectl apply -f trino/trino-ingress.yaml
    ```

### 6. Client Configuration

To access the deployed services from your local machine (e.g., with DBeaver or `pyiceberg`), edit your local `hosts` file (`C:\Windows\System32\drivers\etc\hosts` on Windows or `/etc/hosts` on Linux/macOS).

```
# Point all service hostnames to the external load balancer IP
192.168.1.20   minio.local minio-api.local iceberg-catalog.local trino.local
```

You can now connect to your services:
-   **MinIO Console:** `http://minio.local`
-   **Trino UI:** `http://trino.local`
-   **DBeaver/Trino CLI:** Server URL `http://trino.local`
-   **PyIceberg:** Catalog URI `http://iceberg.local`