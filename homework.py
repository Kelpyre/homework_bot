"""Telegram-бот для проверки статуса домашних заданий Yandex.Практикум."""

import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from settings import (
    PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    RETRY_TIME, ENDPOINT, HEADERS, HOMEWORK_STATUSES,
)
from exceptions import (
    SendMessageError, Status500Error,
    UnknownStatusError, EmptyListError,
)

logger = logging.getLogger()


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
    homework = response['homeworks']
    if 'homeworks' not in response or 'current_date' not in response:
        log_message = 'В ответе сервера нет требуемых ключей'
        logger.error(log_message)
        raise EmptyListError('В ответе сервера нет требуемых ключей')
    homework = response['homeworks']
    if not isinstance(response, dict) or not isinstance(homework, list):
        raise TypeError('Тип объекта отличается от ожидаемого')
    return homework


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
    if check_tokens() is False:
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
                logger.debug(log_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_error is None:
                send_message(bot, message)
            last_error = error
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        encoding='utf-8',
    )
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    )
    logger.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Выполнение остановлено')
