pipeline {
    agent { docker 'python:2.7.10' }
    stages {
        stage('build') {
            steps {
                sh 'python --version'
                sh 'python test_reduce_music.py'
            }
        }
    }
}
