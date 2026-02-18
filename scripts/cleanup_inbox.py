import sys
import os
import json
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define base directory (project root)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(os.path.join(BASE_DIR, 'phantom-antenna/src/skills'))
from google_workspace import GoogleWorkspaceSkill

LABEL_NAME = "Phantom/To-Do"

def get_or_create_label(service, label_name):
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for label in labels:
            if label['name'] == label_name:
                return label['id']
        
        # Create label if not found
        label_body = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        created_label = service.users().labels().create(userId='me', body=label_body).execute()
        print(f"Created label: {label_name} (ID: {created_label['id']})")
        return created_label['id']
    except Exception as e:
        print(f"Error getting/creating label: {e}")
        return None

def main():
    skill = GoogleWorkspaceSkill()
    service = skill._service_gmail
    
    label_id = get_or_create_label(service, LABEL_NAME)
    if not label_id:
        print("Could not get or create label. Exiting.")
        return

    classification_file = os.path.join(BASE_DIR, 'memory/mail_classification_result.json')
    with open(classification_file, 'r') as f:
        results = json.load(f)

    for item in results:
        msg_id = item['id']
        category = item['category']
        
        if category in ['No-Action', 'Done']:
            # Archive: remove INBOX label
            try:
                service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'removeLabelIds': ['INBOX']}
                ).execute()
                print(f"Archived message {msg_id} ({category})")
            except Exception as e:
                print(f"Error archiving {msg_id}: {e}")
        
        elif category == 'To-Do':
            # Add label
            try:
                service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'addLabelIds': [label_id]}
                ).execute()
                print(f"Labeled message {msg_id} as {LABEL_NAME}")
            except Exception as e:
                print(f"Error labeling {msg_id}: {e}")

if __name__ == '__main__':
    main()
