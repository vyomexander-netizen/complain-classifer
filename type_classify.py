from transformers import pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def check(text):
    candidate_labels = ["hostel", "academic","mess","other"]
    result = classifier(text, candidate_labels)
    
    if result["labels"][0] == "hostel":
        return 3
    elif result["labels"][0] == "academic":
        return 2
    elif result["labels"][0] == "mess":
        return 1
    else: 
        return 0
i = 0
import db_manager

data = db_manager.convert_record_to_dictionary("complaints")

for record in data:
    text = record["content"]
    value = check(text)

    if value == 3:
        db_manager.store_in_db("hostel", text)
    elif value == 2:
        db_manager.store_in_db("academics", text)
    elif value == 1:
        db_manager.store_in_db("mess", text)
    else:
        i += 1

print("Other / unclassified complaints:", i)
