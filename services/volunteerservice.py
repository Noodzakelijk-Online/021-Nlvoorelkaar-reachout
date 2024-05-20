import logging

from config.settings import headers
from models.sessionmanager import SessionManager
from services.UrlService import UrlService
from bs4 import BeautifulSoup


class VolunteerService:

    @staticmethod
    def get_volunteers(notifier, checkbox_vars, location_ids_types, location, distance) -> list:
        url = UrlService.build_url_volunteers(checkbox_vars, location_ids_types, location, distance)
        volunteers_ids = []
        current_page = 1
        try:
            response = SessionManager.get_session().get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            key = soup.find('input', {'name': 'key'})['value']
            url = f"{url}&key={key}"
        except Exception as e:
            logging.error(f'Error while getting volunteers: {e.__str__()}')
            return []

        while True:
            page_url = f"{url}&p={current_page}&submitSearchForm=1#"
            try:
                response = SessionManager.get_session().get(page_url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')

                elements = soup.find_all(['article', 'section'])
                for element in elements:
                    classes = set(element.get('class', []))
                    if element.name == 'section' and {'c-results-banner', 'c-results-banner--center'}.issubset(classes):
                        break

                    if element.name == 'article' and {'c-card', 'c-card--offer', 'js-card'}.issubset(classes):
                        anchor = element.find('a', {'class': 'c-card__anchor'})
                        if anchor:
                            volunteer_id = anchor.get('id')
                            volunteers_ids.append(volunteer_id)

                next_button = soup.find('a', {'rel': 'next'})
                notifier.notify_progresse_get_volunteers(current_page)
                if next_button:
                    current_page += 1
                else:
                    notifier.notify_progresse_get_volunteers(current_page)
                    break
            except Exception as e:
                logging.error(f'Error while getting volunteers: {e.__str__()}')
                return []
        return volunteers_ids

    @staticmethod
    def get_amount_of_volunteer(checkbox_vars, location_ids_types, location, distance) -> str:
        url = UrlService.build_url_volunteers(checkbox_vars, location_ids_types, location, distance)
        response = SessionManager.get_session().get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        total_volunteers = soup.find('span', {'class': 'c-brush-underline__text'}).text
        return total_volunteers
