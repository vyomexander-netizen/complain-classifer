import pandas as pd
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq,
)


df = pd.read_csv("complains.csv")

tokenizer = AutoTokenizer.from_pretrained("facebook/bart-base")
model = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-base")

inputs = tokenizer(
    df["dialogue"].tolist(),
    padding=True,
    truncation=True,
    max_length=512,
    return_tensors="pt",
)

outputs = tokenizer(
    df["summary"].tolist(),
    padding=True,
    truncation=True,
    max_length=128,
    return_tensors="pt",
)

mapped_data = {
    "input_ids": inputs["input_ids"],
    "attention_mask": inputs["attention_mask"],
    "labels": outputs["input_ids"],
}

train_dataset = Dataset.from_dict(mapped_data)
data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

training_args = Seq2SeqTrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=4,
    num_train_epochs=3,
    learning_rate=2e-5,
    save_strategy="epoch",
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    data_collator=data_collator,
)

trainer.train()

trainer.save_model("./summarizer_model")
tokenizer.save_pretrained("./summarizer_model")

print("Model saved to ./summarizer_model")