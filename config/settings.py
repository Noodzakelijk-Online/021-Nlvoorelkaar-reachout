headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-GB,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36'
}

url_base = 'https://www.nlvoorelkaar.nl/'
url_volunteer = f'{url_base}hulpaanbod/'
url_autocomplete = f'{url_base}location/autocomplete?s=3&term='
url_logout = f'{url_base}uitloggen'
url_login_page = 'https://www.nlvoorelkaar.nl/inloggen'
url_login = 'https://www.nlvoorelkaar.nl/login_check'

delay_to_start_sending = 30.7584
minimum_time = 30
maximum_time = 60
