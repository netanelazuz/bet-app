// ─────────────────────────────────────────────────────────────────────────────
// BET – CI Pipeline
//
// Stages:
//   1. Checkout        – clone predictions repo
//   2. Test            – run pytest inside the app image
//   3. Version         – determine next SemVer with git-cliff
//   4. Build & Push    – build Docker image, tag :vX.Y.Z + :latest, push to Hub
//   5. Update Infra    – bump image.tag in bet-infra/helm/bet/values.yaml
//                        (ArgoCD auto-syncs from there)
//
// Required Jenkins credentials:
//   dockerhub-creds   – Username/Password  (Docker Hub login)
//   gitlab-token      – Secret text        (GitLab PAT with api + write_repository)
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent {
        kubernetes {
            label 'bet-agent'
            defaultContainer 'jnlp'
            yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: python
      image: python:3.12-slim
      command: [cat]
      tty: true
      resources:
        requests:
          cpu: 200m
          memory: 512Mi
    - name: docker
      image: docker:24-dind
      securityContext:
        privileged: true
      env:
        - name: DOCKER_TLS_CERTDIR
          value: ""
      volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
  volumes:
    - name: docker-sock
      hostPath:
        path: /var/run/docker.sock
"""
        }
    }

    environment {
        DOCKER_IMAGE     = 'netanelazuz/bet-app'
        INFRA_REPO_URL   = 'https://gitlab.com/sela-1119/students/netanelazuz/final_project/bet-infra.git'
        INFRA_VALUES     = 'helm/bet/values.yaml'
        GIT_AUTHOR_NAME  = 'Jenkins CI'
        GIT_AUTHOR_EMAIL = 'jenkins@bet.local'
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    stages {

        // ── 1. Checkout ───────────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    echo "Commit: ${env.GIT_COMMIT_SHORT}"
                }
            }
        }

        // ── 2. Test ───────────────────────────────────────────────────────────
        stage('Test') {
            steps {
                container('python') {
                    sh '''
                        pip install --quiet -r requirements.txt
                        python run_tests.py
                    '''
                }
            }
            post {
                failure {
                    echo 'Tests failed — aborting pipeline. No image will be built.'
                }
            }
        }

        // ── 3. Version ────────────────────────────────────────────────────────
        // git-cliff reads Conventional Commits and bumps the version.
        // If no tags exist yet it defaults to v0.1.0.
        stage('Version') {
            steps {
                container('python') {
                    sh 'pip install --quiet git-cliff'
                    script {
                        def version = sh(
                            script: '''
                                git fetch --tags
                                git cliff --bumped-version 2>/dev/null || echo "v0.1.0"
                            ''',
                            returnStdout: true
                        ).trim()

                        // Normalise: ensure leading 'v'
                        if (!version.startsWith('v')) { version = "v${version}" }

                        env.APP_VERSION = version
                        echo "Next version: ${env.APP_VERSION}"
                    }
                }
            }
        }

        // ── 4. Build & Push ───────────────────────────────────────────────────
        stage('Build & Push') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                container('docker') {
                    withCredentials([usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )]) {
                        sh """
                            docker login -u \$DOCKER_USER -p \$DOCKER_PASS

                            docker build \\
                                -t ${DOCKER_IMAGE}:${env.APP_VERSION} \\
                                -t ${DOCKER_IMAGE}:latest \\
                                -f docker/Dockerfile .

                            docker push ${DOCKER_IMAGE}:${env.APP_VERSION}
                            docker push ${DOCKER_IMAGE}:latest

                            docker logout
                        """
                    }
                }
            }
        }

        // ── 5. Update Infra ───────────────────────────────────────────────────
        // Writes the new image tag into bet-infra → ArgoCD auto-syncs.
        stage('Update Infra') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                container('python') {
                    withCredentials([string(
                        credentialsId: 'gitlab-token',
                        variable: 'GITLAB_TOKEN'
                    )]) {
                        sh """
                            pip install --quiet ruamel.yaml

                            # Clone infra repo
                            git clone https://oauth2:\$GITLAB_TOKEN@\$(echo ${INFRA_REPO_URL} | sed 's|https://||') /tmp/bet-infra
                            cd /tmp/bet-infra

                            # Bump image.tag using Python (preserves YAML comments)
                            python3 - <<'PYEOF'
from ruamel.yaml import YAML
import sys

path = '${INFRA_VALUES}'
version = '${env.APP_VERSION}'

yaml = YAML()
yaml.preserve_quotes = True
with open(path) as f:
    data = yaml.load(f)

data['image']['tag'] = version
print(f'Updated image.tag to {version}')

with open(path, 'w') as f:
    yaml.dump(data, f)
PYEOF

                            # Commit and push
                            git config user.name  "${GIT_AUTHOR_NAME}"
                            git config user.email "${GIT_AUTHOR_EMAIL}"
                            git add ${INFRA_VALUES}
                            git commit -m "chore(release): bump image.tag to ${env.APP_VERSION} [skip ci]"
                            git push
                        """
                    }
                }
            }
        }

    } // end stages

    post {
        success {
            echo "Pipeline complete — ${env.DOCKER_IMAGE}:${env.APP_VERSION} deployed."
        }
        failure {
            echo "Pipeline failed at stage '${env.STAGE_NAME}'. Check logs above."
        }
        always {
            cleanWs()
        }
    }
}
