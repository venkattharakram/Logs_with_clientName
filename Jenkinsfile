pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/venkattharakram/Logs_with_clientName.git', branch: 'master'
            }
        }

        stage('Docker Compose Up') {
    steps {
        sh 'docker compose -f docker-compose.local.yml up -d'
    



                }
            }
        }
    }
