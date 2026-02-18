import os
import base64
import argparse
import logging
import re
import io
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# 設定
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive.file'
]
TOKEN_FILE = 'token.json'
SEARCH_QUERY = 'has:attachment filename:pdf after:2026/01/31 subject:(invoice OR 請求書) -from:{{COMPANY_DOMAIN}} -label:Invoices_Saved'
LABEL_NAME = 'Invoices_Saved'

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_credentials():
    if os.path.exists(TOKEN_FILE):
        return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return None

def sanitize_sender(sender_str):
    """送信者名をサニタイズする (e.g. "Name <email@example.com>" -> "email_at_example.com")"""
    match = re.search(r'<(.+?)>', sender_str)
    email = match.group(1) if match else sender_str
    return email.replace('@', '_at_').replace('.', '_')

def get_or_create_folder(drive_service, folder_name, parent_id=None):
    """フォルダを取得または作成する"""
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
    
    # 作成
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    logger.info(f"Created folder: {folder_name}")
    return folder.get('id')

def get_invoice_folder(drive_service):
    """Invoices/YYYY-MM フォルダのIDを取得する"""
    root_folder_id = get_or_create_folder(drive_service, "Invoices")
    month_str = datetime.now().strftime("%Y-%m")
    return get_or_create_folder(drive_service, month_str, parent_id=root_folder_id)

def file_exists(drive_service, folder_id, filename):
    """同名ファイルが存在するか確認"""
    query = f"name = '{filename}' and '{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    return len(results.get('files', [])) > 0

def get_or_create_label(gmail_service, label_name):
    """ラベルを取得または作成する"""
    results = gmail_service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']
    
    label_body = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    label = gmail_service.users().labels().create(userId='me', body=label_body).execute()
    logger.info(f"Created label: {label_name}")
    return label['id']

def main():
    parser = argparse.ArgumentParser(description='Save invoices from Gmail to Google Drive.')
    parser.add_argument('--dry-run', action='store_true', help='Do not save files or add labels.')
    args = parser.parse_args()

    creds = get_credentials()
    if not creds:
        logger.error("Credentials not found. Please run generate_token.py first.")
        return

    try:
        gmail_service = build('gmail', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # ラベルID取得
        label_id = get_or_create_label(gmail_service, LABEL_NAME)

        # メッセージ検索
        results = gmail_service.users().messages().list(userId='me', q=SEARCH_QUERY).execute()
        messages = results.get('messages', [])

        if not messages:
            logger.info("No invoices found.")
            return

        logger.info(f"Found {len(messages)} messages.")

        for msg in messages:
            message = gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = message['payload']['headers']
            
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
            
            # 日付パース (YYYYMMDD)
            if date_str:
                try:
                    # RFC 2822 format
                    dt = datetime.strptime(' '.join(date_str.split()[:4]), '%a, %d %b %Y')
                    formatted_date = dt.strftime('%Y%m%d')
                except:
                    formatted_date = datetime.now().strftime('%Y%m%d')
            else:
                formatted_date = datetime.now().strftime('%Y%m%d')

            sanitized_sender = sanitize_sender(sender)
            
            parts = message['payload'].get('parts', [])
            for part in parts:
                if part['filename'] and part['filename'].lower().endswith('.pdf'):
                    attachment_id = part['body'].get('attachmentId')
                    if not attachment_id:
                        continue
                    
                    original_name = part['filename']
                    # ファイル名生成: YYYYMMDD_{Sender}_{OriginalName}.pdf
                    new_filename = f"{formatted_date}_{sanitized_sender}_{original_name}"
                    
                    logger.info(f"Processing: {new_filename} (Subject: {subject})")
                    
                    if args.dry_run:
                        logger.info(f"[DRY-RUN] Would save {new_filename} to Drive and add label.")
                        continue

                    # フォルダ取得
                    folder_id = get_invoice_folder(drive_service)
                    
                    # 重複チェック
                    if file_exists(drive_service, folder_id, new_filename):
                        logger.warning(f"File already exists: {new_filename}. Skipping.")
                        continue

                    # 添付ファイル取得
                    attachment = gmail_service.users().messages().attachments().get(
                        userId='me', messageId=msg['id'], id=attachment_id).execute()
                    data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                    # Driveへ保存
                    file_metadata = {
                        'name': new_filename,
                        'parents': [folder_id]
                    }
                    media = MediaIoBaseUpload(io.BytesIO(data), mimetype='application/pdf')
                    
                    drive_file = drive_service.files().create(
                        body=file_metadata, media_body=media, fields='id').execute()
                    
                    logger.info(f"Saved to Drive: {new_filename} (ID: {drive_file.get('id')})")

                    # ラベル付与
                    gmail_service.users().messages().modify(
                        userId='me', id=msg['id'],
                        body={'addLabelIds': [label_id]}
                    ).execute()
                    logger.info(f"Added label {LABEL_NAME} to message {msg['id']}")

    except HttpError as error:
        logger.error(f"An error occurred: {error}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == '__main__':
    main()
