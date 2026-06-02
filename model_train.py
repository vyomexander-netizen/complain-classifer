# train_summarizer.py
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


MODEL_PATH = "./summarizer_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)