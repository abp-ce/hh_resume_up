import logging
import os
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv, set_key

HH_URL = 'https://api.hh.ru'
HH_API_URL = 'https://api.hh.ru'

load_dotenv()
logger = logging.getLogger(__name__)


class ResumeUp:
    def __init__(self):
        self.access_token = os.getenv('ACCESS_TOKEN')
        self.refresh_token = os.getenv('REFRESH_TOKEN')
        self.headers = {'Authorization': 'Bearer ' + self.access_token}
        t_token = os.getenv('TELEGRAM_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.telegram_url = (
            f'https://api.telegram.org/bot{t_token}/'
            f'sendMessage?chat_id={chat_id}&text='
        )
        self.__check_access_token()

    def __send_to_telegram(self, msg):
        response = requests.get(self.telegram_url + msg)
        if response.ok:
            return
        logger.error(response.json())

    def __refresh_env(self):
        set_key('.env', 'ACCESS_TOKEN', self.access_token, quote_mode='never')
        set_key('.env', 'REFRESH_TOKEN', self.refresh_token,
                quote_mode='never')

    def __refresh_token(self):
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        response = requests.post(HH_URL + '/oauth/token', data=data)
        if not response.ok:
            logger.error(response.json())
            return
        jr = response.json()
        self.access_token = jr['access_token']
        self.refresh_token = jr['refresh_token']
        self.headers = {'Authorization': 'Bearer ' + self.access_token}
        self.__refresh_env()

    def __check_access_token(self):
        response = requests.get(HH_API_URL + '/me', headers=self.headers)
        if not response.ok:
            self.__refresh_token()

    def resume_up(self):
        response = requests.get(HH_API_URL + '/resumes/mine',
                                headers=self.headers)
        if not response.ok:
            logger.error(response.json())
            return
        for r in response.json()['items']:
            if r['can_publish_or_update']:
                rr = requests.post(
                    (f'{HH_API_URL}/resumes/{r["id"]}/publish'
                     '?with_professional_roles=true'),
                    headers=self.headers
                )
                if rr.ok:
                    logger.info(f'Поднято {r["title"]}')
                    self.__send_to_telegram(f'Успешно поднято {r["title"]}')
                else:
                    logger.error(rr.json())
                    self.__send_to_telegram(f'Ошибка поднятия {r["title"]}')
            else:
                text = (f'{r["title"]} может быть поднято в'
                        f' {r["next_publish_at"]}')
                logger.debug(text)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler('resume_up.log', maxBytes=51200,
                                  backupCount=3)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(funcName)s %(lineno)d %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    r_up = ResumeUp()
    r_up.resume_up()
