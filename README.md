📘 Cisco Demo Project Documentation
WAR Deployment to Minikube Clusters
🛠️ Prerequisites and Setup
Infrastructure

On-Premises Server → Ubuntu

AWS Cloud Server → EC2 Ubuntu instance

✅ Jenkins Installation
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/ | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt update
sudo apt install jenkins -y
sudo systemctl start jenkins
sudo systemctl enable jenkins

🐳 Docker Installation
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io -y

docker --version
docker compose version

🔀 Jenkins CI/CD Overview
🔌 Required Plugins

Docker Pipeline

Pipeline

Pipeline View

SSH Agent

🌐 Jenkins Credentials

dockerhub-creds → Docker Hub credentials (username & password)

ec2-ssh-key → SSH private key for EC2 access

ubuntu → EC2 user credentials

📄 CI/CD Pipelines

Two pipelines are configured:

Pipeline 1 (Local Server) → log-monitoring-generator & log-monitoring-listener

Pipeline 2 (Cloud EC2 Server) → log-collector, log-ui, and all persistor services

🚀 Pipeline 1: Local Log-Monitoring
📦 docker-compose.local.yml
version: "3.8"

services:
  log-listener:
    build: ./log-listener
    container_name: log-pipeline-log-listener
    ports:
      - "5001:5001"
    environment:
      - COLLECTOR_URL=http://13.201.64.104:5002/collect

  log-generator:
    build: ./log-generator
    container_name: log-pipeline-log-generator
    depends_on:
      - log-listener
    ports:
      - "5000:5000"
    environment:
      - LISTENER_URL=http://log-listener:5001/logs
      - CLIENT_NAME=venkat's macbook

📑 Jenkinsfile-local

Handles build, tag, push, and deployment of listener & generator.

Builds Docker images for both services.

Pushes to Docker Hub.

Updates docker-compose.local.yml.

Restarts containers with updated images.

🛠️ Pipeline Stages

Checkout → Pull latest GitHub repo

Docker Login → Authenticate to Docker Hub

Build & Tag Images → Build listener & generator

Push Images → Push to Docker Hub

Update Compose File → Replace build: with image:

Deploy → Restart containers with new images

📷 Screenshots:

Pipeline execution stages

Running Docker containers

Log Dashboard

☁️ Pipeline 2: Cloud Deployment (EC2)
📦 docker-compose.cloud.yml

Defines Postgres, Collector, Persistors, and Log-UI services.

Key services:

postgres (database)

log-collector (central service)

persistor-* (auth, payment, system, application)

log-ui (frontend dashboard)

📑 Jenkinsfile-cloud

Manages EC2 deployment:

Clones GitHub repo on EC2

Builds & pushes images to Docker Hub

Updates Compose file with image tags

Restarts containers on EC2

🛠️ Pipeline Stages

Checkout → Pull latest repo

Docker Login → Authenticate to Docker Hub

Build & Push Images → Collector, Persistors, UI

Deploy to EC2 → SSH into server, update Compose, restart containers

📷 Screenshots:

Cloud pipeline execution

EC2 running containers

Web UI on port 80

📊 Project Output

Log Generator produces application logs.

Log Listener forwards logs to the central Collector.

Persistor Services store categorized logs (auth, payment, system, application).

Log UI displays logs in a dashboard interface.
