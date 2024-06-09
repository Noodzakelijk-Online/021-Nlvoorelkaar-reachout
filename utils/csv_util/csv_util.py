import csv
import pathlib
import sys
from datetime import date, datetime
from os.path import join, dirname

contacts_date_path = pathlib.Path(join(dirname(sys.executable), 'test.csv'))
chats_no_response_path = pathlib.Path(join(dirname(sys.executable), 'chats_no_response.csv'))


def contact_date_to_csv(volunteer_id: str):
    """
    Update the last contact date for the volunteer with the given volunteer_id.
    If the volunteer_id is not found in the file, a new record will be added.

    :param volunteer_id: The id of the volunteer.

    :return: None
    """
    today = date.today()
    six_months_ago = today.replace(month=today.month - 6) if today.month >= 6 else today.replace(year=today.year - 1,
                                                                                                 month=today.month + 6)

    with open(contacts_date_path, 'r+', newline='') as file:
        reader = csv.reader(file)
        writer = csv.writer(file)
        rows = list(reader)  # Read all rows into memory

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
            file.seek(0)  # Move pointer to beginning of file
            writer.writerows(rows)
        if not updated:  # Here's the logic to check for new volunteer_id
            # Write logic here to add a new row with volunteer_id and today's date
            new_row = [volunteer_id, today.strftime('%Y-%m-%d')]
            rows.append(new_row)  # Add new row to the in-memory list
            file.seek(0)  # Move pointer to beginning of file again
            writer.writerows(rows)  # Write updated list with new row


def pre_send_message_check(volunteer_id: str):
    """
    Check if the message can be sent to the volunteer with the given volunteer_id.
    The message can be sent if the last contact date is more than six months ago
    or if the volunteer_id is not found in the file.

    :param volunteer_id: The id of the volunteer.

    :return: True if the message can be sent, False otherwise.
    """
    today = date.today()
    six_months_ago = today.replace(month=today.month - 6) if today.month >= 6 else today.replace(year=today.year - 1,
                                                                                                 month=today.month + 6)
    last_contact_date = None
    with open(contacts_date_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            # Check if the row is empty before accessing elements
            if len(row) > 0 and row[0] == volunteer_id:
                last_contact_date = datetime.strptime(row[1], '%Y-%m-%d').date()
                break  # Stop reading after finding the volunteer_id

        if last_contact_date is None or last_contact_date <= six_months_ago and not check_if_volunteer_id_is_banned(
                volunteer_id):
            print(f"Sending message to volunteer with id {volunteer_id}")
            return True
        elif not check_if_volunteer_id_is_banned(volunteer_id):
            print(f"Cannot send message to volunteer with id {volunteer_id}: Volunteer is banned")
            return False
        else:
            print(f"Cannot send message to volunteer with id {volunteer_id}: Last contact date is {last_contact_date}")
            return False


def check_if_volunteer_id_is_banned(volunteer_id: str):
    """
    Check if the volunteer with the given volunteer_id is banned from receiving messages.

    :param volunteer_id: The id of the volunteer.

    :return: False if the volunteer is banned, True if he was banned more than 12 months ago or if he is not banned.
    """
    today = date.today()
    twelve_months_ago = today.replace(year=today.year - 1)
    with open(chats_no_response_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            # Check if the row is empty before accessing elements
            if len(row) > 0 and row[0].split('/')[-1] == volunteer_id and int(row[2]) > 4:
                last_contact_date = datetime.strptime(row[1], '%Y-%m-%d').date()
                return last_contact_date <= twelve_months_ago
    return False



