$ErrorActionPreference = "Stop"

python -m backend.dataset_builder
if ($LASTEXITCODE -ne 0) { throw "Dataset export failed." }

python finetune/train_lora.py `
  --base-model "Qwen/Qwen2.5-7B-Instruct" `
  --dataset-dir finetune/dataset `
  --output-dir finetune/output
if ($LASTEXITCODE -ne 0) { throw "LoRA training failed." }

ollama create "huyen-hoc-qwen2.5" -f finetune/Modelfile
if ($LASTEXITCODE -ne 0) { throw "Ollama model creation failed." }
