# 📘 Cisco Log Monitoring Project

This project demonstrates a complete **CI/CD pipeline** for log monitoring applications deployed across **on-premises (local Ubuntu server)** and **AWS EC2 Ubuntu instances**, using **Jenkins, Docker, and Docker Compose**.

---

## 🛠️ Prerequisites and Setup

### Infrastructure
- **On-Premises Server** → Ubuntu (Local Jenkins + Docker host)
- **AWS Cloud Server** → EC2 Ubuntu instance

---

### ✅ Jenkins Installation
```bash
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/ | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt update
sudo apt install jenkins -y
sudo systemctl start jenkins
sudo systemctl enable jenkins

### ✅Docker Installation
bash
Copy code
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

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
The project uses two pipelines:
Pipeline 1 (Cloud EC2 Server) → Deploys log-collector, log-ui, and persistor services


Pipeline 2 (Local Server) → Deploys log-monitoring-generator & log-monitoring-listener



☁️ Pipeline 2: Cloud Deploymen Deploys log-collector, log-ui, and persistor services

📦 docker-compose.cloud.yml
# docker-compose.cloud.yml
# (No "version:" key to avoid the Compose deprecation warning)
yaml
Copy code
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
      - PERSISTOR_AUTH=persistor-auth
      - PERSISTOR_PAYMENT=persistor-payment
      - PERSISTOR_SYSTEM=persistor-system
      - PERSISTOR_APPLICATION=persistor-application
      - PERSISTOR_PORT=6000
    depends_on:
      - postgres
    ports:
      - "5002:5002"
    volumes:
      - collector-data:/data
    restart: unless-stopped

  persistor-auth:
    build: ./persistor-auth
    environment:
      - STORE_FILE=/data/auth_logs.json
    volumes:
      - persistor-auth-data:/data
    restart: unless-stopped

  persistor-payment:
    build: ./persistor-payment
    environment:
      - STORE_FILE=/data/payment_logs.json
    volumes:
      - persistor-payment-data:/data
    restart: unless-stopped

  persistor-system:
    build: ./persistor-system
    environment:
      - STORE_FILE=/data/system_logs.json
    volumes:
      - persistor-system-data:/data
    restart: unless-stopped

  persistor-application:
    build: ./persistor-application
    environment:
      - STORE_FILE=/data/application_logs.json
    volumes:
      - persistor-application-data:/data
    restart: unless-stopped

  log-ui:
    build: ./log-ui
    ports:
      - "80:80"
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
groovy
Copy code
pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-creds')
        DOCKERHUB_REPO = "tharak397"
        APP_NAME = "log-monitoring"
        TAG = "latest"
        GIT_REPO = "https://github.com/venkattharakram/Logs_with_clientName.git"
        EC2_HOST = "ubuntu@13.201.64.104"
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
                    def services = ["log-collector","persistor-auth","persistor-payment","persistor-system","persistor-application","log-ui"]
                    for (s in services) {
                        sh """
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



💻 Pipeline 1: Local Deployment
📦 docker-compose.local.yml
yaml
Copy code
version: "3.8"
services:
  log-listener:
    build: ./log-listener
    ports:
      - "5001:5001"
    environment:
      - COLLECTOR_URL=http://13.201.64.104:5002/collect

  log-generator:
    build: ./log-generator
    depends_on:
      - log-listener
    ports:
      - "5000:5000"
    environment:
      - LISTENER_URL=http://log-listener:5001/logs
      - CLIENT_NAME=venkat's macbook


📑 Jenkinsfile-local
groovy
Copy code
pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-creds')
        DOCKERHUB_REPO = "tharak397"
        APP_NAME = "log-monitoring"
        TAG = "latest"
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
                    sh "docker build -t $DOCKERHUB_REPO/${APP_NAME}-listener:$TAG ./log-listener"
                    sh "docker build -t $DOCKERHUB_REPO/${APP_NAME}-generator:$TAG ./log-generator"
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
                sh """
                sed -i 's|build: ./log-listener|image: $DOCKERHUB_REPO/${APP_NAME}-listener:$TAG|' docker-compose.local.yml
                sed -i 's|build: ./log-generator|image: $DOCKERHUB_REPO/${APP_NAME}-generator:$TAG|' docker-compose.local.yml
                """
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
📊 Monitoring & UI
Local Pipeline (Generator + Listener) sends logs → Cloud Pipeline (Collector + Persistors + Postgres)

UI available at → http://<EC2-Public-IP>

Collector API exposed at → http://<EC2-Public-IP>:5002/collect

📸 Screenshots
Pipeline 1 Execution


Pipeline 2 Execution


EC2 Running Containers


Log Dashboard


✅ Summary
Pipeline 1 (Local): Builds, pushes, and runs log-generator & log-listener

Pipeline 2 (Cloud): Builds, pushes, and runs log-collector, log-ui, and persistor services on EC2

End-to-end log monitoring system with UI and database storage
