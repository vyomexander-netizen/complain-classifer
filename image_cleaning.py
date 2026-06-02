import re
from bs4 import BeautifulSoup


def clean_email_content(mail_content: str) -> str:
    soup = BeautifulSoup(mail_content, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text