import csv
import io

from google_drive.google_api_services import GoogleDriveManager

class BlacklistService:

    def __init__(self):
        self.google_drive_manager = GoogleDriveManager()

    def add_to_blacklist(self, offer_url: str):
        # Find the file ID of the blacklisted_volunteers.csv file
        file_id = self.google_drive_manager.find_file_id_by_name("blacklisted_volunteers.csv")

        # Download the existing content of the file
        if file_id:
            existing_content = self.google_drive_manager.download_file_content(file_id)
            with io.StringIO(existing_content.decode('utf-8')) as file:
                reader = csv.reader(file)
                existing_blacklist = list(reader)
        else:
            # If file doesn't exist, create an empty list
            existing_blacklist = []

        # Check if the user is already in the blacklist
        if offer_url in [row[0] for row in existing_blacklist]:
            print(f"'{offer_url}' is already blacklisted.")
            return

        # Add the new user to the blacklist
        existing_blacklist.append([offer_url])

        # Write the updated blacklist back to the CSV
        with io.StringIO() as file_content:
            writer = csv.writer(file_content)
            writer.writerows(existing_blacklist)
            file_content.seek(0)
            self.google_drive_manager.upload_file_content(file_content.getvalue().encode('utf-8'), "blacklisted_volunteers.csv")

        print(f"'{offer_url}' has been added to the blacklist.")

    def get_blacklisted_users(self) -> [str]:
        # Find the file ID of the blacklisted_volunteers.csv file
        file_id = self.google_drive_manager.find_file_id_by_name("blacklisted_volunteers.csv")

        if file_id:
            # Download the existing content of the file
            existing_content = self.google_drive_manager.download_file_content(file_id)
            with io.StringIO(existing_content.decode('utf-8')) as file:
                reader = csv.reader(file)
                blacklisted_users = [row[0] for row in reader]
            return blacklisted_users
        else:
            # If file doesn't exist, return an empty list
            return []

    def check_if_was_blacklisted(self, id: str) -> bool:
        urls = self.get_blacklisted_users()
        for url in urls:
            if id in url:
                return True

        return False

