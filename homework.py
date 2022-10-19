import logging
import os
import time
import sys

import requests

from dotenv import load_dotenv

from telegram import Bot, TelegramError
from http import HTTPStatus

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


RETRY_TIME = 10 * 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
    'missing': 'Работы на проверку нет. Грусть :('
}


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    logger.info(f'{send_message.__name__} начинает работу')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError as tg_error:
        logger.error(f'Сообщнеие не отправлено: {tg_error}')
        raise tg_error()
    else:
        logger.info(f'Успешно отправили сообщение {message}')


def get_api_answer(current_timestamp):
    """Запрос к сервису."""
    logger.info(f'{get_api_answer.__name__} начинает работу')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    requests_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }

    try:
        response = requests.get(**requests_params)
        if response.status_code != HTTPStatus.OK:
            error_msg = (f'Эндпоинт {ENDPOINT} недоступен.\n'
                         f'Статус ответа: {response.status_code}.\n'
                         f'Параметры запроса: {requests_params}.\n')

            logger.error(error_msg)
            raise exceptions.TheAnswerIsNot200Error(error_msg)
        response = response.json()
        return response
    except Exception as error:
        error_msg = (f'Ошибка при запросе, эндпоинт недоступен: {error}\n'
                     f'Параметры запроса: {requests_params}.\n')
        logger.error(error_msg)
        raise exceptions.RequestExceptionError(error)


def check_response(response):
    """Функция проверки корректности ответа ЯП."""
    logger.info(f'{check_response.__name__} начинает работу')
    if not isinstance(response, dict):
        error_msg = f'response должен быть словарём, сейчас - {type(response)}'
        logger.error(error_msg)
        raise TypeError(error_msg)
    try:
        timestamp = response['current_date']
    except KeyError:
        error_msg = ('Ключ current_date отсутствует.\n'
                     f'Ответ: {response}.\n')
        logger.error(error_msg)
        raise KeyError(error_msg)
    try:
        homeworks = response['homeworks']
    except KeyError:
        error_msg = ('Ключ homeworks отсутствует.\n'
                     f'Ответ: {response}.\n')
        logger.error(error_msg)
        raise KeyError(error_msg)
    if not isinstance(homeworks, list):
        error_msg = (f'Домашние работы должны быть списком, '
                     f'сейчас - {type(homeworks)}')
        logger.error(error_msg)
        raise KeyError(error_msg)
    if not isinstance(timestamp, int):
        error_msg = ('Текущее время должно быть числом, '
                     f'сейчас - {type(timestamp)}')
        logger.error(error_msg)
        raise KeyError(error_msg)
    return homeworks


def parse_status(homework):
    """Получаем статус домашней работы."""
    logger.info(f'{parse_status.__name__} начинает работу')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        error_msg = ('В словаре отсутсвует имя домашней работы.\n'
                     f'Словарь - {homework}')
        logger.error(error_msg)
        raise KeyError(error_msg)
    if homework_status not in HOMEWORK_STATUSES:
        error_msg = (f'Неизвестный статус домашней работы - {homework_status}')
        logger.error(error_msg)
        raise KeyError(error_msg)

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем обязательные токены."""
    logger.info(f'{check_tokens.__name__} начинает работу')
    no_token_msg = 'Отсутствует обязательная переменная окружения: '
    flag = True
    if PRACTICUM_TOKEN is None:
        flag = False
        logger.critical(f'{no_token_msg} PRACTICUM_TOKEN')
    if TELEGRAM_TOKEN is None:
        flag = False
        logger.critical(f'{no_token_msg} TELEGRAM_TOKEN')
    if TELEGRAM_CHAT_ID is None:
        flag = False
        logger.critical(f'{no_token_msg} TELEGRAM_CHAT_ID')
    return flag


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise exceptions.MandatoryTokenError()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_homework = ''
    previous_status = ''
    previous_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) != 0:
                homework = homework[0]
            else:
                homework = {'homework_name': 'There is no homework yet',
                            'status': 'missing'
                            }
            hw_name = homework.get('homework_name')
            hw_status = homework.get('status')
            if previous_homework != hw_name and previous_status != hw_status:
                message = parse_status(homework)
                send_message(bot, message)
                previous_homework = homework.get('homework_name')
                previous_status = homework.get('status')
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if str(error) != previous_error:
                send_message(bot, message)
                previous_error = str(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
