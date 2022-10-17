import logging
import os
import time
import sys

import requests

from dotenv import load_dotenv

from telegram import Bot, TelegramError

import exceptions
load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# А в таком случае нужно настраивать общий логер?
# Ведь ниже мы создаём логер для проекта
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
    """Отправляем сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Успешно отправили сообщение {message}')
    except TelegramError as tg_error:
        logger.error(f'Сообщнеие не отправлено: {tg_error}')


def get_api_answer(current_timestamp):
    """Запрос к сервису."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
        if response.status_code != 200:
            error_msg = (
                f'Эндпоинт {ENDPOINT} недоступен.'
                f'Код ошибки: {response.status_code}')
            logger.error(error_msg)
            raise exceptions.TheAnswerIsNot200Error(error_msg)
        response = response.json()

        return response
    except Exception as error:
        error_msg = (f'Ошибка при запросе, эндпоинт недоступен: {error}')
        logger.error(error_msg)
        raise exceptions.RequestExceptionError(error)


def check_response(response):
    """Функция проверки корректности ответа ЯП."""
    try:
        timestamp = response['current_date']
    except KeyError:
        logger.error(
            'Ключ current_date отсутствует'
        )
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error(
            'Ключ homeworks отсутствует'
        )
    if isinstance(timestamp, int) and isinstance(homeworks, list):
        return homeworks
    else:
        raise Exception


def parse_status(homework):
    """Получаем статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError()
    if homework_status is None:
        raise KeyError()
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise KeyError()


def check_tokens():
    """Проверяем обязательные токены."""
    no_token_msg = ('Отсутствует обязательная переменная окружения:')
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
    if check_tokens():
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        prev_hw = ''
        prev_status = ''
        prev_error = ''
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
                if prev_hw != hw_name and prev_status != hw_status:
                    message = parse_status(homework)
                    send_message(bot, message)
                    prev_hw = homework.get('homework_name')
                    prev_status = homework.get('status')
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                # А тут я применил нечеловеческую хитрость личинки джуна
                # P.S как сравнивают ошибки нормальные люди?
                # У них наверное возвращается код ошибки
                if str(error) != prev_error:
                    send_message(bot, message)
                    prev_error = str(error)
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
