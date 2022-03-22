"""Telegram-бот для проверки статуса домашних заданий Yandex.Практикум."""

import logging
import sys
import time

import requests
import telegram
from http import HTTPStatus

from settings import (
    PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    RETRY_TIME, ENDPOINT, HEADERS, HOMEWORK_STATUSES,
)
from exceptions import (
    SendMessageError, Status500Error,
    UnknownStatusError, EmptyListError,
)

if __name__ == '__main__':
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
    except telegram.TelegramError as error:
        log_message = f'Ошибка при отправке сообщения: {error}'
        logger.error(log_message)
        raise SendMessageError(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Функция запроса к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    raw_response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if raw_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR.value:
        raise Status500Error('Сервер не отвечает')
    if raw_response.status_code != HTTPStatus.OK.value:
        raise UnknownStatusError('Ошибка при получении ответа от сервера')
    response = raw_response.json()
    return response


def check_response(response):
    """Функция проверки ответа API."""
    try:
        response['homeworks']
        response['current_date']
    except KeyError as error:
        log_message = f'В ответе сервера нет требуемых ключей: {error}'
        logger.error(log_message)
        raise EmptyListError(f'В ответе сервера нет требуемых ключей: {error}')
    homework = response['homeworks']
    if isinstance(response, dict) and isinstance(homework, list):
        return homework
    else:
        raise TypeError('Тип объекта отличается от ожидаемого')


def parse_status(homework):
    """Функция извлечения данных из информации API."""
    if homework:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES:
            raise KeyError(f'Неизвестный статус {homework_status}')
        verdict = HOMEWORK_STATUSES[homework_status]
        message = (
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )
        return message


def check_tokens():
    """Функция проверки токенов."""
    return all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error = None
    if check_tokens() is not True:
        sys.exit('Возникла ошибка при проверке TOKENS')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            current_date = response['current_date']
            if homework:
                homework = homework[0]
                send_message(bot, parse_status(homework))
                current_timestamp = current_date
            else:
                log_message = 'Нет обновлений'
                logging.debug(log_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if last_error is None:
                send_message(bot, message)
                last_error = error
            else:
                last_error = error
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Выполнение остановлено')
