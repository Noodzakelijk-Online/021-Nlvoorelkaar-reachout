import csv
import io
import logging
import os
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TOKEN_PATH = os.environ.get("NLVE_GOOGLE_TOKEN_PATH", os.path.join(DATA_DIR, "google_token.json"))
CLIENT_SECRET_PATH = os.environ.get("NLVE_GOOGLE_CLIENT_SECRET_PATH", os.path.join(DATA_DIR, "google_credentials.json"))


class GoogleDriveManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GoogleDriveManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.creds = None
        self.service = None
        self.file_id = None
        self.folder_id = None
        self.setup()

    def setup(self):
        os.makedirs(DATA_DIR, exist_ok=True)

        if os.path.exists(TOKEN_PATH):
            self.creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                logger.info("Refreshing Google Drive token")
                self.creds.refresh(Request())
            except Exception as e:
                logger.warning("Failed to refresh Google Drive token: %s", e)
                self.creds = None

        if not self.creds or not self.creds.valid:
            try:
                self.creds = self.get_new_credentials()
            except FileNotFoundError as e:
                logger.warning("%s", e)
                return

        if self.creds:
            with open(TOKEN_PATH, "w") as token:
                token.write(self.creds.to_json())
            try:
                os.chmod(TOKEN_PATH, 0o600)
            except OSError:
                logger.debug("Could not set private permissions on %s", TOKEN_PATH)

        try:
            service = build("drive", "v3", cache_discovery=False, credentials=self.creds)
            self.service = service

            folder_name = "nlvoorelkaar_data"

            self.folder_id = self.get_folder_id_by_name(folder_name)

            if not self.folder_id:
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')

                self.folder_id = folder_id

            files = ["contacts_date.csv", "reminder_data.csv", "chats_no_response.csv", "blacklisted_volunteers.csv"]
            for file in files:
                try:
                    existing_file = self.find_file_by_name(file)
                    if not existing_file:
                        file_metadata = {"name": file, "parents": [self.folder_id]}
                        self.service.files().create(body=file_metadata, fields="id").execute()
                        time.sleep(1)
                except HttpError as error:
                    logger.error("Google Drive setup failed for %s: %s", file, error)

        except Exception as e:
            logger.error("Google Drive setup failed: %s", e)

    def get_new_credentials(self):
        if not os.path.exists(CLIENT_SECRET_PATH):
            raise FileNotFoundError(
                f"Google OAuth client secret not found. Place it at {CLIENT_SECRET_PATH} "
                "or set NLVE_GOOGLE_CLIENT_SECRET_PATH."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        return creds

    def get_folder_id_by_name(self, folder_name):
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        results = self.service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
        items = results.get('files', [])
        if items:
            return items[0].get('id')
        return None

    def find_file_by_name(self, file_name):
        if not self.folder_id:
            logger.warning("Folder ID is not set for %s", file_name)
            return None
        query = f"name='{file_name}' and '{self.folder_id}' in parents"
        results = self.service.files().list(q=query,
                                                spaces='drive',
                                                fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            return None
        else:
            return items[0]

    def find_file_id_by_name(self, file_name):
        if not self.folder_id:
            logger.warning("Folder ID is not set for %s", file_name)
            return None
        query = f"name='{file_name}' and '{self.folder_id}' in parents"
        results = self.service.files().list(q=query,
                                            spaces='drive',
                                            fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            return None
        else:
            return items[0].get("id")

    def upload_file(self, local_file_path, drive_file_name):
        file_metadata = {
            "name": drive_file_name,
            "parents": [self.folder_id]  # Specify the folder ID here
        }
        media_file = open(local_file_path, "rb")
        media = MediaIoBaseUpload(media_file, mimetype="text/csv")

        try:
            existing_file = self.find_file_by_name(drive_file_name)
            if existing_file:
                self.file_id = existing_file.get("id")
                file = self.service.files().update(fileId=self.file_id, media_body=media, body=file_metadata).execute()
            else:
                file = self.service.files().create(body=file_metadata, media_body=media, fields="id").execute()
                self.file_id = file.get("id")
        finally:
            media_file.close()

        return self.file_id

    def upload_file_content(self, file_content, drive_file_name):
        media_body = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='text/csv', resumable=True)
        file_metadata = {
            "name": drive_file_name,
        }

        existing_file = self.find_file_by_name(drive_file_name)
        if existing_file:
            self.file_id = existing_file.get("id")
            response = self.service.files().update(fileId=self.file_id, media_body=media_body,
                                                   body=file_metadata).execute()
        else:
            response = self.service.files().create(body=file_metadata, media_body=media_body, fields="id").execute()
            self.file_id = response.get("id")

        return response

    def download_file_content(self, file_id):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()

    def download_file(self, file_id, local_file_path):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_file_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.close()

    def write_frequency_data(self, reminder_frequency, reminder_message):
        file_name = "reminder_data.csv"
        existing_file = self.find_file_by_name(file_name)
        file_id = existing_file.get("id") if existing_file else None

        with io.StringIO() as file_content:
            writer = csv.writer(file_content)
            writer.writerow([reminder_frequency, reminder_message])
            file_content.seek(0)

            if file_id:
                self.upload_file_content(file_content.getvalue().encode('utf-8'), file_name)
            else:
                self.upload_file_content(file_content.getvalue().encode('utf-8'), file_name)

    def read_frequency_data(self):
        file_name = "reminder_data.csv"
        existing_file = self.find_file_by_name(file_name)
        file_id = existing_file.get("id") if existing_file else None

        if file_id:
            file_content = self.download_file_content(file_id)
            with io.StringIO(file_content.decode('utf-8')) as file:
                reader = csv.reader(file)
                for row in reader:
                    return row[0], row[1]

        return None, None
