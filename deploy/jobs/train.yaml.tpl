name: train-model
project_id: $PROJECT_ID
compute_config: $CLUSTER_COMPUTE_NAME
cluster_env: $CLUSTER_ENV_ID
runtime_env:
  working_dir: .
  upload_path: $UPLOAD_PATH
entrypoint: bash deploy/jobs/train.sh
max_retries: 0