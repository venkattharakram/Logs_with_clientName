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
                script {
                    // run in detached mode so Jenkins doesn’t hang
                    sh 'docker-compose -f docker-compose.local.yml up -d --build'
                }
            }
        }
    }

    post {
        always {
            script {
                // bring services down after pipeline (optional)
                sh 'docker-compose -f docker-compose.local.yml down || true'
            }
        }
    }
}
