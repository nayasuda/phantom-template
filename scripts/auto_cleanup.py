import sys
import os
import json
import base64
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google.generativeai as genai

# Define base directory (project root)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

# Load .gemini/.env so GEMINI_API_KEY and other keys are available
_env_path = os.path.join(BASE_DIR, '.gemini', '.env')
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
sys.path.append(os.path.join(BASE_DIR, 'phantom-antenna/src/skills'))
from google_workspace import GoogleWorkspaceSkill

# Results file path (from HEAD)
CLASSIFICATION_RESULT_FILE = os.path.join(BASE_DIR, 'memory/mail_classification_result.json')

JAPANESE_BUSINESS_SIGNATURE = """--------------------------------------------------
{{COMPANY_NAME}}株式会社
{{USER_FULLNAME}}
email: {{USER_EMAIL}}
--------------------------------------------------"""

def save_classification_result(msg_id, category, reason):
    """Save classification result to a JSON file for analysis (from HEAD)"""
    results = []
    if os.path.exists(CLASSIFICATION_RESULT_FILE):
        try:
            with open(CLASSIFICATION_RESULT_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
                if not isinstance(results, list):
                    results = []
        except Exception:
            results = []
    
    # Update or append
    found = False
    for item in results:
        if item.get('id') == msg_id:
            item['category'] = category
            item['reason'] = reason
            item['timestamp'] = datetime.datetime.now().isoformat()
            found = True
            break
    
    if not found:
        results.append({
            "id": msg_id,
            "category": category,
            "reason": reason,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CLASSIFICATION_RESULT_FILE), exist_ok=True)
        with open(CLASSIFICATION_RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving results: {e}")

def main():
    skill = GoogleWorkspaceSkill()
    gmail_service = skill._service_gmail

    if not gmail_service:
        print("Error: Gmail service not available. Exiting.")
        return

    # Ensure Phantom labels exist
    print("Ensuring Phantom labels...")
    skill.ensure_phantom_labels()

    # Get label IDs for later use
    label_todo_id = skill.get_label_id_by_name("0. Phantom/To-Do")
    label_no_action_id = skill.get_label_id_by_name("3. 対応不要")
    label_done_id = skill.get_label_id_by_name("4. 対応完了") 

    if not all([label_todo_id, label_no_action_id, label_done_id]):
        print("Error: Required Phantom labels not found.")
        return

    print("Fetching unread emails from INBOX...")
    try:
        results = gmail_service.users().messages().list(userId='me', q='label:INBOX is:unread').execute()
        messages = results.get('messages', [])
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return

    if not messages:
        print("No unread emails in INBOX to process.")
        return

    processed_count = 0
    for message in messages:
        msg_id = message['id']
        try:
            full_msg = gmail_service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            headers = full_msg.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            snippet = full_msg.get('snippet', '')
            
            print(f"\n--- Processing: {subject} (ID: {msg_id}) ---")
            print(f"From: {sender}")

            # Use GoogleWorkspaceSkill.classify_email (from main)
            classification_result_json = skill.classify_email(subject, snippet, sender)
            classification_result = json.loads(classification_result_json)
            category = classification_result.get("category", "No-Action")
            reason = classification_result.get("reason", "")
            reply_draft = classification_result.get("reply_draft", "")
            
            print(f"Classified as: {category}")
            print(f"Reason: {reason}")

            # Save result (from HEAD)
            save_classification_result(msg_id, category, reason)

            if category == "Joker-Action":
                # Create task for Joker
                print(f"Creating task for Joker...")
                print(skill.add_task_from_email(msg_id, title=f"ジョーカー要対応: {subject}"))
                
                # Move to To-Do and keep UNREAD (so the user sees it)
                skill.modify_email_labels(msg_id, add_labels=[label_todo_id], remove_labels=['INBOX'])
                print(f"Processed Joker-Action. Moved to 'To-Do', removed from INBOX, kept UNREAD.")

            elif category == "Phantom-Action":
                print(f"Processing Phantom-Action (Background)...")
                # Prefix changed to "Phantom代行中"
                print(skill.add_task_from_email(msg_id, title=f"Phantom代行中: {subject}"))
                
                # Move to To-Do and mark as read (background processing)
                skill.modify_email_labels(msg_id, add_labels=[label_todo_id], remove_labels=['INBOX', 'UNREAD'])
                print(f"Processed Phantom-Action. Moved to 'To-Do', removed from INBOX, marked as read.")
            
            elif category == "No-Action":
                print(f"Archiving and marking as read...")
                # Mark as read and label as No-Action
                skill.modify_email_labels(msg_id, add_labels=[label_no_action_id], remove_labels=['INBOX', 'UNREAD'])
                print(f"Archived and labeled as '対応不要'.")
            
            processed_count += 1

        except Exception as e:
            print(f"Error processing message {msg_id}: {e}")

    print(f"\nFinished processing. Total emails processed: {processed_count}")

if __name__ == "__main__":
    main()
