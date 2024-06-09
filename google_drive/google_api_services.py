import os
import csv
import time
from datetime import datetime, date
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io

SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleDriveReminderManager:
    def __init__(self):
        self.creds = None
        self.service = None
        self.file_id = None
        self.setup()

    def setup(self):
        creds = None
        if os.path.exists("google_drive/token.json"):
            if Credentials.from_authorized_user_file("google_drive/token.json", SCOPES) is not None:
                creds = Credentials.from_authorized_user_file("google_drive/token.json", SCOPES)
            else:
                print("Token file is empty")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "google_drive/credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("google_drive/token.json", "w") as token:
                token.write(creds.to_json())

        try:
            service = build("drive", "v3", cache_discovery=False, credentials=creds)
            self.service = service
            print("Google Drive service setup successfully")

            files = ["contacts_date.csv", "reminder_data.csv", "chats_no_response.csv"]
            for file in files:
                try:
                    existing_file = self.find_file_by_name(file)
                    if existing_file:
                        print(f"File {file} exists")
                    else:
                        file_metadata = {"name": file}
                        file = self.service.files().create(body=file_metadata, fields="id").execute()
                        time.sleep(1)
                        print(f"File {file} created")
                except HttpError as error:
                    print("An error occurred: %s" % error)

        except Exception as e:
            print("An error occurred: %s" % e)



    def find_file_by_name(self, file_name):
        results = self.service.files().list(q=f"name='{file_name}'",
                                            spaces='drive',
                                            fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            return None
        else:
            return items[0]

    def find_id_by_name(self, file_name):
        results = self.service.files().list(q=f"name='{file_name}'",
                                            spaces='drive',
                                            fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            return None
        else:
            return items[0].get("id")

    def upload_file(self, local_file_path, drive_file_name):
        file_metadata = {"name": drive_file_name}
        media = MediaIoBaseUpload(open(local_file_path, "rb"), mimetype="text/csv")

        existing_file = self.find_file_by_name(drive_file_name)
        if existing_file:
            self.file_id = existing_file.get("id")
            file = self.service.files().update(fileId=self.file_id, media_body=media, body=file_metadata).execute()
        else:
            file = self.service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            self.file_id = file.get("id")

        return self.file_id

    def upload_file_content(self, file_content, file_id, drive_file_name):
        media_body = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='text/csv', resumable=True)
        file_metadata = {"name": drive_file_name}

        existing_file = self.find_file_by_name(drive_file_name)
        if existing_file:
            print("File", drive_file_name, "already exists")
            self.file_id = existing_file.get("id")
            response = self.service.files().update(fileId=self.file_id, media_body=media_body, body=file_metadata).execute()
        else:
            print("File", drive_file_name, "does not exist. Creating new file")
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
                self.upload_file_content(file_content.getvalue().encode('utf-8'), file_id, file_name)
            else:
                self.upload_file_content(file_content.getvalue().encode('utf-8'), None, file_name)

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


def main():
    manager = GoogleDriveReminderManager()
    # Example usage
    manager.write_frequency_data('weekly', 'This is a reminder message.')
    frequency, message = manager.read_frequency_data()
    print(f'Frequency: {frequency}, Message: {message}')


if __name__ == "__main__":
    main()
