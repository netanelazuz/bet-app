// ─────────────────────────────────────────────────────────────────────────────
// BET – Pipeline 1: CI + Build + Create MR
//
// Trigger : Push to dev branch (GitLab webhook — Push events, dev branch only)
//
// Stages:
//   1. Checkout   – clone the dev branch
//   2. Test       – run pytest inside the python container
//   3. Version    – determine next SemVer with git-cliff
//   4. Build & Push – build Docker image, tag :vX.Y.Z + :latest, push to Hub
//   5. Create MR  – open a GitLab Merge Request from dev → main (idempotent)
//
// Required Jenkins credentials:
//   dockerhub-creds  – Username/Password  (Docker Hub login)
//   gitlab-token     – Secret text        (GitLab PAT with api + write_repository)
//
// Agent pod:
//   - python  : tests, git-cliff, MR creation via GitLab API
//   - docker  : docker:27-cli talking to host daemon via mounted socket
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent {
        kubernetes {
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
        limits:
          cpu: 500m
          memory: 1Gi
    - name: docker
      image: docker:27-cli
      command: [cat]
      tty: true
      env:
        - name: DOCKER_HOST
          value: "unix:///var/run/docker.sock"
      volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
      resources:
        requests:
          cpu: 200m
          memory: 256Mi
        limits:
          cpu: 1000m
          memory: 512Mi
  volumes:
    - name: docker-sock
      hostPath:
        path: /var/run/docker.sock
"""
        }
    }

    environment {
        DOCKER_IMAGE      = 'netanelazuz/bet-app'
        GITLAB_API_URL    = 'https://gitlab.com/api/v4'
        GITLAB_PROJECT_ID = '77900502'   // predictions project numeric ID
        GIT_AUTHOR_NAME   = 'Jenkins CI'
        GIT_AUTHOR_EMAIL  = 'jenkins@bet.local'
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
                    echo "Branch: dev  |  Commit: ${env.GIT_COMMIT_SHORT}"
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
                    echo 'Tests failed — aborting pipeline. No image will be built and no MR will be created.'
                }
            }
        }

        // ── 3. Version ────────────────────────────────────────────────────────
        stage('Version') {
            steps {
                container('python') {
                    sh 'apt-get update -qq && apt-get install -y -qq git'
                    sh 'pip install --quiet git-cliff'
                    sh 'git config --global --add safe.directory "*"'
                    script {
                        def version = sh(
                            script: 'git cliff --bumped-version 2>/dev/null || echo "v0.1.0"',
                            returnStdout: true
                        ).trim()
                        if (!version.startsWith('v')) { version = "v${version}" }
                        env.APP_VERSION = version
                        echo "Next version: ${env.APP_VERSION}"
                    }
                }
            }
        }

        // ── 4. Build & Push ───────────────────────────────────────────────────
        stage('Build & Push') {
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

        // ── 5. Create MR ──────────────────────────────────────────────────────
        // Opens a GitLab MR from dev → main (idempotent: skips if one already exists).
        stage('Create MR') {
            steps {
                container('python') {
                    withCredentials([string(
                        credentialsId: 'gitlab-token',
                        variable: 'GITLAB_TOKEN'
                    )]) {
                        sh """
                            pip install --quiet requests

                            python3 - << 'PYEOF'
import requests, os, sys

api      = os.environ['GITLAB_API_URL']
proj     = os.environ['GITLAB_PROJECT_ID']
token    = os.environ['GITLAB_TOKEN']
version  = os.environ['APP_VERSION']
commit   = os.environ['GIT_COMMIT_SHORT']

headers = {'PRIVATE-TOKEN': token, 'Content-Type': 'application/json'}

# Check whether an open MR dev→main already exists
resp = requests.get(
    f'{api}/projects/{proj}/merge_requests',
    params={'state': 'opened', 'source_branch': 'dev', 'target_branch': 'main'},
    headers=headers, timeout=15
)
resp.raise_for_status()
existing = resp.json()

if existing:
    mr = existing[0]
    print(f"MR already open: !{mr['iid']}  {mr['web_url']}")
    sys.exit(0)

# Create a new MR
payload = {
    'source_branch': 'dev',
    'target_branch': 'main',
    'title': f'chore(release): deploy {version} ({commit})',
    'description': (
        f'Automated release MR created by Jenkins Pipeline 1.\\n\\n'
        f'- Image: `netanelazuz/bet-app:{version}`\\n'
        f'- Commit: `{commit}`\\n\\n'
        f'Approve and merge to trigger Pipeline 2 (Update Infra → ArgoCD deploy).'
    ),
    'remove_source_branch': False,
}
resp = requests.post(
    f'{api}/projects/{proj}/merge_requests',
    json=payload, headers=headers, timeout=15
)
resp.raise_for_status()
mr = resp.json()
print(f"MR created: !{mr['iid']}  {mr['web_url']}")
PYEOF
                        """
                    }
                }
            }
        }

    } // end stages

    post {
        success {
            echo "Pipeline 1 complete — ${env.DOCKER_IMAGE}:${env.APP_VERSION} pushed. MR dev→main opened."
        }
        failure {
            echo "Pipeline 1 failed. Check logs above."
        }
        always {
            script {
                try { deleteDir() } catch (e) { echo "Workspace cleanup skipped: ${e.message}" }
            }
        }
    }
}
