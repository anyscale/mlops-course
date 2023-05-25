name: madewithml-service
project_id: $PROJECT_ID
compute_config: $CLUSTER_COMPUTE_NAME
cluster_env: $CLUSTER_ENV_ID
ray_serve_config:
  import_path: deploy.services.service:entrypoint
  runtime_env:
    working_dir: .
    upload_path: $UPLOAD_PATH
    env_vars:
      RUN_ID: $RUN_ID