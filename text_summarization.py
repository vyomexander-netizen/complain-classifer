import model_train
import db_manager

tokenizer = model_train.tokenizer
model = model_train.model
def summarize_text(text: str) -> str:
    inputs = tokenizer(
        text,
        return_tensors="pt",
        max_length=512,
        truncation=True,
    )

    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=128,
        min_length=20,
        num_beams=4,
        early_stopping=True,
    )

    return tokenizer.decode(
        summary_ids[0],
        skip_special_tokens=True,
    )
def summarize_records(records, batch_size=8):
    summaries = []
    temp = []

    for record in records:
        temp.append(record["content"])

        if len(temp) == batch_size:
            combined_text = " ".join(temp)
            summaries.append(summarize_text(combined_text))
            temp.clear()

    if temp:
        combined_text = " ".join(temp)
        summaries.append(summarize_text(combined_text))

    return summaries
data_academics = db_manager.convert_record_to_dictionary("academics")
data_hostel = db_manager.convert_record_to_dictionary("hostel")
data_mess = db_manager.convert_record_to_dictionary("mess")
academics_summarized = summarize_records(data_academics)
hostel_summarized = summarize_records(data_hostel)
mess_summarized = summarize_records(data_mess)
for summary in academics_summarized:
    db_manager.store_in_db("academics_summarized", summary)

for summary in hostel_summarized:
    db_manager.store_in_db("hostel_summarized", summary)

for summary in mess_summarized:
    db_manager.store_in_db("mess_summarized", summary)

print("Summaries saved successfully.")