#!/bin/bash

MODEL_PATH='T:/Programming/Python/Machine Learning/PyTorch/Multimodel (Vision) Language Model/paligemma3b/'
PROMPT="this tower is "
IMAGE_FILE_PATH='T:/Programming/Python/Machine Learning/PyTorch/Multimodel (Vision) Language Model/images/eiffel_tower.jpeg'
MAX_TOKENS_TO_GENERATE=100
TEMPERATURE=0.8
TOP_P=0.9
DO_SAMPLE="False"
ONLY_CPU="False"

python inference.py \
    --model_path "$MODEL_PATH" \
    --prompt "$PROMPT" \
    --image_file_path "$IMAGE_FILE_PATH" \
    --max_tokens_to_generate $MAX_TOKENS_TO_GENERATE \
    --temperature $TEMPERATURE \
    --top_p $TOP_P \
    --do_sample $DO_SAMPLE \
    --only_cpu $ONLY_CPU
