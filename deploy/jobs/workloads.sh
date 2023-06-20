#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$PWD

# Test data
export RESULTS_FILE=test_data_results.txt
export DATASET_LOC="https://raw.githubusercontent.com/GokuMohandas/Made-With-ML/main/datasets/madewithml/dataset.csv"
pytest --dataset-loc=$DATASET_LOC tests/data --verbose --disable-warnings > $RESULTS_FILE
cat $RESULTS_FILE

# Test code
export RESULTS_FILE=test_code_results.txt
python -m pytest tests/code --verbose --disable-warnings > $RESULTS_FILE
cat $RESULTS_FILE

# Train
export RESULTS_FILE=training_results.json
export DATASET_LOC="https://raw.githubusercontent.com/GokuMohandas/Made-With-ML/main/datasets/madewithml/dataset.csv"
export TRAIN_LOOP_CONFIG='{"dropout_p": 0.5, "lr": 1e-4, "lr_factor": 0.8, "lr_patience": 3}'
python madewithml/train.py \
    --experiment-name "$EXPERIMENT_NAME" \
    --dataset-loc "$DATASET_LOC" \
    --train-loop-config "$TRAIN_LOOP_CONFIG" \
    --num-workers 2 \
    --cpu-per-worker 10 \
    --gpu-per-worker 1 \
    --num-epochs 10 \
    --batch-size 256 \
    --results-fp $RESULTS_FILE

# Get and save run ID
export RUN_ID=$(jq -r '.run_id' $RESULTS_FILE)
export RUN_ID_FILE=/mnt/user_storage/run_id.txt
echo $RUN_ID > $RUN_ID_FILE  # used for serving later

# Evaluate
export RESULTS_FILE=evaluation_results.json
export HOLDOUT_LOC="https://raw.githubusercontent.com/GokuMohandas/Made-With-ML/main/datasets/madewithml/holdout.csv"
python madewithml/evaluate.py \
    --run-id $RUN_ID \
    --dataset-loc $HOLDOUT_LOC \
    --results-fp $RESULTS_FILE

# Test model
RESULTS_FILE=test_model_results.txt
pytest --run-id=$RUN_ID tests/model --verbose --disable-warnings > $RESULTS_FILE
cat $RESULTS_FILE