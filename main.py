import base64
import logging
import re
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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


EMAIL_SUMMARY_BATCH_SIZE = 6

MESS_KEYWORDS = [
    "mess", "food", "meal", "canteen", "breakfast", "lunch", "dinner",
    "hygiene", "water", "taste", "quality", "kitchen",
]

HOSTEL_KEYWORDS = [
    "hostel", "room", "fan", "bed", "bathroom", "washroom", "cleaning",
    "warden", "mosquito", "electricity", "maintenance",
]

ACADEMICS_KEYWORDS = [
    "class", "exam", "fees", "faculty", "teacher", "lecture", "attendance",
    "marks", "result", "assignment", "timetable", "academic",
]

DEMO_SUMMARIES = {
    "mess_summarized": [
        "- Mess food was cold and rice was undercooked during lunch.",
        "- Students reported poor hygiene in the mess dining area.",
        "- Dinner was delayed and many students could not eat on time.",
        "- Drinking water near the mess was not clean.",
        "- Students requested better quality control in mess food.",
    ],
    "hostel_summarized": [
        "- Water supply was unavailable in the hostel block.",
        "- Bathroom cleaning was not done for several days.",
        "- Room fan was not functioning despite repeated complaints.",
        "- Hostel washrooms had blocked drainage.",
        "- Power backup was not available during electricity cuts.",
    ],
    "academics_summarized": [
        "- Assignment upload was not showing correctly on the portal.",
        "- Attendance was marked incorrectly for a class.",
        "- Exam result was missing from the academic portal.",
        "- Course material was not uploaded before the exam.",
        "- Students requested rescheduling of overlapping exams.",
    ],
}


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
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        if sentence.strip()
    ]

    if not sentences:
        return "- No clear summary generated."

    selected_sentences = []

    for sentence in sentences:
        lower_sentence = sentence.lower()
        if any(
            keyword in lower_sentence
            for keyword in MESS_KEYWORDS + HOSTEL_KEYWORDS + ACADEMICS_KEYWORDS
        ):
            selected_sentences.append(sentence)

        if len(selected_sentences) == 5:
            break

    if not selected_sentences:
        selected_sentences = sentences[:5]

    summary = "\n".join(f"- {sentence}" for sentence in selected_sentences)
    return normalize_summary_to_bullets(summary)


def classify_category(text: str) -> str:
    lower_text = text.lower()

    mess_score = sum(1 for keyword in MESS_KEYWORDS if keyword in lower_text)
    hostel_score = sum(1 for keyword in HOSTEL_KEYWORDS if keyword in lower_text)
    academics_score = sum(1 for keyword in ACADEMICS_KEYWORDS if keyword in lower_text)

    if mess_score >= hostel_score and mess_score >= academics_score:
        return "mess_summarized"

    if hostel_score >= mess_score and hostel_score >= academics_score:
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


@app.post("/load-demo-data")
def load_demo_data():
    try:
        stored_count = 0

        for category, summaries in DEMO_SUMMARIES.items():
            full_content = (
                "Demo complaint batch used when Gmail has no unread test emails."
            )

            for summary in summaries:
                status = db_manager.store_summary_in_db(
                    category,
                    summary,
                    full_content,
                )

                if status == "stored":
                    stored_count += 1

        return {
            "status": "success",
            "message": f"Demo data loaded. Added {stored_count} new summaries.",
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
