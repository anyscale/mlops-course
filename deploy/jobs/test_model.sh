#!/bin/bash
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install ".[dev]"
python3 -m pip install -U "ray[air] @ https://s3-us-west-2.amazonaws.com/ray-wheels/latest/ray-3.0.0.dev0-cp310-cp310-manylinux2014_x86_64.whl"

# Get run ID
if [[ -z "${run_id}" ]]; then  # if RUN_ID is set use it, else get the best run
    run_id=$(python src/madewithml/predict.py get-best-run-id --experiment-name $experiment_name --metric val_loss --mode ASC)
fi

# Test model
RESULTS_FILE=test_model_results.txt
pytest --run-id=$run_id tests/model --verbose --disable-warnings > $RESULTS_FILE

# Save to S3
python deploy/utils.py save-to-s3 \
    --file-path $RESULTS_FILE \
    --bucket-name $s3_bucket_name \
    --bucket-path $username/results/$commit_id/$RESULTS_FILE