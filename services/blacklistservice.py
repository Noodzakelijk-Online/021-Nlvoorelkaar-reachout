import csv
import io

from google_drive.google_api_services import GoogleDriveManager

class BlacklistService:

    def __init__(self):
        self.google_drive_manager = GoogleDriveManager()

    def add_to_blacklist(self, profile_id: str):
        # Find the file ID of the blacklisted_volunteers.csv file
        file_id = self.google_drive_manager.find_file_id_by_name("blacklisted_volunteers.csv")
        profile_id =  profile_id.strip()
        # Download the existing content of the file
        if file_id:
            existing_content = self.google_drive_manager.download_file_content(file_id)
            with io.StringIO(existing_content.decode('utf-8')) as file:
                reader = csv.reader(file)
                existing_blacklist = list(reader)
                print("Existing blacklist", existing_blacklist)
        else:
            # If file doesn't exist, create an empty list
            existing_blacklist = []

        # Check if the user is already in the blacklist
        if  profile_id in  [row[0] for row in existing_blacklist]:
            print(f"'{profile_id}' is already blacklisted.")
            return

        # Add the new user to the blacklist
        existing_blacklist.append([profile_id])

        # Write the updated blacklist back to the CSV
        with io.StringIO() as file_content:
            writer = csv.writer(file_content)
            writer.writerows(existing_blacklist)
            file_content.seek(0)
            self.google_drive_manager.upload_file_content(file_content.getvalue().encode('utf-8'), "blacklisted_volunteers.csv")

        print(f"'{profile_id}' has been added to the blacklist.")

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

    def check_if_was_blacklisted(self, profile_id: str) -> bool:
        ids = self.get_blacklisted_users()
        if profile_id in ids:
            return True

        return False

    def remove_from_blacklist(self, profile_id: str):
        """Removes a user ID from the blacklist CSV file.

        Args:
            profile_id: The ID of the user to remove from the blacklist.
        """
        # Find the file ID of the blacklisted_volunteers.csv file
        file_id = self.google_drive_manager.find_file_id_by_name("blacklisted_volunteers.csv")
        profile_id = profile_id.strip()

        # Download the existing content of the file
        if file_id:
            existing_content = self.google_drive_manager.download_file_content(file_id)
            with io.StringIO(existing_content.decode('utf-8')) as file:
                reader = csv.reader(file)
                existing_blacklist = list(reader)
        else:
            # If file doesn't exist, there's nothing to delete
            print("Blacklist file not found. No users to remove.")
            return

        # Check if the user is in the blacklist
        if profile_id not in [row[0] for row in existing_blacklist]:
            print(f"'{profile_id}' is not currently blacklisted.")
            return

        # Filter out the user from the blacklist
        filtered_blacklist = [row for row in existing_blacklist if row[0] != profile_id]

        # Write the updated blacklist back to the CSV
        with io.StringIO() as file_content:
            writer = csv.writer(file_content)
            writer.writerows(filtered_blacklist)
            file_content.seek(0)
            self.google_drive_manager.upload_file_content(file_content.getvalue().encode('utf-8'),
                                                          "blacklisted_volunteers.csv")

        print(f"'{profile_id}' has been removed from the blacklist.")


