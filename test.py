import os
from dotenv import load_dotenv
import requests
from pprint import pprint

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
params = {'from_date': 1662015741}
response = requests.get(
    ENDPOINT, headers=HEADERS, params=params
)
response = response.json()

pprint(response.get('homeworks'))


def check_response(response):
    """Проверяем response на корректность."""

    empty_response = {'homework_name': 'There is no homework to check',
                      'status': 'There is no homework yet'}
    if not isinstance(response, dict):
        error_msg = ('response не является словарём')
        logger.error(error_msg)
        raise TypeError(error_msg)
    if response.get('homeworks') is None:
        logger.error('Ошибка ключа, ожидаем ключ homeworks'
                     'в словаре response')
        raise exceptions.EmptyDictionaryError()
    if len(response.get('homeworks')) == 0:
        return empty_response
    if ('homework_name' in response.get('homeworks')[0].keys()
            and 'status' in response.get('homeworks')[0].keys()):
        return response.get('homeworks')
