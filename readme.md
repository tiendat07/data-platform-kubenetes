# Personal Data Platform on K3s

This project documents the step-by-step process of building a modern, scalable data platform on a K3s Kubernetes cluster. The platform includes object storage (MinIO), a structured data layer (Iceberg), a distributed SQL query engine (Trino), and a general-purpose processing engine (Spark), all running on a multi-node cluster.

This guide is structured to be a complete reference for recreating the environment.

## Table of Contents
1.  [Environment Setup](#1-environment-setup)
2.  [K3s Cluster Installation](#2-k3s-cluster-installation)
3.  [External Load Balancer Setup](#3-external-load-balancer-setup)
4.  [Core Services Deployment (Helm)](#4-core-services-deployment-helm)
5.  [Application Deployment](#5-application-deployment)
6.  [(Optional) GPU Integration (via WSL2)](#6-optional-gpu-integration-via-wsl2)
7.  [Client Configuration](#7-client-configuration)

---

### **1. Environment Setup**

This project uses a 5-VM setup, with 4 VMs for the K3s cluster and 1 VM acting as a dedicated external load balancer.

**VM IP Allocation:**
-   `192.168.1.20`: `vm-lb` (NGINX Load Balancer)
-   `192.168.1.7`: `hyper-vm-b` (K3s Master Node)
-   `192.168.1.10`: `hyper-vm-1` (K3s Worker Node)
-   `192.168.1.11`: `hyper-vm-2` (K3s Worker Node)
-   `192.168.1.12`: `hyper-vm-3` (K3s Worker Node)

---

### **2. K3s Cluster Installation**

We will use K3s for a lightweight, certified Kubernetes distribution. We specify a version channel for stability and disable the default Traefik ingress controller to install our own.

**On the Master Node (`hyper-vm-b`):**
```bash
# Install K3s master, disabling the default servicelb and traefik
curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL=v1.31 sh -s - \
  --cluster-init --token k3scluster --disable traefik --disable servicelb

# Set up kubeconfig for local kubectl access
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
# Note: To access from an external machine, edit ~/.kube/config and
# replace the server IP '127.0.0.1' with the master node's actual IP '192.168.1.7'.
```

**On each Worker Node (`hyper-vm-1`, `hyper-vm-2`, `hyper-vm-3`):**
```bash
# Join the worker node to the cluster
curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL=v1.31 K3S_URL=https://192.168.1.7:6443 K3S_TOKEN=k3scluster sh -
```

**Uninstall Commands (for reference):**
-   Master: `/usr/local/bin/k3s-uninstall.sh`
-   Agent: `/usr/local/bin/k3s-agent-uninstall.sh`

---

### **3. External Load Balancer Setup**

We will use NGINX on a dedicated VM (`vm-lb`) to load balance traffic across the Kubernetes worker nodes. This provides a single, stable entry point for all services.

**On the Load Balancer VM (`vm-lb`):**

1.  **Install NGINX:**
    ```bash
    sudo apt-get update
    sudo apt-get install -y nginx
    ```

2.  **Configure NGINX:** Create a configuration file at `/etc/nginx/conf.d/k3s-ingress.conf`.
    ```nginx
    # /etc/nginx/conf.d/k3s-ingress.conf

    upstream k3s_ingress_nodes {
        # Point to the NodePort on all K3s worker nodes
        server 192.168.1.10:30080;
        server 192.168.1.11:30080;
        server 192.168.1.12:30080;
    }

    server {
        listen 80;
        server_name _; # Act as the default server

        location / {
            proxy_pass http://k3s_ingress_nodes;

            # Standard proxy headers to preserve client info
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```

3.  **Test and Reload NGINX:**
    ```bash
    sudo nginx -t
    sudo systemctl reload nginx
    ```

---

### **4. Core Services Deployment (Helm)**

We use Helm to manage the deployment of our core infrastructure services. All commands are run from the `k3s-master` node.

#### **4.1. NGINX Ingress Controller**

This will be the internal load balancer for our cluster, receiving traffic from the external `vm-lb`.

```bash
# Add the ingress-nginx Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install the controller, exposing it via a static NodePort (30080)
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=30080 \
  --set controller.service.nodePorts.https=30443
```

#### **4.2. PostgreSQL Database (for Iceberg Catalog)**

```bash
# Add the Bitnami Helm repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install PostgreSQL using a values file for configuration
# (See postgres/postgres-values.yaml for details on user, password, db)
helm upgrade --install postgres bitnami/postgresql \
  --namespace catalog \
  --create-namespace \
  -f postgres/postgres-values.yaml
```

#### **4.3. MinIO Object Storage**

```bash
# Install MinIO using a values file
# (See minio/minio-values.yaml for details on credentials, service type, etc.)
helm upgrade --install minio bitnami/minio \
  --namespace minio \
  --create-namespace \
  -f minio/minio-values.yaml \
  --version 14.6.0
```

#### **4.4. Trino SQL Engine**

```bash
# Add the Trino Helm repository
helm repo add trino https://trinodb.github.io/charts/
helm repo update

# Install Trino using a values file
# (See trino/trino-values.yaml for details on catalogs and configs)
helm upgrade --install trino trino/trino \
  --namespace trino \
  --create-namespace \
  -f trino/trino-values.yaml
```

---

### **5. Application Deployment**

These are the Kubernetes resources that define our custom applications and expose them via Ingress.

#### **5.1. Iceberg REST Catalog**

This is a simple web service that provides a REST API for managing Iceberg metadata.

```bash
# Deploy the Iceberg REST Catalog service and its Ingress rule
kubectl apply -f iceberg/iceberg.yaml
kubectl apply -f iceberg/iceberg-ingress.yaml
```

#### **5.2. Ingress Rules**

We use Ingress resources to route traffic from the NGINX Ingress Controller to our services based on hostnames.

```bash
# Apply Ingress rules for MinIO and Trino
kubectl apply -f minio/minio-ingress.yaml
kubectl apply -f trino/trino-ingress.yaml
```

---

### **6. (Optional) GPU Integration (via WSL2)**

This advanced section details how to add your Windows PC's GPU to the cluster by using WSL2 as a GPU-enabled worker node. This allows you to run GPU-accelerated workloads like Spark with RAPIDS.

**Note:** This method uses the manual NVIDIA Device Plugin, as the full GPU Operator is not supported on WSL2.

#### **6.1. Prepare Windows and WSL2**

1.  **Install/Update NVIDIA Drivers:** Ensure you have the latest drivers for your GPU installed on your Windows host.
2.  **Update WSL2:** Open PowerShell as Admin and run `wsl --update`.
3.  **Install Ubuntu on WSL2:** Install a distribution like "Ubuntu 22.04 LTS" from the Microsoft Store.
4.  **Verify GPU Access in WSL2:** Open your Ubuntu WSL terminal and run `nvidia-smi`. The output should match the `nvidia-smi` command on Windows. **Do not install drivers inside WSL2.**

#### **6.2. Prepare the WSL2 Instance**

1.  **Install NVIDIA Container Toolkit:** Inside your Ubuntu WSL terminal, install the toolkit.
    ```bash
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    ```

2.  **Join WSL2 Node to Cluster:** Run this command inside the WSL2 terminal.
    ```bash
    curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL=v1.31 K3S_URL=https://192.168.1.7:6443 K3S_TOKEN=k3scluster sh -
    ```

#### **6.3. Deploy the NVIDIA Device Plugin**

1.  **Apply Nvidia Device Plugin:**
    ```bash
    kubectl apply -f nvidia/nvidia-device-plugin.yaml
    ```

2.  **Label GPU node in Cluster:**
    ```bash
    kubectl label node <wsl-node-name> accelerator=nvidia --overwrite
    ```

3.  **Verify GPU is Available:** Check that your WSL2 node now advertises the GPU resource.
    ```bash
    kubectl describe node <wsl-node-name> | grep -A1 -B1 'nvidia\.com/gpu'
    ```
    Look for `nvidia.com/gpu: 1` under the `Allocatable` section.

---

### **7. Client Configuration**

To access the services from your local machine (e.g., your Windows PC), you need to edit your local `hosts` file to point the service hostnames to the external load balancer.

**Edit your `hosts` file:**
-   Windows: `C:\Windows\System32\drivers\etc\hosts`
-   Linux/macOS: `/etc/hosts`

Add the following line:
```
# Point all service hostnames to the external load balancer IP
192.168.1.20   minio.local minio-api.local iceberg.local trino.local
```

You can now connect to your services:
-   **MinIO Console:** `http://minio.local`
-   **Trino UI:** `http://trino.local`
-   **DBeaver/Trino CLI:** Server URL `http://trino.local`
-   **PyIceberg:** Catalog URI `http://iceberg.local`