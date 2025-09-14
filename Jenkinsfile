pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/venkattharakram/Logs_with_clientName.git', branch: 'dev'
            }
        }

        stage('Docker Compose Up') {
            steps {
                script {
                    // run in detached mode so Jenkins doesn’t hang
                    sh 'sudo docker compose -f docker-compose.local.yml up -d'
                }
            }
        }
    }
}
