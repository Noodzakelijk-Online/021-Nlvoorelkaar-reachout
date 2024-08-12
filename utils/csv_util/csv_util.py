import csv
import io
import pathlib
import sys
from datetime import date, datetime
from os.path import join, dirname

from dateutil.relativedelta import relativedelta

from google_drive.google_api_services import GoogleDriveManager



def contact_date_to_csv(volunteer_id: str, drive_manager: GoogleDriveManager):
    """
    Update the last contact date for the volunteer with the given volunteer_id.
    If the volunteer_id is not found in the file, a new record will be added.

    :param volunteer_id: The id of the volunteer.
    :param drive_manager: An instance of GoogleDriveReminderManager.

    :return: None
    """
    today = date.today()
    six_months_ago = today - relativedelta(months=6)
    file_id = drive_manager.find_file_id_by_name("contacts_date.csv")
    file_content = drive_manager.download_file_content(file_id)
    rows = list(csv.reader(io.StringIO(file_content.decode('utf-8'))))

    # Update existing record or add new record
    updated = False
    for i, row in enumerate(rows):
        if len(row) >= 2 and row[0] == volunteer_id:
            last_contact_date = datetime.strptime(row[1], '%Y-%m-%d').date()
            if last_contact_date <= six_months_ago:
                row[1] = today.strftime('%Y-%m-%d')  # Update date format
                updated = True
            break  # Stop reading after finding the volunteer_id

    # Write updated rows back to the file
    if updated:
        file_content = io.StringIO()
        writer = csv.writer(file_content)
        writer.writerows(rows)
        drive_manager.upload_file_content(file_content.getvalue().encode('utf-8'), "contacts_date.csv")
    if not updated:  # Here's the logic to check for new volunteer_id
        new_row = [volunteer_id, today.strftime('%Y-%m-%d')]
        rows.append(new_row)  # Add new row to the in-memory list
        file_content = io.StringIO()
        writer = csv.writer(file_content)
        writer.writerows(rows)  # Write updated list with new row
        drive_manager.upload_file_content(file_content.getvalue().encode('utf-8'),  "contacts_date.csv")



def pre_send_message_check(volunteer_id: str, drive_manager: GoogleDriveManager):
    """
    Check if the message can be sent to the volunteer with the given volunteer_id.
    The message can be sent if the last contact date is more than six months ago
    or if the volunteer_id is not found in the file.

    :param volunteer_id: The id of the volunteer.
    :param drive_manager: An instance of GoogleDriveReminderManager.

    :return: True if the message can be sent, False otherwise.
    """
    today = date.today()
    six_months_ago = today - relativedelta(months=6)
    file_id = drive_manager.find_file_id_by_name("contacts_date.csv")
    file_content = drive_manager.download_file_content(file_id)
    rows = []
    if file_content:
        file_stream = io.StringIO(file_content.decode('utf-8'))
        reader = csv.reader(file_stream)
        rows = list(reader)

    last_contact_date = None
    for i, row in enumerate(rows):
        # Check if the row is empty before accessing elements
        if len(row) > 0 and row[0] == volunteer_id:
            last_contact_date = datetime.strptime(row[1], '%Y-%m-%d').date()
            break  # Stop reading after finding the volunteer_id

    if last_contact_date is None or last_contact_date <= six_months_ago:
        if not check_if_volunteer_id_is_banned(volunteer_id, drive_manager):
            print(f"Sending message to volunteer with id {volunteer_id}")
            return True
        else:
            print(f"Cannot send message to volunteer with id {volunteer_id}: Volunteer is banned")
            return False
    else:
        print(f"Cannot send message to volunteer with id {volunteer_id}: Last contact date is {last_contact_date}")
        return False

def check_if_volunteer_id_is_banned(volunteer_id: str, drive_manager: GoogleDriveManager):
    """
    Check if the volunteer with the given volunteer_id is banned from receiving messages.

    :param volunteer_id: The id of the volunteer.
    :param drive_manager: An instance of GoogleDriveReminderManager.

    :return: False if the volunteer is banned, True if he was banned more than 12 months ago or if he is not banned.
    """
    today = date.today()
    twelve_months_ago = today.replace(year=today.year - 1)
    file_id = drive_manager.find_file_id_by_name("chats_no_response.csv")
    file_content = drive_manager.download_file_content(file_id)
    rows = list(csv.reader(io.StringIO(file_content.decode('utf-8'))))

    for row in rows:
        # Check if the row is empty before accessing elements
        if len(row) > 0 and row[0].split('/')[-1] == volunteer_id and int(row[2]) > 4:
            last_contact_date = datetime.strptime(row[1], '%Y-%m-%d').date()
            return last_contact_date <= twelve_months_ago
    return False



