"""Optional LoRA fine-tuning for a locally exported review-approved JSONL set."""

import argparse
import importlib
import inspect
import json
from pathlib import Path


def read_records(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            record = json.loads(line)
            messages = record.get("messages")
            if (
                not isinstance(messages, list)
                or len(messages) != 3
                or [message.get("role") for message in messages]
                != ["system", "user", "assistant"]
                or not all(isinstance(message.get("content"), str) for message in messages)
            ):
                raise ValueError(f"Invalid chat example at {path}:{line_number}")
            records.append(record)
    if not records:
        raise ValueError(f"Dataset is empty: {path}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--dataset-dir", type=Path, default=Path("finetune/dataset"))
    parser.add_argument("--output-dir", type=Path, default=Path("finetune/output"))
    parser.add_argument("--epochs", type=float, default=3)
    parser.add_argument("--max-length", type=int, default=2048)
    args = parser.parse_args()
    if args.epochs <= 0 or args.max_length < 128:
        parser.error("--epochs must be positive and --max-length at least 128.")

    train_rows = read_records(args.dataset_dir / "train.jsonl")
    validation_rows = read_records(args.dataset_dir / "validation.jsonl")
    try:
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
        peft = importlib.import_module("peft")
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Optional training packages are missing. Install finetune/requirements-training.txt "
            "in a dedicated training environment."
        ) from exc

    tokenizer = transformers.AutoTokenizer.from_pretrained(
        args.base_model, trust_remote_code=False
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = transformers.AutoModelForCausalLM.from_pretrained(
        args.base_model,
        trust_remote_code=False,
        torch_dtype="auto",
    )
    model.config.use_cache = False
    model = peft.get_peft_model(
        model,
        peft.LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            target_modules=["q_proj", "v_proj"],
            task_type="CAUSAL_LM",
        ),
    )

    class ChatDataset(torch.utils.data.Dataset):
        def __init__(self, records: list[dict]) -> None:
            self.features = [self._encode(record) for record in records]

        def _encode(self, record: dict) -> dict:
            messages = record["messages"]
            prompt = tokenizer.apply_chat_template(
                messages[:-1], tokenize=False, add_generation_prompt=True
            )
            conversation = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            input_ids = tokenizer(
                conversation,
                add_special_tokens=False,
                truncation=True,
                max_length=args.max_length,
            )["input_ids"]
            prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
            prefix_length = 0
            for actual, expected in zip(input_ids, prompt_ids):
                if actual != expected:
                    break
                prefix_length += 1
            if prefix_length == 0 or prefix_length >= len(input_ids):
                raise ValueError("The chat template did not produce a trainable assistant response.")
            labels = list(input_ids)
            labels[:prefix_length] = [-100] * prefix_length
            return {
                "input_ids": input_ids,
                "attention_mask": [1] * len(input_ids),
                "labels": labels,
            }

        def __len__(self) -> int:
            return len(self.features)

        def __getitem__(self, index: int) -> dict:
            return self.features[index]

    train_dataset = ChatDataset(train_rows)
    validation_dataset = ChatDataset(validation_rows)
    collator = transformers.DataCollatorForSeq2Seq(
        tokenizer=tokenizer, padding=True, label_pad_token_id=-100, return_tensors="pt"
    )
    use_cuda = torch.cuda.is_available()
    supports_bf16 = use_cuda and torch.cuda.is_bf16_supported()
    training_arguments = {
        "output_dir": str(args.output_dir / "checkpoints"),
        "num_train_epochs": args.epochs,
        "per_device_train_batch_size": 1,
        "per_device_eval_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "learning_rate": 2e-4,
        "logging_steps": 5,
        "save_strategy": "epoch",
        "report_to": "none",
        "fp16": use_cuda and not supports_bf16,
        "bf16": supports_bf16,
        "gradient_checkpointing": True,
    }
    arguments_parameters = inspect.signature(transformers.TrainingArguments).parameters
    evaluation_parameter = (
        "eval_strategy"
        if "eval_strategy" in arguments_parameters
        else "evaluation_strategy"
    )
    training_arguments[evaluation_parameter] = "epoch"
    trainer = transformers.Trainer(
        model=model,
        args=transformers.TrainingArguments(**training_arguments),
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        data_collator=collator,
    )
    trainer.train()
    adapter_dir = args.output_dir / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    print(f"LoRA adapter saved to {adapter_dir}")


if __name__ == "__main__":
    main()
