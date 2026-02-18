import os
import json
import subprocess
import re
import logging
import sys
import argparse
import base64
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Add path for GoogleWorkspaceSkill
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(os.path.join(BASE_DIR, 'phantom-antenna/src/skills'))
try:
    from google_workspace import GoogleWorkspaceSkill
except ImportError:
    # Fallback if path is not correct or file missing
    GoogleWorkspaceSkill = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/tasks']

class GoogleTasksSync:
    # Project v2 Constants
    PROJECT_ID = 'PVT_kwHOCB_Y0s4BOscH'
    STATUS_FIELD_ID = 'PVTSSF_lAHOCB_Y0s4BOscHzg9Uf8Y'
    TODO_OPTION_ID = '62f277af'
    IN_PROGRESS_OPTION_ID = '8e5985ba'
    DONE_OPTION_ID = '67fb16e8'
    DONE_STATUSES = {'Done'}

    def __init__(self, owner="{{GITHUB_USERNAME}}", repo="{{REPO_NAME}}", create_issues=False):
        # Validate environment variables
        if not os.environ.get("GITHUB_TOKEN") and not os.environ.get("GH_TOKEN"):
            # Warning only, as we might just want to update a task without GitHub sync
            logger.warning("GITHUB_TOKEN or GH_TOKEN environment variable is missing. GitHub operations will fail.")
        
        self.owner = owner
        self.repo = repo
        self.create_issues = create_issues
        self.creds = self.load_credentials()
        self.service = build('tasks', 'v1', credentials=self.creds)
        mode = "issues+project" if self.create_issues else "project-draft-only"
        logger.info(f"Sync mode: {mode}")
        
        # Initialize GoogleWorkspaceSkill for Gmail processing
        try:
            if GoogleWorkspaceSkill:
                self.workspace_skill = GoogleWorkspaceSkill()
                logger.info("Initialized GoogleWorkspaceSkill for Gmail processing")
            else:
                self.workspace_skill = None
        except Exception as e:
            logger.warning(f"Failed to initialize GoogleWorkspaceSkill: {e}")
            self.workspace_skill = None

    def _build_task_metadata(self, task):
        task_id = task['id']
        tasklist_id = task.get('tasklist_id', '@default')
        notes = task.get('notes', '')
        gmail_link = None
        if notes:
            gmail_match = re.search(r'https://mail\.google\.com/mail/[^?#\s]+', notes)
            if gmail_match:
                gmail_link = gmail_match.group(0)
        link = f"https://www.googleapis.com/tasks/v1/lists/{tasklist_id}/tasks/{task_id}"
        return task_id, tasklist_id, notes, gmail_link, link

    def _build_task_body(self, task):
        task_id, tasklist_id, notes, gmail_link, link = self._build_task_metadata(task)
        body_lines = [
            "## 📋 Task Details",
            "",
            "### Links",
        ]
        if gmail_link:
            body_lines.append(f"- [✉️ View Email in Gmail]({gmail_link})")
        body_lines.extend([
            f"- [🔗 View Task in Google Tasks]({link})",
            "",
            "---",
            f"Origin: Google Tasks {task_id}",
            f"Tasklist-ID: {tasklist_id}",
            f"System-Link: {link} (Do not click / System use only)",
            f"Note: {notes}"
        ])
        return "\n".join(body_lines)

    def _extract_task_id_from_text(self, text):
        if not text:
            return None
        match_task = re.search(r'Origin: Google Tasks ([^\n\s]+)', text)
        if match_task:
            return match_task.group(1)
        return None

    def _extract_task_context_from_text(self, text):
        if not text:
            return None, None, None
        task_id = None
        tasklist_id = None
        gmail_id = None

        match_task = re.search(r'Origin: Google Tasks ([^\n\s]+)', text)
        if match_task:
            task_id = match_task.group(1)

        match_tasklist = re.search(r'Tasklist-ID: ([^\n\s]+)', text)
        if match_tasklist:
            tasklist_id = match_tasklist.group(1)

        match_gmail = re.search(r'Gmail-ID: ([a-zA-Z0-9]+)', text)
        if match_gmail:
            gmail_id = match_gmail.group(1)

        if not tasklist_id:
            match_link = re.search(r'(?:System-)?Link: https://www\.googleapis\.com/tasks/v1/lists/([^/]+)/tasks/([^/\n\s]+)', text)
            if match_link:
                tasklist_id = match_link.group(1)

        return task_id, tasklist_id, gmail_id

    def _extract_task_ids_from_project_items(self, project_items):
        task_ids = set()
        for item in project_items:
            candidates = []
            if isinstance(item.get('title'), str):
                candidates.append(item.get('title'))
            if isinstance(item.get('body'), str):
                candidates.append(item.get('body'))
            content = item.get('content', {})
            if isinstance(content, dict):
                if isinstance(content.get('title'), str):
                    candidates.append(content.get('title'))
                if isinstance(content.get('body'), str):
                    candidates.append(content.get('body'))
            for text in candidates:
                task_id = self._extract_task_id_from_text(text)
                if task_id:
                    task_ids.add(task_id)
        return task_ids

    def _collect_text_candidates_from_project_item(self, item):
        candidates = []
        for key in ('title', 'body'):
            value = item.get(key)
            if isinstance(value, str):
                candidates.append(value)

        content = item.get('content', {})
        if isinstance(content, dict):
            for key in ('title', 'body'):
                value = content.get(key)
                if isinstance(value, str):
                    candidates.append(value)

        return [text for text in candidates if text]

    def load_credentials(self):
        """
        Load credentials from environment variables (CI/CD) or local files (dev).
        Priority: GOOGLE_TOKEN_BASE64 > token.json > interactive flow
        """
        creds = None
        
        # 1. Try to load from environment variable (Base64 encoded)
        env_token = os.environ.get('GOOGLE_TOKEN_BASE64')
        if env_token:
            try:
                token_data = json.loads(base64.b64decode(env_token).decode('utf-8'))
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                logger.info("Loaded credentials from GOOGLE_TOKEN_BASE64")
            except Exception as e:
                logger.error(f"Error loading token from env: {e}", exc_info=True)
        
        # 2. Fallback to local file if not loaded from env
        if not creds and os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                logger.info("Loaded credentials from token.json")
            except Exception as e:
                logger.error(f"Error loading token from file: {e}", exc_info=True)
        
        # 3. Handle expired or missing credentials
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed expired credentials")
            except Exception as e:
                logger.warning(f"Error refreshing token: {e}")
                if os.environ.get('GITHUB_ACTIONS'):
                    logger.error("Token refresh failed in GitHub Actions environment")
        
        # 4. Final validation and fallback to interactive flow if possible
        if not creds or not creds.valid:
            if os.environ.get('GITHUB_ACTIONS'):
                if not creds:
                    raise ValueError("No credentials available in GitHub Actions environment. Set GOOGLE_TOKEN_BASE64.")
                else:
                    logger.warning("Credentials are not valid, but proceeding in GitHub Actions")
            else:
                # Only attempt interactive flow if NOT in GitHub Actions
                logger.info("Attempting interactive authentication flow")
                
                # Try to load credentials.json from env or file
                env_creds = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
                if env_creds:
                    creds_data = json.loads(base64.b64decode(env_creds).decode('utf-8'))
                    flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
                else:
                    if not os.path.exists('credentials.json'):
                        raise FileNotFoundError("credentials.json not found and GOOGLE_CREDENTIALS_BASE64 not set")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                
                creds = flow.run_local_server(port=0)
                
                # Save to local file for future use
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                logger.info("Saved new credentials to token.json")
        
        return creds

    def get_task_lists(self):
        results = self.service.tasklists().list().execute()
        return results.get('items', [])

    def get_tasks(self, tasklist_id):
        results = self.service.tasks().list(tasklist=tasklist_id, showCompleted=True, showHidden=True).execute()
        return results.get('items', [])

    def get_open_issues(self):
        command = [
            'gh', 'issue', 'list',
            '--repo', f"{self.owner}/{self.repo}",
            '--state', 'open',
            '--json', 'number,title,body,labels'
        ]
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error fetching open issues: {e.stderr}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching open issues: {e}", exc_info=True)
            return []

    def get_closed_issues(self):
        command = [
            'gh', 'issue', 'list',
            '--repo', f"{self.owner}/{self.repo}",
            '--state', 'closed',
            '--json', 'number,title,body,labels'
        ]
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error fetching closed issues: {e.stderr}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching closed issues: {e}", exc_info=True)
            return []

    def get_all_issues(self):
        """
        Fetch both open and closed issues for robust deduplication and reconciliation.
        """
        command = [
            'gh', 'issue', 'list',
            '--repo', f"{self.owner}/{self.repo}",
            '--state', 'all',
            '--json', 'number,title,body,labels,state,id',
            '--limit', '1000'
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error fetching all issues: {e.stderr}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching all issues: {e}", exc_info=True)
            return []

    def get_all_project_items(self):
        """Get all Project v2 items"""
        command = [
            'gh', 'project', 'item-list', '{{PROJECT_NUMBER}}',
            '--owner', self.owner,
            '--format', 'json',
            '--limit', '1000'
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )
            data = json.loads(result.stdout)
            return data.get('items', [])
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error fetching project items: {e.stderr}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching project items: {e}", exc_info=True)
            return []

    def create_issue(self, task):
        title = f"🐺 Phantom要対応: {task['title']}"
        task_id = task['id']
        body = self._build_task_body(task)

        command = [
            'gh', 'issue', 'create',
            '--repo', f"{self.owner}/{self.repo}",
            '--title', title,
            '--body', body,
            '--label', 'Status: 🕵️ Infiltration'
        ]
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=True
            )
            issue_url = result.stdout.strip()
            issue_number = issue_url.split('/')[-1]
            logger.info(f"Created issue: {issue_url}")
            
            # Add to Project
            self.add_issue_to_project(issue_number)
            
            return issue_number
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout creating issue for task {task_id}", exc_info=True)
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating issue: {e.stderr}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating issue: {e}", exc_info=True)
            return None

    def create_project_draft_item(self, task):
        title = f"📝 Phantom Task: {task['title']}"
        task_id = task['id']
        body = self._build_task_body(task)
        command = [
            'gh', 'project', 'item-create', '1',
            '--owner', self.owner,
            '--title', title,
            '--body', body,
            '--format', 'json'
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            item_id = None
            try:
                created = json.loads(result.stdout)
                item_id = created.get('id')
            except Exception:
                item_id = None

            # Keep board visuals consistent: draft items should also start at Todo (green).
            if item_id:
                subprocess.run([
                    'gh', 'project', 'item-edit',
                    '--id', item_id,
                    '--field-id', self.STATUS_FIELD_ID,
                    '--single-select-option-id', self.TODO_OPTION_ID,
                    '--project-id', self.PROJECT_ID
                ], capture_output=True, text=True, timeout=30, check=True)

            logger.info(f"Created project draft item for task: {task_id}")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout creating project draft item for task {task_id}", exc_info=True)
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating project draft item: {e.stderr}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating project draft item: {e}", exc_info=True)
            return False

    def add_issue_to_project(self, issue_number):
        """Add issue to Project v2 and set status to Todo"""
        try:
            # First, add to project to get item ID
            add_command = [
                'gh', 'project', 'item-add', '1',
                '--owner', self.owner,
                '--url', f"https://github.com/{self.owner}/{self.repo}/issues/{issue_number}",
                '--format', 'json'
            ]
            add_result = subprocess.run(
                add_command,
                capture_output=True, 
                text=True, 
                timeout=30,
                check=True
            )
            add_data = json.loads(add_result.stdout)
            item_id = add_data.get('id')

            if item_id:
                logger.info(f"Setting Status to 'Todo' for Project Item ID: {item_id}")
                
                edit_command = [
                    'gh', 'project', 'item-edit', 
                    '--id', item_id,
                    '--field-id', self.STATUS_FIELD_ID,
                    '--single-select-option-id', self.TODO_OPTION_ID,
                    '--project-id', self.PROJECT_ID
                ]
                subprocess.run(
                    edit_command,
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    check=True
                )
                logger.info(f"Successfully set Status to 'Todo' for issue #{issue_number}")
                return True
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout adding issue #{issue_number} to project", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to add issue #{issue_number} to project: {e}", exc_info=True)
        return False

    def close_task(self, tasklist_id, task_id):
        try:
            self.service.tasks().patch(
                tasklist=tasklist_id,
                task=task_id,
                body={'status': 'completed'}
            ).execute()
            logger.info(f"Closed Google Task: {task_id} in list {tasklist_id}")
            return True
        except Exception as e:
            logger.error(f"Error closing Google Task {task_id}: {e}", exc_info=True)
            return False

    def update_task_status(self, task_id, status, tasklist_id='@default'):
        """Update a specific task's status"""
        try:
            # First get the task to ensure it exists and get current state
            task = self.service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
            
            if task['status'] == status:
                logger.info(f"Task {task_id} is already {status}")
                return True
                
            task['status'] = status
            self.service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
            logger.info(f"Task ID {task_id} updated to status: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False

    def reconcile_issue_project_consistency(self):
        """
        Ensure consistency between GitHub Issues and Project v2 items.
        1. Add missing Open issues to Project
        2. Set Close issues to Done in Project
        3. Set Open issues with empty status to Todo
        """
        logger.info("Step 4: Reconciling GitHub Issues ↔ Project v2 consistency...")
        
        all_issues = self.get_all_issues()
        if not all_issues:
            logger.warning("No issues found to reconcile.")
            return

        project_items = self.get_all_project_items()
        
        # Map issue number to project item
        issue_to_item = {}
        for item in project_items:
            content = item.get('content', {})
            if content.get('type') == 'Issue':
                number = content.get('number')
                if number:
                    issue_to_item[int(number)] = item

        added_to_project = 0
        set_done = 0
        set_todo = 0
        
        for issue in all_issues:
            issue_number = issue['number']
            issue_state = issue['state'] # OPEN or CLOSED
            
            # 1. Open issue not in project -> Add
            if issue_state == 'OPEN' and issue_number not in issue_to_item:
                logger.info(f"Issue #{issue_number} is OPEN but not in Project. Adding...")
                if self.add_issue_to_project(issue_number):
                    added_to_project += 1
                continue
            
            # If item exists in project
            if issue_number in issue_to_item:
                item = issue_to_item[issue_number]
                item_id = item['id']
                current_status_id = None
                
                # Get current status option ID
                for fv in item.get('fieldValues', {}).get('nodes', []):
                    if fv.get('field', {}).get('id') == self.STATUS_FIELD_ID:
                        current_status_id = fv.get('singleSelectOptionId')
                        break
                
                # 2. Close issue and not Done -> Set Done
                if issue_state == 'CLOSED' and current_status_id != self.DONE_OPTION_ID:
                    logger.info(f"Issue #{issue_number} is CLOSED but Project Status is not Done. Updating...")
                    try:
                        subprocess.run([
                            'gh', 'project', 'item-edit', 
                            '--id', item_id,
                            '--field-id', self.STATUS_FIELD_ID,
                            '--single-select-option-id', self.DONE_OPTION_ID,
                            '--project-id', self.PROJECT_ID
                        ], check=True, capture_output=True)
                        set_done += 1
                        logger.info(f"Updated Issue #{issue_number} status to Done")
                    except Exception as e:
                        logger.error(f"Failed to update Issue #{issue_number} to Done: {e}")

                # 3. Open issue and status empty -> Set Todo
                if issue_state == 'OPEN' and not current_status_id:
                    logger.info(f"Issue #{issue_number} is OPEN but has no Project Status. Setting to Todo...")
                    try:
                        subprocess.run([
                            'gh', 'project', 'item-edit', 
                            '--id', item_id,
                            '--field-id', self.STATUS_FIELD_ID,
                            '--single-select-option-id', self.TODO_OPTION_ID,
                            '--project-id', self.PROJECT_ID
                        ], check=True, capture_output=True)
                        set_todo += 1
                        logger.info(f"Updated Issue #{issue_number} status to Todo")
                    except Exception as e:
                        logger.error(f"Failed to update Issue #{issue_number} to Todo: {e}")

        # 4. Draft items with No Status -> Set Todo
        set_draft_todo = 0
        for item in project_items:
            content = item.get('content', {})
            item_type = content.get('type') if isinstance(content, dict) else None
            if item_type == 'DraftIssue':
                status = item.get('status', '')
                if not status:
                    item_id = item.get('id')
                    if not item_id:
                        continue
                    logger.info(f"Draft item '{content.get('title', 'unknown')}' has No Status. Setting to Todo...")
                    try:
                        subprocess.run([
                            'gh', 'project', 'item-edit',
                            '--id', item_id,
                            '--field-id', self.STATUS_FIELD_ID,
                            '--single-select-option-id', self.TODO_OPTION_ID,
                            '--project-id', self.PROJECT_ID
                        ], check=True, capture_output=True, text=True, timeout=30)
                        set_draft_todo += 1
                        logger.info(f"Updated Draft item '{content.get('title', 'unknown')}' status to Todo")
                    except Exception as e:
                        logger.error(f"Failed to update Draft item to Todo: {e}")

        logger.info(f"Reconcile result: added_to_project={added_to_project}, set_done={set_done}, set_todo={set_todo}, set_draft_todo={set_draft_todo}")

    def sync(self):
        logger.info("Starting Google Tasks ↔ GitHub sync...")
        task_lists = self.get_task_lists()
        all_issues = self.get_all_issues()
        project_items = self.get_all_project_items()
        
        # 1. Google Tasks -> Project Draft or GitHub Issues
        created_issue_count = 0
        created_draft_count = 0
        logger.info("Step 1: Syncing open Google Tasks to Project...")
        existing_task_ids = set()
        for issue in all_issues:
            issue_body = issue.get('body') or ''
            task_id = self._extract_task_id_from_text(issue_body)
            if task_id:
                existing_task_ids.add(task_id)
        existing_task_ids.update(self._extract_task_ids_from_project_items(project_items))

        for tl in task_lists:
            tasks = self.get_tasks(tl['id'])
            for task in tasks:
                if task['status'] == 'needsAction':
                    task_id = task['id']
                    if task_id not in existing_task_ids:
                        task['tasklist_id'] = tl['id']
                        if self.create_issues:
                            result = self.create_issue(task)
                            if result:
                                created_issue_count += 1
                                existing_task_ids.add(task_id)
                        else:
                            result = self.create_project_draft_item(task)
                            if result:
                                created_draft_count += 1
                                existing_task_ids.add(task_id)

        logger.info(f"Created {created_issue_count} new GitHub issues")
        logger.info(f"Created {created_draft_count} new Project draft items")

        # 2. GitHub Issues (Closed) -> Google Tasks (Complete)
        logger.info("Step 2: Completing Google Tasks from closed GitHub Issues...")
        
        # We need to process closed issues. 
        # get_closed_issues was removed from sync() logic in original code? 
        # Ah, original code had process_closed_issues() calling get_closed_issues() internally.
        # But wait, create_issue uses get_all_issues now? No, I defined get_all_issues separately.
        
        processed_tasks_from_issues = set()
        closed_issues = [i for i in all_issues if i['state'] == 'CLOSED']
        logger.info(f"Found {len(closed_issues)} closed issues to check")
        
        for issue in closed_issues:
             task_id = self._complete_google_task_from_issue(issue['number'], issue['body'])
             if task_id:
                 processed_tasks_from_issues.add(task_id)
                 
        logger.info(f"Processed {len(processed_tasks_from_issues)} tasks from closed issues")

        # 3. Project v2 (Done) -> Google Tasks (Complete)
        logger.info("Step 3: Completing Google Tasks from Project v2 'Done' items...")
        self.process_project_done_items(processed_tasks_from_issues)
        
        # 4. Reconcile Consistency
        self.reconcile_issue_project_consistency()

        # 5. Archive Done items older than 7 days
        self.archive_completed_items(archive_after_days=7)
        
        logger.info("Sync completed successfully")

    def _complete_google_task_from_text(self, source_ref, source_text):
        """
        Complete a Google Task and associated Gmail based on text payload.
        Returns task_id if processed, None otherwise.
        """
        if not source_text:
            return None
            
        if "Origin: Google Tasks" not in source_text:
            return None

        task_id, tasklist_id, gmail_id = self._extract_task_context_from_text(source_text)
        
        # Process Google Task
        if task_id and tasklist_id:
            try:
                task = self.service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
                if task['status'] == 'needsAction':
                    self.close_task(tasklist_id, task_id)
                    logger.info(f"Completed Google Task {task_id} from {source_ref}")
                else:
                    logger.debug(f"Task {task_id} already completed, skipping")
            except Exception as e:
                logger.error(f"Error checking/closing task {task_id}: {e}", exc_info=True)
        
        # Process associated Gmail if present
        if gmail_id and self.workspace_skill:
            try:
                logger.info(f"Processing associated Gmail {gmail_id} for {source_ref}")
                result_json = self.workspace_skill.mark_email_as_done(gmail_id)
                result = json.loads(result_json)
                
                if "error" in result:
                    logger.warning(f"Failed to mark Gmail as done: {result['error']}")
                else:
                    logger.info(f"Successfully marked Gmail {gmail_id} as done (removed from INBOX)")
            except Exception as e:
                logger.error(f"Error processing Gmail {gmail_id}: {e}", exc_info=True)
        elif gmail_id and not self.workspace_skill:
            logger.warning(f"Gmail-ID {gmail_id} found but GoogleWorkspaceSkill not available")
        
        return task_id

    def _complete_google_task_from_issue(self, issue_number, issue_body):
        """Compatibility wrapper for issue-based completion."""
        return self._complete_google_task_from_text(f"Issue #{issue_number}", issue_body)
    
    def process_project_done_items(self, already_processed_tasks):
        """
        Process Project v2 items with Status='Done' and complete corresponding Google Tasks.
        Supports both Issue-backed items and draft items.
        """
        logger.info("Processing Project v2 'Done' items...")
        project_items = self.get_all_project_items()

        if not project_items:
            logger.info("No 'Done' items found in Project v2")
            return
        
        processed_count = 0
        done_items = [i for i in project_items if i.get('status', '') in self.DONE_STATUSES]

        for item in done_items:
            item_id = item.get('id', 'unknown-item')
            content = item.get('content', {})
            item_type = content.get('type') if isinstance(content, dict) else None

            # Issue-backed item: fetch fresh issue body
            if item_type == 'Issue':
                issue_number = content.get('number')
                if not issue_number:
                    continue
                command = [
                    'gh', 'issue', 'view', str(issue_number),
                    '--repo', f"{self.owner}/{self.repo}",
                    '--json', 'number,body,state'
                ]
                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True
                    )
                    issue_data = json.loads(result.stdout)
                    task_id = self._complete_google_task_from_issue(
                        issue_data['number'],
                        issue_data.get('body', '')
                    )
                    if task_id and task_id not in already_processed_tasks:
                        processed_count += 1
                        logger.info(f"Completed Google Task {task_id} from Project Done Issue #{issue_number} (state={issue_data.get('state')})")
                except subprocess.TimeoutExpired:
                    logger.error(f"Timeout fetching issue #{issue_number}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error fetching issue #{issue_number}: {e.stderr}")
                except Exception as e:
                    logger.error(f"Unexpected error processing issue #{issue_number}: {e}", exc_info=True)
                continue

            # Draft or other item types: parse text directly from item payload
            for text in self._collect_text_candidates_from_project_item(item):
                task_id = self._complete_google_task_from_text(f"Project Item {item_id}", text)
                if task_id:
                    if task_id in already_processed_tasks:
                        break
                    processed_count += 1
                    already_processed_tasks.add(task_id)
                    logger.info(f"Completed Google Task {task_id} from Project Done item {item_id}")
                    break
        
        logger.info(f"Processed {processed_count} additional tasks from Project v2 'Done' items")
    
    def archive_completed_items(self, archive_after_days=7):
        """
        Archive Project v2 items that have been in 'Done' status for longer than archive_after_days.
        Uses GraphQL to fetch updatedAt timestamps for accurate age calculation.
        """
        logger.info(f"Step 5: Archiving items Done for {archive_after_days}+ days...")

        query = """
        query($projectId: ID!, $cursor: String) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: 100, after: $cursor) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id
                  updatedAt
                  isArchived
                  fieldValues(first: 10) {
                    nodes {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        name
                        field { ... on ProjectV2SingleSelectField { name } }
                      }
                    }
                  }
                  content {
                    ... on DraftIssue { title }
                    ... on Issue { title number }
                  }
                }
              }
            }
          }
        }
        """

        cutoff = datetime.now(timezone.utc) - timedelta(days=archive_after_days)
        archived_count = 0
        cursor = None

        while True:
            try:
                cmd = [
                    'gh', 'api', 'graphql',
                    '-f', f'query={query}',
                    '-F', f'projectId={self.PROJECT_ID}',
                ]
                if cursor:
                    cmd.extend(['-f', f'cursor={cursor}'])
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60, check=True
                )
                data = json.loads(result.stdout)
            except subprocess.CalledProcessError as e:
                logger.error(f"GraphQL query failed: {e.stderr}")
                break
            except Exception as e:
                logger.error(f"Unexpected error querying project items for archive: {e}", exc_info=True)
                break

            project_node = data.get('data', {}).get('node', {})
            items_data = project_node.get('items', {})
            nodes = items_data.get('nodes', [])

            for node in nodes:
                if node.get('isArchived'):
                    continue

                status_name = None
                for fv in node.get('fieldValues', {}).get('nodes', []):
                    if fv.get('field', {}).get('name') == 'Status':
                        status_name = fv.get('name')
                        break

                if status_name not in self.DONE_STATUSES:
                    continue

                updated_at_str = node.get('updatedAt')
                if not updated_at_str:
                    continue

                try:
                    updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse updatedAt '{updated_at_str}' for item {node['id']}")
                    continue

                if updated_at >= cutoff:
                    continue

                item_id = node['id']
                content = node.get('content', {})
                title = content.get('title', 'unknown')
                days_done = (datetime.now(timezone.utc) - updated_at).days

                logger.info(f"Archiving item '{title}' (Done for {days_done} days, id={item_id})")
                try:
                    subprocess.run([
                        'gh', 'project', 'item-archive', '1',
                        '--owner', self.owner,
                        '--id', item_id
                    ], check=True, capture_output=True, text=True, timeout=30)
                    archived_count += 1
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to archive item {item_id}: {e.stderr}")
                except Exception as e:
                    logger.error(f"Unexpected error archiving item {item_id}: {e}", exc_info=True)

            page_info = items_data.get('pageInfo', {})
            if page_info.get('hasNextPage'):
                cursor = page_info.get('endCursor')
            else:
                break

        logger.info(f"Archived {archived_count} items that were Done for {archive_after_days}+ days")

    def get_project_done_items(self):
        """Get all Project v2 items with Status = 'Done'"""
        command = [
            'gh', 'project', 'item-list', '{{PROJECT_NUMBER}}',
            '--owner', self.owner,
            '--format', 'json',
            '--limit', '500'
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,  # Longer timeout for large projects
                check=True
            )
            data = json.loads(result.stdout)
            items = data.get('items', [])
            total_count = data.get('totalCount', 0)
            
            logger.info(f"Retrieved {len(items)} items from Project v2 (total: {total_count})")
            
            # Filter items with Status = 'Done' or similar completion statuses
            done_items = []
            for item in items:
                # Check status field
                status = item.get('status', '')
                
                # Match various completion statuses
                # Note: Status values are case-sensitive from gh CLI
                if status in self.DONE_STATUSES:
                    # Extract issue number directly from content
                    content = item.get('content', {})
                    if content.get('type') == 'Issue':
                        issue_number = content.get('number')
                        if issue_number:
                            done_items.append(int(issue_number))
                        else:
                            logger.warning(f"Issue in Done status has no number field: {item.get('id')}")
            
            logger.info(f"Found {len(done_items)} items with completion status in Project v2")
            return done_items
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error fetching project items: {e.stderr}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching project items: {e}", exc_info=True)
            return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sync Google Tasks with GitHub Project v2 (and optionally Issues)')
    parser.add_argument('--owner', default='{{GITHUB_USERNAME}}', help='GitHub repository owner')
    parser.add_argument('--repo', default='{{REPO_NAME}}', help='GitHub repository name')
    parser.add_argument('--task_id', type=str, help='The ID of the task to update (optional)')
    parser.add_argument('--status', type=str, choices=['needsAction', 'completed'], help='The new status of the task (optional)')
    parser.add_argument(
        '--create-issues',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Create GitHub Issues from tasks (default: disabled, create Project draft items only)'
    )
    args = parser.parse_args()
    
    try:
        sync_engine = GoogleTasksSync(owner=args.owner, repo=args.repo, create_issues=args.create_issues)
        
        if args.task_id and args.status:
            # Single task update mode
            sync_engine.update_task_status(args.task_id, args.status)
        else:
            # Full sync mode
            sync_engine.sync()
            logger.info("Sync completed successfully")
            
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        sys.exit(1)
