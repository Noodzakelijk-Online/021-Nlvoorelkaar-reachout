import logging
from bs4 import BeautifulSoup

from config.settings import headers
from models.sessionmanager import SessionManager

logger = logging.getLogger(__name__)

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
                    logger.info('Extracted profile id from offer page')
                    return id
                else:
                    logger.warning("No profile link found inside offer metadata")
            else:
                logger.warning("No metadata block found on offer page")
        else:
            logger.warning("No profile metadata container found on offer page")
    else:
        logger.warning("Failed to retrieve offer page: status %s", response.status_code)


def get_offer_url_from_chat_page(chat_url):
    response = SessionManager.get_session().get(chat_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        offer_dd = soup.select_one('#content > div.site-retain.react-dashboard-menu > div > div.col-span-9 > dl > dd:nth-child(4) > a')
        if offer_dd:
            if 'href' in offer_dd.attrs:
                offer_url = offer_dd['href'].strip()

                return f"https://www.nlvoorelkaar.nl{offer_url}"
            else:
                logger.warning("Offer link found without href")
                return None
        else:
            logger.warning("Offer link not found on chat page")
            return None
    else:
        logger.warning("Failed to retrieve chat page: status %s", response.status_code)
        return None

