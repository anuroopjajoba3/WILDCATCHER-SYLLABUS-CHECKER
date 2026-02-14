pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 1, unit: 'HOURS')
        timestamps()
    }
    environment {
        DOCKER_IMAGE = "nechecker:${BUILD_NUMBER}"
        APP_PORT = "8001"
    }
    stages {
        stage('Checkout') {
            steps {
                echo '🔄 Checking out code...'
                checkout scm
            }
        }
        stage('Install Dependencies') {
            steps {
                echo '📦 Installing dependencies...'
                sh 'pip install -r requirements.txt && pip install pytest pytest-cov flake8'
            }
        }
        stage('Unit Tests') {
            steps {
                echo '🧪 Running tests...'
                sh 'pytest tests/ -v --cov=. || true'
            }
        }
        stage('Build Docker Image') {
            steps {
                echo '🐳 Building Docker image...'
                sh 'docker build -t ${DOCKER_IMAGE} .'
            }
        }
        stage('Deploy to Dev') {
            when { branch 'develop' }
            steps {
                sh 'docker-compose up -d || true'
            }
        }
    }
    post {
        always { echo '✅ Pipeline complete!' }
        failure { echo '❌ Pipeline failed!' }
    }
}
