
📘 Cisco Log Monitoring  Project Documentation


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

SSH Agent

🌐 Jenkins Credentials

dockerhub-creds → Docker Hub credentials (username & password)

ec2-ssh-key → SSH private key for EC2 access

ubuntu → EC2 user credentials

📄 CI/CD Pipelines

Two pipelines are configured:

Pipeline 1 (Local Server) → log-monitoring-generator & log-monitoring-listener

Pipeline 2 (Cloud EC2 Server) → log-collector, log-ui, and all persistor services

Pipeline 1
<img width="1920" height="1080" alt="Screenshot from 2025-09-16 14-19-32" src="https://github.com/user-attachments/assets/9f882ba4-821d-4270-9ebe-5e5e1b35912c" />


📦 docker-compose.cloud.yml

# docker-compose.cloud.yml
# (No "version:" key to avoid the Compose deprecation warning)

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: logs_user
      POSTGRES_PASSWORD: logs_pass
      POSTGRES_DB: logsdb
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  log-collector:
    build: ./log-collector
    container_name: log-pipeline-log-collector
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=logsdb
      - POSTGRES_USER=logs_user
      - POSTGRES_PASSWORD=logs_pass
      # Persistor hostnames (if collector needs to call them)
      - PERSISTOR_AUTH=persistor-auth
      - PERSISTOR_PAYMENT=persistor-payment
      - PERSISTOR_SYSTEM=persistor-system
      - PERSISTOR_APPLICATION=persistor-application
      - PERSISTOR_PORT=6000
    depends_on:
      - postgres
    volumes:
      - collector-data:/data
    ports:
      - "5002:5002"    # expose collector to the internet (EC2)
    restart: unless-stopped

  persistor-auth:
    build: ./persistor-auth
    container_name: log-pipeline-persistor-auth
    environment:
      - STORE_FILE=/data/auth_logs.json
    volumes:
      - persistor-auth-data:/data
    restart: unless-stopped

  persistor-payment:
    build: ./persistor-payment
    container_name: log-pipeline-persistor-payment
    environment:
      - STORE_FILE=/data/payment_logs.json
    volumes:
      - persistor-payment-data:/data
    restart: unless-stopped

  persistor-system:
    build: ./persistor-system
    container_name: log-pipeline-persistor-system
    environment:
      - STORE_FILE=/data/system_logs.json
    volumes:
      - persistor-system-data:/data
    restart: unless-stopped

  persistor-application:
    build: ./persistor-application
    container_name: log-pipeline-persistor-application
    environment:
      - STORE_FILE=/data/application_logs.json
    volumes:
      - persistor-application-data:/data
    restart: unless-stopped

  log-ui:
    build: ./log-ui
    container_name: log-pipeline-log-ui
    # UI calls /api/* (nginx proxy in log-ui will forward to log-collector)
    ports:
      - "80:80"        # UI available on EC2 public IP:80
    depends_on:
      - log-collector
    restart: unless-stopped

volumes:
  pgdata:
  collector-data:
  persistor-auth-data:
  persistor-payment-data:
  persistor-system-data:
  persistor-application-data:


📑 Jenkinsfile-cloud
pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-creds') // Jenkins creds (username+password)
        DOCKERHUB_REPO = "tharak397"
        APP_NAME = "log-monitoring"
        TAG = "latest"
        GIT_REPO = "https://github.com/venkattharakram/Logs_with_clientName.git"
        EC2_HOST = "ubuntu@13.201.64.104"   // change this to your EC2 public IP/DNS
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'master', url: "${GIT_REPO}"
            }
        }

        stage('Docker Login') {
            steps {
                sh """
                  echo $DOCKERHUB_CREDENTIALS_PSW | docker login -u $DOCKERHUB_CREDENTIALS_USR --password-stdin
                """
            }
        }

        stage('Build & Push Docker Images') {
            steps {
                script {
                    // These are the services with build context in docker-compose.cloud.yml
                    def services = [
                        "log-collector",
                        "persistor-auth",
                        "persistor-payment",
                        "persistor-system",
                        "persistor-application",
                        "log-ui"
                    ]

                    for (s in services) {
                        sh """
                          echo "🚀 Building image for ${s}"
                          docker build -t $DOCKERHUB_REPO/${APP_NAME}-${s}:$TAG ${s}/
                          docker push $DOCKERHUB_REPO/${APP_NAME}-${s}:$TAG
                        """
                    }
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent (credentials: ['ec2-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${EC2_HOST} '
                          if [ ! -d "/home/ubuntu/Logs_with_clientName" ]; then
                              git clone ${GIT_REPO}
                          fi &&
                          cd /home/ubuntu/Logs_with_clientName &&
                          git pull origin master &&

                          # Replace build with image in docker-compose.cloud.yml
                          sed -i "s|build: ./log-collector|image: $DOCKERHUB_REPO/${APP_NAME}-log-collector:$TAG|" docker-compose.cloud.yml
                          sed -i "s|build: ./persistor-auth|image: $DOCKERHUB_REPO/${APP_NAME}-persistor-auth:$TAG|" docker-compose.cloud.yml
                          sed -i "s|build: ./persistor-payment|image: $DOCKERHUB_REPO/${APP_NAME}-persistor-payment:$TAG|" docker-compose.cloud.yml
                          sed -i "s|build: ./persistor-system|image: $DOCKERHUB_REPO/${APP_NAME}-persistor-system:$TAG|" docker-compose.cloud.yml
                          sed -i "s|build: ./persistor-application|image: $DOCKERHUB_REPO/${APP_NAME}-persistor-application:$TAG|" docker-compose.cloud.yml
                          sed -i "s|build: ./log-ui|image: $DOCKERHUB_REPO/${APP_NAME}-log-ui:$TAG|" docker-compose.cloud.yml

                          sudo docker compose -f docker-compose.cloud.yml down
                          sudo docker compose -f docker-compose.cloud.yml pull
                          sudo docker compose -f docker-compose.cloud.yml up -d
                        '
                    """
                }
            }
        }
    }

    post {
        always {
            echo "✅ Pipeline finished successfully!"
        }
    }
}

🛠️ Pipeline Stages

Checkout → Pull latest repo

Docker Login → Authenticate to Docker Hub

Build & Push Images → Collector, Persistors, UI

Deploy to EC2 → SSH into server, update Compose, restart containers

🛠️ Pipeline Stages

Checkout → Pull latest repo

Docker Login → Authenticate to Docker Hub

Build & Push Images → Collector, Persistors, UI

Deploy to EC2 → SSH into server, update Compose, restart containers

Cloud pipeline execution
<img width="1920" height="1080" alt="Screenshot from 2025-09-16 14-22-40" src="https://github.com/user-attachments/assets/99ed3ba3-b879-48be-97e0-45e04b864c1c" />


EC2 running containers

Pending 



☁️ Pipeline 2: local Deployment
<img width="1920" height="1080" alt="Screenshot from 2025-09-16 14-23-55" src="https://github.com/user-attachments/assets/cd057371-2c66-4ddb-a54b-07dafbb2bb64" />

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

pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-creds') // Jenkins credential ID
        DOCKERHUB_REPO = "tharak397"
        APP_NAME = "log-monitoring"
        TAG = "latest"   // you can also use "${env.BUILD_NUMBER}" for unique tags
    }

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/venkattharakram/Logs_with_clientName.git', branch: 'master'
            }
        }

        stage('Docker Login') {
            steps {
                sh """
                echo $DOCKERHUB_CREDENTIALS_PSW | docker login -u $DOCKERHUB_CREDENTIALS_USR --password-stdin
                """
            }
        }

        stage('Build & Tag Docker Images') {
            steps {
                script {
                    // Build log-listener
                    sh """
                    docker build -t $DOCKERHUB_REPO/${APP_NAME}-listener:$TAG ./log-listener
                    """

                    // Build log-generator
                    sh """
                    docker build -t $DOCKERHUB_REPO/${APP_NAME}-generator:$TAG ./log-generator
                    """
                }
            }
        }

        stage('Push to DockerHub') {
            steps {
                script {
                    sh "docker push $DOCKERHUB_REPO/${APP_NAME}-listener:$TAG"
                    sh "docker push $DOCKERHUB_REPO/${APP_NAME}-generator:$TAG"
                }
            }
        }

        stage('Update Docker Compose') {
            steps {
                script {
                    // Replace local build with DockerHub images dynamically
                    sh """
                    sed -i 's|build: ./log-listener|image: $DOCKERHUB_REPO/${APP_NAME}-listener:$TAG|' docker-compose.local.yml
                    sed -i 's|build: ./log-generator|image: $DOCKERHUB_REPO/${APP_NAME}-generator:$TAG|' docker-compose.local.yml
                    """
                }
            }
        }

        stage('Docker Compose Down') {
            steps {
                sh 'docker compose -f docker-compose.local.yml down'
            }
        }

        stage('Docker Compose Up') {
            steps {
                sh 'docker compose -f docker-compose.local.yml up -d'
            }
        }
    }

    post {
        always {
            sh 'docker logout'
        }
    }
}

🛠️ Pipeline Stages
Checkout → Pull latest GitHub repo

Docker Login → Authenticate to Docker Hub

Build & Tag Images → Build listener & generator

Push Images → Push to Docker Hub

Update Compose File → Replace build: with image:

Deploy → Restart containers with new images

Pipeline execution stages
<img width="1920" height="1080" alt="Screenshot from 2025-09-16 14-11-36" src="https://github.com/user-attachments/assets/dea502e8-a703-430d-b768-b45e71185427" />


Running Docker containers
<img width="1920" height="1080" alt="Screenshot from 2025-09-16 14-12-04" src="https://github.com/user-attachments/assets/7a6cf4c4-3182-4cde-97cd-68f07363ac4b" />


Log Dashboard
<img width="1920" height="1080" alt="Screenshot from 2025-09-16 14-12-26" src="https://github.com/user-attachments/assets/785f526d-378f-4271-a6f1-660cf813994a" />





