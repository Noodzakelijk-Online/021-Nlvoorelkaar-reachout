import time

import requests
from bs4 import BeautifulSoup

from config.settings import headers
from models.sessionmanager import SessionManager


def get_profile_url(url):
    response = SessionManager.get_session().get(url, headers=headers)
    # Check if the request was successful
    if response.status_code == 200:
        # Step 2: Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')

        # Step 3: Find the specific <div> element with the class "block block--small block--square text--center first"
        target_div = soup.find('div', class_="block block--small block--square text--center first")

        if target_div:
            # Step 4: Inside this div, find the <div> element with the class "meta"
            meta_div = target_div.find('div', class_="meta")

            if meta_div:
                # Step 5: Find the <a> tag inside the meta div
                a_tag = meta_div.find('a')

                if a_tag:
                    # Step 6: Get the href attribute of the <a> tag
                    href = a_tag.get('href')
                    print(f'Found href: {href}')
                else:
                    print("No <a> tag found inside the meta div.")
            else:
                print("No div with class 'meta' found inside the target div.")
        else:
            print("No div with class 'block block--small block--square text--center first' found.")
    else:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
