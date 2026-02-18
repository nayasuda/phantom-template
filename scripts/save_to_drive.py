import os
import argparse
import logging
import mimetypes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# 設定
SCOPES = [
    'https://www.googleapis.com/auth/drive.file'
]
TOKEN_FILE = 'token.json'

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_credentials():
    """token.jsonから認証情報を取得する"""
    if os.path.exists(TOKEN_FILE):
        return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return None

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

def upload_file(drive_service, file_path, folder_id, mime_type=None):
    """ファイルをGoogle Driveにアップロードする"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None

    file_name = os.path.basename(file_path)
    
    if not mime_type:
        if file_path.lower().endswith('.drawio'):
            mime_type = 'application/vnd.jgraph.mxfile'
        else:
            mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    
    try:
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        logger.info(f"File uploaded successfully: {file_name}")
        return file
    except HttpError as error:
        logger.error(f"An error occurred during upload: {error}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Upload a local file to Google Drive.')
    parser.add_argument('file_path', help='Path to the local file to upload')
    parser.add_argument('--folder', default='Phantom Uploads', help='Target folder name in Google Drive (default: "Phantom Uploads")')
    parser.add_argument('--mime-type', help='MIME type of the file (optional, auto-detected if not provided)')
    
    args = parser.parse_args()

    creds = get_credentials()
    if not creds:
        logger.error("Credentials not found. Please run generate_token.py first.")
        return

    try:
        drive_service = build('drive', 'v3', credentials=creds)

        # フォルダの取得または作成
        folder_id = get_or_create_folder(drive_service, args.folder)
        
        # アップロード
        result = upload_file(drive_service, args.file_path, folder_id, args.mime_type)
        
        if result:
            print("\nUpload Complete!")
            print(f"File ID: {result.get('id')}")
            print(f"View Link: {result.get('webViewLink')}")

    except HttpError as error:
        logger.error(f"An error occurred: {error}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == '__main__':
    main()
