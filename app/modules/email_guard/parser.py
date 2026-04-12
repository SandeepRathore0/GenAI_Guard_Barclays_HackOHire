import email
from email import policy
from email.message import EmailMessage
import re
from typing import Dict, Any, List

def parse_eml_content(eml_bytes: bytes) -> Dict[str, Any]:
    """
    Parses a raw .eml byte payload into structured components.
    Extracts: Headers, Body Text, URLs, and Attachments.
    """
    msg = email.message_from_bytes(eml_bytes, policy=policy.default)
    
    # 1. Extract Headers
    headers = {
        "subject": msg.get("Subject", "No Subject"),
        "from": msg.get("From", "Unknown Sender"),
        "to": msg.get("To", "Unknown Recipient"),
        "date": msg.get("Date", "Unknown Date")
    }

    # 2. Extract Body Text
    body_text = ""
    html_text = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            # Get the content type, we are looking for text/plain or text/html
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # Skip attachments here
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text += str(payload.decode(errors='ignore'))
                except Exception:
                    pass
            elif content_type == "text/html":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_text += str(payload.decode(errors='ignore'))
                except Exception:
                    pass
    else:
        # Not multipart, just read the payload
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = str(payload.decode(errors='ignore'))
        except Exception:
            pass
            
    # Prefer plain text, fallback to HTML if plain is empty (though HTML would need cleaning ideally)
    final_body = body_text if body_text.strip() else html_text

    # 3. Extract URLs (from the final body text we extracted)
    urls = extract_urls(final_body)

    # 4. Extract Attachments
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition or part.get_filename():
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        "filename": filename,
                        "content_type": part.get_content_type(),
                        "payload": part.get_payload(decode=True) # The raw bytes for file/audio guard
                    })

    return {
        "headers": headers,
        "body": final_body,
        "urls": urls,
        "attachments": attachments
    }

def extract_urls(text: str) -> List[str]:
    """
    Extracts all URLs from a given text string using regex.
    """
    url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*')
    urls = url_pattern.findall(text)
    # Remove duplicates
    return list(set(urls))
