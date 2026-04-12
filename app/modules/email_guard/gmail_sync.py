import os
import base64
import time
import asyncio
from typing import List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .parser import parse_eml_content
from .router import EmailSandbox
from app.core.activity_logger import ActivityLogger

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token_path = os.path.join(os.path.dirname(__file__), 'token.json')
    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print(f"ERROR: Cannot find {creds_path}. Please download your OAuth client ID JSON from GCP and place it here.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

async def poll_and_scan_emails():
    """
    Indefinitely polls the inbox for unread messages, analyzes them, and quarantines threats.
    """
    service = get_gmail_service()
    if not service:
        return

    start_time = int(time.time())
    print("Gmail Sync Service Started. Polling for unread emails arriving after now...")
    sandbox = EmailSandbox()

    while True:
        try:
            # Look for unread emails in the inbox that arrived after we started
            query = f'is:unread in:inbox after:{start_time}'
            results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
            messages = results.get('messages', [])

            for msg in messages:
                msg_id = msg['id']
                print(f"\nScanning new email ID: {msg_id}")
                
                # Fetch raw email content
                message_data = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
                raw_email_str = message_data['raw']
                eml_bytes = base64.urlsafe_b64decode(raw_email_str)

                # Parse and analyze
                parsed_email = parse_eml_content(eml_bytes)
                subject = parsed_email['headers'].get('subject', 'No Subject')
                sender = parsed_email['headers'].get('from', 'Unknown')
                print(f"Subject: {subject} | From: {sender}")

                analysis_result = await sandbox.analyze_email_components(parsed_email)
                status = analysis_result['status']
                score = analysis_result['final_score']
                alerts = analysis_result['alerts']
                threat_report = analysis_result.get('threat_report', {}) # Assuming threat_report might be part of analysis_result

                print(f"Verdict: {status} (Score: {score})")
                
                # Generate a real-time log for the Live Dashboard Stream (ISOLATED)
                ActivityLogger.log_gmail_activity(
                    module="Gmail Streamer",
                    input_type=f"Incoming Email: {subject}",
                    risk_score=score,
                    alerts=alerts,
                    threat_report=threat_report
                )

                # Quarantine if malicious
                if status in ["HIGH_RISK", "CRITICAL_RISK"]:
                    print(f"⚠️ THREAT DETECTED. Quarantining email to SPAM.")
                    # Move to SPAM and mark as read
                    service.users().messages().modify(
                        userId='me', id=msg_id, 
                        body={'addLabelIds': ['SPAM'], 'removeLabelIds': ['INBOX', 'UNREAD']}
                    ).execute()
                else:
                    print(" Email is safe. Removing UNREAD label so we don't scan it again.")
                    # Keep in inbox, just mark as read so we don't scan it again
                    service.users().messages().modify(
                        userId='me', id=msg_id, 
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()

        except HttpError as error:
            print(f'An API error occurred: {error}')
        except Exception as e:
            print(f'An unexpected error occurred: {e}')
            
        # Poll every 10 seconds
        time.sleep(10)

if __name__ == '__main__':
    # Add parent directory to path to allow absolute imports
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    
    asyncio.run(poll_and_scan_emails())
