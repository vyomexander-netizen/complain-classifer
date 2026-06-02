import base64
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

import image_cleaning
import db_manager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GmailProcessRequest(BaseModel):
    access_token: str


summarizer_tokenizer = None
summarizer_model = None
category_classifier = None

EMAIL_SUMMARY_BATCH_SIZE = 6


def normalize_summary_to_bullets(summary: str) -> str:
    summary = summary.strip()

    if not summary:
        return "- No clear summary generated."

    if summary.startswith("-"):
        return summary

    sentences = [
        sentence.strip()
        for sentence in summary.replace("\n", " ").split(".")
        if sentence.strip()
    ]

    if not sentences:
        return f"- {summary}"

    return "\n".join(f"- {sentence}." for sentence in sentences)


def summarize_text(text: str) -> str:
    global summarizer_tokenizer, summarizer_model

    if summarizer_tokenizer is None or summarizer_model is None:
        summarizer_tokenizer = AutoTokenizer.from_pretrained("./results/summarizer_model")
        summarizer_model = AutoModelForSeq2SeqLM.from_pretrained("./results/summarizer_model")

    prompt = (
        "Summarize these emails as short bullet points only. "
        "Do not write a paragraph.\n\n"
        f"{text}"
    )

    inputs = summarizer_tokenizer(
        prompt,
        return_tensors="pt",
        max_length=512,
        truncation=True,
    )

    summary_ids = summarizer_model.generate(
        **inputs,
        max_length=120,
        min_length=10,
        num_beams=4,
        early_stopping=True,
    )

    summary = summarizer_tokenizer.decode(
        summary_ids[0],
        skip_special_tokens=True,
    )

    return normalize_summary_to_bullets(summary)


def classify_category(text: str) -> str:
    global category_classifier

    if category_classifier is None:
        category_classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )

    result = category_classifier(
        text,
        candidate_labels=["mess", "hostel", "academics"],
    )

    label = result["labels"][0]

    if label == "mess":
        return "mess_summarized"

    if label == "hostel":
        return "hostel_summarized"

    return "academics_summarized"


def decode_gmail_body(data: str) -> str:
    data += "=" * (-len(data) % 4)
    decoded_bytes = base64.urlsafe_b64decode(data)
    return decoded_bytes.decode("utf-8", errors="replace")


def extract_email_body(payload: dict) -> Optional[str]:
    html_parts = []
    plain_parts = []

    def walk_parts(part: dict):
        mime_type = part.get("mimeType")
        body = part.get("body", {})
        body_data = body.get("data")

        if body_data:
            if mime_type == "text/html":
                html_parts.append(body_data)
            elif mime_type == "text/plain":
                plain_parts.append(body_data)

        for child_part in part.get("parts", []):
            walk_parts(child_part)

    walk_parts(payload)

    if html_parts:
        return "\n".join(decode_gmail_body(part) for part in html_parts)

    if plain_parts:
        return "\n".join(decode_gmail_body(part) for part in plain_parts)

    return None


def mark_email_as_read(service, message_id: str):
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


def chunk_items(items: list, batch_size: int):
    for index in range(0, len(items), batch_size):
        yield items[index:index + batch_size]


def combine_emails_for_summary(emails: list) -> str:
    return "\n\n".join(
        f"Email {index + 1}: {email['content']}"
        for index, email in enumerate(emails)
    )


def background_process_emails(access_token: str):
    try:
        creds = Credentials(token=access_token)
        service = build("gmail", "v1", credentials=creds)

        query = "is:unread"
        results = service.users().messages().list(
            userId="me",
            q=query,
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            logger.info("No unread emails found.")
            return

        logger.info("Found %s unread emails.", len(messages))

        processed_emails = []

        for message in messages:
            message_id = message.get("id")

            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=message_id,
                    format="full",
                ).execute()

                payload = msg.get("payload", {})
                decoded_content = extract_email_body(payload)

                if not decoded_content:
                    logger.warning("No readable body found for email %s.", message_id)
                    continue

                cleaned_mail = image_cleaning.clean_email_content(decoded_content)
                db_manager.store_in_db("archive", cleaned_mail)

                processed_emails.append({
                    "message_id": message_id,
                    "content": cleaned_mail,
                })

                logger.info("Prepared email %s for batch summarization.", message_id)

            except Exception as e:
                logger.exception("Error processing email %s: %s", message_id, e)
                continue

        for batch in chunk_items(processed_emails, EMAIL_SUMMARY_BATCH_SIZE):
            try:
                combined_mail = combine_emails_for_summary(batch)

                summary = summarize_text(combined_mail)
                category = classify_category(combined_mail)

                db_manager.store_summary_in_db(category, summary, combined_mail)

                for email in batch:
                    mark_email_as_read(service, email["message_id"])

                logger.info(
                    "Summarized %s emails together into %s.",
                    len(batch),
                    category,
                )

            except Exception as e:
                message_ids = [email["message_id"] for email in batch]
                logger.exception(
                    "Error summarizing email batch %s: %s",
                    message_ids,
                    e,
                )
                continue

    except Exception as e:
        logger.exception("Background Gmail processing failed: %s", e)


@app.post("/process-gmail")
def process_gmail(request: GmailProcessRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            background_process_emails,
            request.access_token,
        )

        return {
            "status": "success",
            "message": "Gmail processing started.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/email-summaries")
def get_email_summaries(category: str):
    try:
        summaries = db_manager.convert_record_to_dictionary(category)

        return {
            "status": "success",
            "category": category,
            "summaries": summaries,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
