import time

import requests
from bs4 import BeautifulSoup
from cffi.cffi_opcode import PRIM_FLOAT

from config.settings import headers
from models.sessionmanager import SessionManager

def get_profile_id(offer_url):
    response = SessionManager.get_session().get(offer_url, headers=headers)
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

                    id = href.strip("/").split("/")[1]
                    print(f'Found profile_id: {href}')
                    return id
                else:
                    print("No <a> tag found inside the meta div.")
            else:
                print("No div with class 'meta' found inside the target div.")
        else:
            print("No div with class 'block block--small block--square text--center first' found.")
    else:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")


def get_offer_url_from_chat_page(chat_url):
    response = SessionManager.get_session().get(chat_url, headers=headers)
    print("Checking offer url from chat url", chat_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        offer_dd = soup.select_one('#content > div.site-retain.react-dashboard-menu > div > div.col-span-9 > dl > dd:nth-child(4) > a')
        print(offer_dd)
        if offer_dd:
            if 'href' in offer_dd.attrs:
                offer_url = offer_dd['href'].strip()

                return f"https://www.nlvoorelkaar.nl{offer_url}"
            else:
                print("No <a> tag found or no href attribute.")
                return None
        else:
            print("Offer <dd> element not found.")
            return None
    else:
        print(f"Error: Received status code {response.status_code}")
        return None

