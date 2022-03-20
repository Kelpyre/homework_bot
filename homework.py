"""Telegram-бот для проверки статуса домашних заданий Yandex.Практикум."""

import logging
import os
import re
import sys
import time

import requests
import telegram

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    encoding='utf-8',
)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Функция отправки сообщения в Telegram."""
    logger.info('Попытка отправки сообщения')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Успешно отправлено сообщение')
    except Exception as error:
        log_message = f'Ошибка при отправке сообщения: {error}'
        logger.error(log_message)


def get_api_answer(current_timestamp):
    """Функция запроса к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    raw_response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if raw_response.status_code == 500:
        raise Exception('Сервер не отвечает')
    if raw_response.status_code != 200:
        raise Exception('Ошибка при получении ответа от сервера')
    response = raw_response.json()
    return response


def check_response(response):
    """Функция проверки ответа API."""
    homework = response['homeworks']
    try:
        if isinstance(response, dict):
            if isinstance(homework, list):
                return homework
    except Exception as error:
        log_message = f'Ошибка при получении ответа от API: {error}'
        logger.error(log_message)


def parse_status(homework):
    """Функция извлечения данных из информации API."""
    if homework:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
        message = ('Изменился статус проверки работы "%s". %s' %
                   (homework_name, verdict))
        return message


def check_tokens():
    """Функция проверки токенов."""
    try:
        if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            return True
        return False
    except Exception as error:
        log_message = f'Возникла проблема с проверкой TOKENS: {error}'
        logging.error(log_message)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error = TypeError()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if check_tokens() is True:
                if homework:
                    homework = homework[0]
                    send_message(bot, parse_status(homework))
                    current_timestamp = int(time.time())
                    time.sleep(RETRY_TIME)
                else:
                    log_message = 'Нет обновлений'
                    logging.debug(log_message)
                    time.sleep(RETRY_TIME)
            else:
                log_message = 'Проверка токенов вернула False'
                logging.critical(log_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if error.args != last_error.args:
                send_message(bot, message)
                last_error = error
            else:
                last_error = error
            time.sleep(RETRY_TIME)
        else:
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Выполнение остановлено')
        sys.exit(0)
