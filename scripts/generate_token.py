import os
import json
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Unified SCOPES for Calendar, Tasks, Directory API, Gmail, and Drive
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/admin.directory.group.member',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/drive.file'
]

CREDENTIALS_FILE = 'credentials.json' # Make sure credentials.json is in the same directory or adjust path
TOKEN_FILE = 'token.json'

def generate_and_encode_token():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Do not open browser automatically, print URL for manual access
            creds = flow.run_local_server(port=8080, open_browser=False)

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")

    # Read the generated token.json and base64 encode it
    with open(TOKEN_FILE, 'r') as f:
        token_data = f.read()
    
    encoded_token = base64.b64encode(token_data.encode('utf-8')).decode('utf-8')
    print("Base64 encoded token.json:")
    print(encoded_token)

if __name__ == '__main__':
    generate_and_encode_token()
