print("hello")
import sys
print(sys.executable)
import sys
!C:\Users\Satwik\anaconda3\envs\campus_env\python.exe -m pip install transformers torch
from transformers import pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def check(text):
    candidate_labels = ["complain", "non-complain"]
    result = classifier(text, candidate_labels)
    
    if result["labels"][0] == "complain":
        return 1
    else:
        return 0
import db_manager

data = db_manager.convert_record_to_dictionary("archive")

for record in data:
    text = record["content"]
    value = check(text)

    if value == 1:
        db_manager.store_in_db("complaints", text)
        