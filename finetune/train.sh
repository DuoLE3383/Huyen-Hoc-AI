#!/usr/bin/env sh
set -eu

python -m backend.dataset_builder
python finetune/train_lora.py \
  --base-model "${BASE_MODEL:-Qwen/Qwen2.5-7B-Instruct}" \
  --dataset-dir finetune/dataset \
  --output-dir finetune/output
ollama create "${OLLAMA_FINETUNED_MODEL:-huyen-hoc-qwen2.5}" -f finetune/Modelfile
