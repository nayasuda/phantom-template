import os
import json
import base64
import datetime
import argparse
import re
import html
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import google.generativeai as genai # 追加

# Define base directory (project root)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))

# Unified SCOPES for Calendar, Tasks, Directory API, and Gmail
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/admin.directory.group.member',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

class GoogleWorkspaceSkill:
    _instance = None
    _creds = None
    _service_calendar = None
    _service_tasks = None
    _service_directory = None
    _service_gmail = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GoogleWorkspaceSkill, cls).__new__(cls)
            cls._instance._authenticate()
        return cls._instance

    def _authenticate(self):
        creds = None
        
        # 1. Try to load from environment variable (Base64)
        env_token = os.environ.get('GOOGLE_TOKEN_BASE64')
        if env_token:
            try:
                token_data = json.loads(base64.b64decode(env_token).decode('utf-8'))
                # Load with default scopes from token data to avoid mismatch during refresh
                creds = Credentials.from_authorized_user_info(token_data)
            except Exception as e:
                print(f"Error loading token from env: {e}")

        # 2. Fallback to local file if not loaded from env
        if not creds and os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE)
            except Exception as e:
                print(f"Error loading token from file: {e}")
        
        # 3. Handle expired or missing credentials
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                # If refresh fails (e.g. invalid_scope), keep existing creds as is
                # and provide debug info. This prevents crashing in CI environments.
                print(f"Warning: Error refreshing token: {e}")
                if os.environ.get('GITHUB_ACTIONS'):
                    print(f"DEBUG: Current token scopes: {getattr(creds, 'scopes', 'Unknown')}")
                    print(f"DEBUG: Required scopes defined in code: {SCOPES}")
                    # Check for missing scopes
                    if hasattr(creds, 'scopes'):
                        missing = set(SCOPES) - set(creds.scopes)
                        if missing:
                            print(f"DEBUG: Missing scopes: {missing}")

        # 4. Final validation and fallback to interactive flow if possible
        if not creds or not creds.valid:
            if os.environ.get('GITHUB_ACTIONS'):
                if not creds:
                    print("Error: No credentials available in GitHub Actions environment.")
                else:
                    print("Warning: Credentials are not valid (expired or insufficient scopes), but proceeding anyway.")
            else:
                # Only attempt interactive flow if NOT in GitHub Actions
                try:
                    # Priority: env variable for credentials.json
                    env_creds = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
                    if env_creds:
                        creds_data = json.loads(base64.b64decode(env_creds).decode('utf-8'))
                        flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
                    else:
                        if not os.path.exists(CREDENTIALS_FILE):
                            print(f"Credentials file not found: {CREDENTIALS_FILE}")
                            # Don't raise, just let it be None
                        else:
                            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                            creds = flow.run_local_server(port=8080, open_browser=False)
                            
                            # Save token if successfully obtained
                            try:
                                with open(TOKEN_FILE, 'w') as token:
                                    token.write(creds.to_json())
                            except Exception as e:
                                print(f"Warning: Could not write token file: {e}")
                except Exception as e:
                    print(f"Error during interactive auth flow: {e}")

        self._creds = creds
        
        # Build services with individual error handling
        def build_service(name, version, **kwargs):
            try:
                if not self._creds:
                    return None
                return build(name, version, credentials=self._creds, **kwargs)
            except Exception as e:
                print(f"Warning: Failed to build Google Workspace service '{name}': {e}")
                return None

        self._service_calendar = build_service('calendar', 'v3')
        self._service_tasks = build_service('tasks', 'v1')
        self._service_directory = build_service('admin', 'directory_v1')
        self._service_gmail = build_service('gmail', 'v1')

    def list_upcoming_events(self, days: int = 7) -> str:
        try:
            if not self._service_calendar: return "Error: Calendar service not available."
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            end_time = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat() + 'Z'
            events_result = self._service_calendar.events().list(
                calendarId='primary', timeMin=now, timeMax=end_time,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            if not events: return "No upcoming events found."
            
            res = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                res.append(f"{start} - {event['summary']}")
            return "\n".join(res)
        except Exception as e: return f"Error: {e}"

    def create_calendar_event(self, summary, start_time, end_time, description=None, location=None, attendees=None):
        try:
            if not self._service_calendar: return "Error: Calendar service not available."
            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'Asia/Tokyo'},
                'end': {'dateTime': end_time, 'timeZone': 'Asia/Tokyo'},
            }
            if attendees:
                event['attendees'] = [{'email': email.strip()} for email in attendees]
            
            event = self._service_calendar.events().insert(calendarId='primary', body=event).execute()
            return f"Event created: {event.get('htmlLink')}"
        except Exception as e: return f"Error: {e}"

    def list_incomplete_tasks(self) -> str:
        try:
            if not self._service_tasks: return "Error: Tasks service not available."
            results = self._service_tasks.tasks().list(tasklist='@default', showCompleted=False).execute()
            tasks = results.get('items', [])
            if not tasks: return "No incomplete tasks found."
            return "\n".join([f"- {task['title']} (ID: {task['id']})" for task in tasks])
        except Exception as e: return f"Error: {e}"

    def create_task(self, title: str, notes: str = None, tasklist_id: str = '@default') -> str:
        try:
            if not self._service_tasks: return "Error: Tasks service not available."
            task = {'title': title}
            if notes:
                task['notes'] = notes
            result = self._service_tasks.tasks().insert(tasklist=tasklist_id, body=task).execute()
            return f"Task created: {result.get('title')} (ID: {result.get('id')})"
        except Exception as e:
            return f"Error creating task: {e}"

    def complete_task(self, tasklist_id: str, task_id: str) -> str:
        try:
            if not self._service_tasks: return "Error: Tasks service not available."
            body = {'status': 'completed'}
            result = self._service_tasks.tasks().patch(tasklist=tasklist_id, task=task_id, body=body).execute()
            return f"Task completed: {result.get('title')} (ID: {result.get('id')})"
        except Exception as e:
            return f"Error completing task: {e}"

    def add_group_member(self, group_email: str, member_email: str) -> str:
        try:
            if not self._service_directory: return "Error: Directory service not available."
            body = {'email': member_email, 'role': 'MEMBER'}
            result = self._service_directory.members().insert(groupKey=group_email, body=body).execute()
            return f"Successfully added {member_email} to group {group_email}."
        except Exception as e: return f"Error adding member: {e}"

    def get_freebusy(self, calendars: list, time_min: str, time_max: str) -> dict:
        """
        Query free/busy information for a set of calendars.
        time_min and time_max should be ISO 8601 strings (e.g. 2026-02-12T09:00:00Z)
        """
        try:
            if not self._service_calendar: return {"error": "Calendar service not available."}
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cal_id} for cal_id in calendars]
            }
            freebusy_result = self._service_calendar.freebusy().query(body=body).execute()
            return freebusy_result.get('calendars', {})
        except Exception as e:
            return {"error": str(e)}

    def list_recent_emails(self, max_results: int = 30) -> str:
        try:
            if not self._service_gmail: return "Error: Gmail service not available."
            results = self._service_gmail.users().messages().list(userId='me', maxResults=max_results).execute()
            messages = results.get('messages', [])
            if not messages: return "No recent emails found."

            email_list = []
            for message in messages:
                msg = self._service_gmail.users().messages().get(userId='me', id=message['id'], format='full').execute()
                headers = msg['payload']['headers']
                subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
                sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
                date = next((header['value'] for header in headers if header['name'] == 'Date'), 'Unknown Date')
                snippet = msg.get('snippet', 'No snippet available.')
                email_list.append(f"Subject: {subject}\nFrom: {sender}\nDate: {date}\nSnippet: {snippet}\n---")
            return "\n".join(email_list)
        except Exception as e:
            return f"Error listing recent emails: {e}"

    def list_emails(self, max_results: int = 30) -> str:
        try:
            if not self._service_gmail: return json.dumps({"error": "Gmail service not available."})
            results = self._service_gmail.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                m = self._service_gmail.users().messages().get(userId='me', id=msg['id']).execute()
                headers = m.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                emails.append({
                    'id': m['id'],
                    'threadId': m['threadId'],
                    'snippet': m.get('snippet', ''),
                    'subject': subject,
                    'from': sender,
                    'date': next((h['value'] for h in headers if h['name'] == 'Date'), '')
                })
            return json.dumps(emails, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_gmail_signature(self) -> str:
        """
        Get primary Gmail signature as plain text.
        """
        try:
            if not self._service_gmail:
                return ""

            results = self._service_gmail.users().settings().sendAs().list(userId='me').execute()
            send_as = results.get('sendAs', [])
            signature_html = ""
            for alias in send_as:
                if alias.get('isPrimary'):
                    signature_html = alias.get('signature', '')
                    break

            if not signature_html:
                return ""

            text = re.sub(r'<br\s*/?>', '\n', signature_html, flags=re.IGNORECASE)
            text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]*>', '', text)
            text = html.unescape(text)
            lines = [line.strip() for line in text.split('\n')]
            return "\n".join(line for line in lines if line)
        except Exception as e:
            return f"Error getting signature: {e}"

    def create_gmail_draft(self, to: str, subject: str, body: str, thread_id: str = None, cc: str = None) -> str:
        try:
            if not self._service_gmail: return "Error: Gmail service not available."
            message = MIMEText(body, 'plain', 'utf-8')
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['Cc'] = cc

            draft_body = {'message': {}}

            if thread_id:
                draft_body['message']['threadId'] = thread_id
                try:
                    thread = self._service_gmail.users().threads().get(userId='me', id=thread_id).execute()
                    messages = thread.get('messages', [])
                    if messages:
                        last_message = messages[-1]
                        headers = last_message.get('payload', {}).get('headers', [])
                        msg_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), None)
                        refs = next((h['value'] for h in headers if h['name'].lower() == 'references'), None)
                        if msg_id:
                            message['In-Reply-To'] = msg_id
                            message['References'] = f"{refs} {msg_id}".strip() if refs else msg_id
                    if not subject.lower().startswith('re:'):
                        message.replace_header('subject', f"Re: {subject}")
                except Exception as thread_error:
                    return f"Error creating threaded draft: {thread_error}"

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            draft_body['message']['raw'] = raw_message
            draft = self._service_gmail.users().drafts().create(userId='me', body=draft_body).execute()
            return f"Draft created: {draft['id']}"
        except Exception as e:
            return f"Error creating draft: {e}"

    def create_reply_draft(self, message_id, reply_text, signature=None) -> str:
        try:
            if not self._service_gmail: return "Error: Gmail service not available."
            
            # 1. Get original message
            original_msg = self._service_gmail.users().messages().get(userId='me', id=message_id).execute()
            headers = original_msg.get('payload', {}).get('headers', [])
            
            # 2. Extract info
            thread_id = original_msg.get('threadId')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            message_id_header = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), None)
            references_header = next((h['value'] for h in headers if h['name'].lower() == 'references'), '')
            reply_to = next((h['value'] for h in headers if h['name'].lower() == 'reply-to'), 
                           next((h['value'] for h in headers if h['name'].lower() == 'from'), None))

            # 3. Prepare reply headers
            if not subject.lower().startswith('re:'):
                subject = 'Re: ' + subject
                
            body = reply_text
            if signature:
                body += f"\n\n--\n{signature}"
                
            message = MIMEText(body)
            message['to'] = reply_to
            message['subject'] = subject
            if message_id_header:
                message['In-Reply-To'] = message_id_header
                message['References'] = (references_header + ' ' + message_id_header).strip()
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            draft_body = {
                'message': {
                    'raw': raw_message,
                    'threadId': thread_id
                }
            }
            draft = self._service_gmail.users().drafts().create(userId='me', body=draft_body).execute()
            return f"Reply draft created: {draft['id']} (Thread ID: {thread_id})"
        except Exception as e:
            return f"Error creating reply draft: {e}"

    def _get_email_body(self, message_id) -> str:
        try:
            message = self._service_gmail.users().messages().get(userId='me', id=message_id, format='full').execute()
            
            def get_text_from_parts(parts):
                body = ""
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode('utf-8')
                    elif part.get('mimeType') == 'multipart/alternative':
                        body += get_text_from_parts(part.get('parts', []))
                return body

            payload = message.get('payload', {})
            body = ""
            if 'parts' in payload:
                body = get_text_from_parts(payload['parts'])
            else:
                data = payload.get('body', {}).get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            return body
        except Exception as e:
            return ""

    def _extract_slack_invite_link(self, text) -> str:
        if not text: return None
        # Pattern 1: Direct link
        match = re.search(r'https://join\.slack\.com/t/[a-zA-Z0-9-]+/shared_invite/[a-zA-Z0-9-_?=&]+', text)
        if match: return match.group(0)
        # Pattern 2: Google redirected link
        match_google = re.search(r'https://www\.google\.com/url\?q=(https://join\.slack\.com/[^&]+)', text)
        if match_google: return match_google.group(1)
        return None

    def add_task_from_email(self, message_id, title=None, notes=None) -> str:
        try:
            if not self._service_gmail: return "Error: Gmail service not available."
            
            # Get email details first
            msg = self._service_gmail.users().messages().get(userId='me', id=message_id).execute()
            headers = msg.get('payload', {}).get('headers', [])
            
            if not title:
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Email Task')
                title = f"Email: {subject}"

            email_link = f"https://mail.google.com/mail/u/0/#inbox/{message_id}"
            
            # Attempt to extract Slack invitation link
            body = self._get_email_body(message_id)
            slack_link = self._extract_slack_invite_link(body)
            
            full_notes = ""
            if slack_link:
                full_notes += f"🔗 Slack招待リンク: {slack_link}\n\n"
            
            if notes:
                full_notes += f"{notes}\n\n"
            
            full_notes += f"Link: {email_link}"
            
            return self.create_task(title, full_notes)
        except Exception as e:
            return f"Error adding task from email: {e}"

    def ensure_phantom_labels(self) -> str:
        required_labels = [
            '0. Phantom/To-Do',
            '1. Joker-Action',
            '2. Phantom-Action',
            '3. 対応不要',
            '4. 対応完了'
        ]
        created = []
        already_exists = []
        try:
            if not self._service_gmail: return "Error: Gmail service not available."
            
            # List current labels
            results = self._service_gmail.users().labels().list(userId='me').execute()
            current_labels = {l['name']: l['id'] for l in results.get('labels', [])}
            
            for label_name in required_labels:
                if label_name in current_labels:
                    already_exists.append(label_name)
                else:
                    label_body = {
                        'name': label_name,
                        'labelListVisibility': 'labelShow',
                        'messageListVisibility': 'show'
                    }
                    self._service_gmail.users().labels().create(userId='me', body=label_body).execute()
                    created.append(label_name)
            
            res = ""
            if created:
                res += f"Created: {', '.join(created)}. "
            if already_exists:
                res += f"Already exists: {', '.join(already_exists)}."
            return res or "No labels to process."
        except Exception as e:
            return f"Error ensuring labels: {e}"

    def modify_email_labels(self, message_id: str, add_labels: list = None, remove_labels: list = None) -> str:
        try:
            if not self._service_gmail: return json.dumps({"error": "Gmail service not available."})
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels
            
            result = self._service_gmail.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def archive_email(self, message_id: str) -> str:
        return self.modify_email_labels(message_id, remove_labels=['INBOX'])

    def list_labels(self) -> str:
        try:
            if not self._service_gmail: return json.dumps({"error": "Gmail service not available."})
            results = self._service_gmail.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            return json.dumps(labels, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_label_id_by_name(self, label_name: str) -> str:
        """
        Get label ID by its name. Returns None if not found.
        """
        try:
            results = self._service_gmail.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            return None
        except Exception as e:
            print(f"Error getting label ID: {e}")
            return None

    def mark_email_as_done(self, message_id: str) -> str:
        """
        Marks an email as done by:
        - Removing '0. Phantom/To-Do' label
        - Adding '4. 対応完了' label
        - Removing 'INBOX' label (archiving)
        """
        try:
            # Get label IDs
            todo_label_id = self.get_label_id_by_name("0. Phantom/To-Do")
            done_label_id = self.get_label_id_by_name("4. 対応完了")
            
            add_labels = []
            if done_label_id:
                add_labels.append(done_label_id)
            else:
                return json.dumps({"error": "Required label '4. 対応完了' not found. Please create it first."})
                
            remove_labels = ["INBOX"]
            if todo_label_id:
                remove_labels.append(todo_label_id)
            
            return self.modify_email_labels(message_id, add_labels=add_labels, remove_labels=remove_labels)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def classify_email(self, subject: str, snippet: str, sender: str = "Unknown") -> str:
        """
        Classifies an email using LLM into one of: Joker-Action, Phantom-Action, No-Action.
        Returns a JSON string with category, reason, and optionally reply_draft.
        """
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return json.dumps({"error": "GEMINI_API_KEY not set", "category": "No-Action", "reason": "API key missing"})

        genai.configure(api_key=api_key)
        
        # Determine model
        model_name = 'gemini-3-flash-preview'
        try:
            model = genai.GenerativeModel(model_name)
        except Exception:
            # Fallback to stable version
            model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""\
あなたは有能なビジネスアシスタント「Phantom」です。\
以下のメールの内容を解析し、適切なカテゴリに分類してください。\
\n【重要ルール】\
- Slackへの招待（"Slack でやり取りするために招待されました", "invited you to join a Slack workspace" 等）は、必ず **Joker-Action** に分類してください。\
- 単なる通知メール（手動対応不要のもの）は **No-Action** に分類してください：\
  * 「〇〇 is waiting for your response」「〇〇があなたの返信を待っています」→ No-Action（リマインダー通知）\
  * 「Alert:」「Notification:」「[アラート]」で始まるログイン通知・監視アラート → No-Action（情報提供のみ）\
  * Jira期限通知、GitHub App追加通知、カレンダーリマインダー → No-Action\
  * 完了報告、処理完了通知 → No-Action\
- システムエラー通知でコード修正が必要なものは **Phantom-Action** です。\
- 人間からの質問・相談・依頼メールは **Joker-Action** です。\
\n【カテゴリ定義】\
1. **Joker-Action**: {{USER_FULLNAME}}（ジョーカー）本人が確認、返信、判断、実行する必要があるもの。\
   - 例: 人間からの相談メール、契約確認依頼、Slack招待、重要な意思決定が必要なもの\
2. **Phantom-Action**: ユーザーの手を煩わせない完全自動処理、またはアシスタントが代行・処理できるタスク。\
   - 例: アカウント削除代行、単純なツール操作、データ集計依頼\
3. **No-Action**: 通知、お知らせ、完了報告、広告、メルマガなど、特に対応が不要なもの。\
   - 例: リマインダー通知、ログインアラート、期限通知、自動レポート、完了通知\
\n【判定の優先順位】\
1. まず「通知・アラート・リマインダー」かを判断 → Yes なら No-Action\
2. 次に「人間からの質問・依頼・Slack招待」かを判断 → Yes なら Joker-Action\
3. 最後に「自動処理可能なタスク」かを判断 → Yes なら Phantom-Action\
\n【出力ルール】\
- 判定理由（reason）は簡潔に、なぜそのカテゴリを選んだか説明してください。\
- 人間による返信が必要な内容（Joker-Actionに該当）の場合、日本のビジネスメール形式で適切な返信案（reply_draft）を作成してください。\
- 返信案は丁寧かつ簡潔にし、署名は含めないでください。\
\n【出力形式】\
必ず以下のJSON形式のみを出力してください。\
\n{{\
  "category": "Joker-Action" | "Phantom-Action" | "No-Action",\
  "reason": "判定理由",\
  "reply_draft": "返信案（返信が必要な場合のみ、それ以外は空文字列）"\
}}\
\n---\
\n件名: {subject}\
\n差出人: {sender}\
\n内容: {snippet}\
"""
        try:
            response = model.generate_content(prompt)
            content = response.text.strip()
            # Remove markdown code blocks
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            # Validate JSON
            data = json.loads(content)
            if data.get("category") not in ["Joker-Action", "Phantom-Action", "No-Action"]:
                data["category"] = "No-Action"
            
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "category": "No-Action",
                "reason": f"LLM Error: {str(e)}",
                "reply_draft": ""
            }, ensure_ascii=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Google Workspace CLI Tool')
    parser.add_argument('--action', choices=['events', 'create_event', 'tasks', 'create_task', 'complete_task', 'add_member', 'freebusy', 'list_emails', 'list_recent_emails', 'create_draft', 'create_reply_draft', 'add_task_from_email', 'ensure_labels', 'modify_labels', 'archive', 'get_label_id', 'mark_done', 'list_labels', 'classify', 'get_signature'], required=True)
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--max_results', type=int, default=30)
    parser.add_argument('--summary', help='Event summary')
    parser.add_argument('--start', help='Event start time (ISO 8601)')
    parser.add_argument('--end', help='Event end time (ISO 8601)')
    parser.add_argument('--description', help='Event description')
    parser.add_argument('--location', help='Event location')
    parser.add_argument('--attendees', help='Comma separated list of attendee emails')
    parser.add_argument('--group', help='Group email for add_member')
    parser.add_argument('--member', help='Member email to add')
    parser.add_argument('--to', help='Recipient email for Gmail actions')
    parser.add_argument('--subject', help='Email subject for Gmail actions')
    parser.add_argument('--body', help='Email body for Gmail actions')
    parser.add_argument('--message_id', help='Gmail message ID')
    parser.add_argument('--reply_text', help='Reply text for create_reply_draft')
    parser.add_argument('--signature', help='Signature for create_reply_draft')
    parser.add_argument('--thread_id', help='Gmail thread ID for create_draft')
    parser.add_argument('--cc', help='Cc recipients for create_draft')
    parser.add_argument('--add', help='Comma separated list of labels to add')
    parser.add_argument('--remove', help='Comma separated list of labels to remove')
    parser.add_argument('--label_name', help='Label name to find ID for')
    parser.add_argument('--title', help='Task title')
    parser.add_argument('--notes', help='Task notes')
    parser.add_argument('--task_id', help='Task ID')
    parser.add_argument('--tasklist_id', help='Tasklist ID', default='@default')
    parser.add_argument('--snippet', help='Email snippet for classify')
    parser.add_argument('--sender', help='Email sender for classify')
    args = parser.parse_args()

    skill = GoogleWorkspaceSkill()
    if args.action == 'events': print(skill.list_upcoming_events(days=args.days))
    elif args.action == 'create_event':
        if not args.summary or not args.start or not args.end:
            print("Error: --summary, --start, and --end are required for create_event.")
        else:
            attendees_list = args.attendees.split(',') if args.attendees else None
            print(skill.create_calendar_event(
                args.summary, 
                args.start, 
                args.end, 
                args.description, 
                args.location, 
                attendees_list
            ))
    elif args.action == 'tasks': print(skill.list_incomplete_tasks())
    elif args.action == 'create_task':
        if not args.title:
            print("Error: --title is required for create_task.")
        else:
            print(skill.create_task(args.title, args.notes))
    elif args.action == 'complete_task':
        if not args.task_id:
            print("Error: --task_id is required for complete_task.")
        else:
            print(skill.complete_task(args.tasklist_id, args.task_id))
    elif args.action == 'add_member':
        if not args.group or not args.member:
            print("Error: --group and --member arguments are required for add_member action.")
        else:
            print(skill.add_group_member(args.group, args.member))
    elif args.action == 'freebusy':
        if not args.start or not args.end or not args.attendees:
            print("Error: --start, --end, and --attendees (comma separated) are required for freebusy.")
        else:
            calendars = args.attendees.split(',')
            import json
            print(json.dumps(skill.get_freebusy(calendars, args.start, args.end), indent=2, ensure_ascii=False))
    elif args.action == 'list_recent_emails':
        print(skill.list_recent_emails())
    elif args.action == 'list_emails':
        print(skill.list_emails(max_results=args.max_results))
    elif args.action == 'create_draft':
        if not args.to or not args.subject or not args.body:
            print("Error: --to, --subject, and --body are required for create_draft.")
        else:
            print(skill.create_gmail_draft(args.to, args.subject, args.body, args.thread_id, args.cc))
    elif args.action == 'create_reply_draft':
        if not args.message_id or not args.reply_text:
            print("Error: --message_id and --reply_text are required for create_reply_draft.")
        else:
            print(skill.create_reply_draft(args.message_id, args.reply_text, args.signature))
    elif args.action == 'add_task_from_email':
        if not args.message_id:
            print("Error: --message_id is required for add_task_from_email.")
        else:
            print(skill.add_task_from_email(args.message_id, args.title, args.notes))
    elif args.action == 'ensure_labels':
        print(skill.ensure_phantom_labels())
    elif args.action == 'modify_labels':
        if not args.message_id:
            print("Error: --message_id is required for modify_labels.")
        else:
            add_labels = args.add.split(',') if args.add else None
            remove_labels = args.remove.split(',') if args.remove else None
            print(skill.modify_email_labels(args.message_id, add_labels, remove_labels))
    elif args.action == 'archive':
        if not args.message_id:
            print("Error: --message_id is required for archive.")
        else:
            print(skill.archive_email(args.message_id))
    elif args.action == 'get_label_id':
        if not args.label_name:
            print("Error: --label_name is required for get_label_id.")
        else:
            print(skill.get_label_id_by_name(args.label_name))
    elif args.action == 'mark_done':
        if not args.message_id:
            print("Error: --message_id is required for mark_done.")
        else:
            print(skill.mark_email_as_done(args.message_id))
    elif args.action == 'list_labels':
        print(skill.list_labels())
    elif args.action == 'classify':
        if not args.subject or not args.snippet:
            print("Error: --subject and --snippet are required for classify.")
        else:
            print(skill.classify_email(args.subject, args.snippet, args.sender or "Unknown"))
    elif args.action == 'get_signature':
        print(skill.get_gmail_signature())
