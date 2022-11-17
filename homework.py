import logging
import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus

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


class MyCustomError(Exception):
    """Обработка ошибки отправки сообщения."""

    def __init__(self, *args):
        """Инициализатор класса."""
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        """Объект в строку."""
        if self.message:
            return f'Ошибка отправки сообщения {self.message}'
        else:
            return 'Сообщение не удалось отправить'


def send_message(bot, message):
    """function(Bot, str) -> None.
    Отправляет сообщение в Telegram чат, определяемый переменной окружения
    TELEGRAM_CHAT_ID. Принимает на вход два параметра: экземпляр класса
    Bot и строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except MyCustomError(Exception) as error:
        return error


def get_api_answer(current_timestamp):
    """function(int) -> dict.
    Делает запрос к единственному эндпоинту API-сервиса. В качестве.
    параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата
    JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        response_content = response.json()
        if response.status_code == HTTPStatus.OK:
            return response_content
        else:
            raise requests.ConnectionError(
                'Ошибка при обращении к API Яндекс.Практикума: ',
                f'Код ответа: {response_content.get("code")}',
                f'Сообщение сервера: {response_content.get("message")}'
            )
    except requests.ConnectionError as error:
        message = f'Ошибка при обращении к API Яндекс.Практикума. {error}'
        logging.error(error, message)
    except requests.Timeout as error:
        message = f'Ошибка Timeout. {error}'
        logging.error(error, message)
    except requests.RequestException as error:
        message = f'Ошибка отправки запроса. {error}'
        logging.error(error, message)


def check_response(response):
    """function(dict) -> list.
    Проверяет ответ API на корректность. В качестве параметра функция.
    получает ответ API, приведенный к типам данных Python. Если ответ
    API соответствует ожиданиям, то функция должна вернуть список
    домашних работ (он может быть и пустым), доступный в ответе API по
    ключу 'homeworks'.
    """
    if 'current_date' not in response:
        logging.error(
            'Ключ current_date в ответе API Яндекс.Практикум отсутствует'
        )

    if 'homeworks' not in response:
        logging.error(
            'Ключ homeworks в ответе API Яндекс.Практикум отсутствует'
        )

    timestamp = response['current_date']
    homeworks = response['homeworks']

    if isinstance(timestamp, int) and isinstance(homeworks, list):
        return homeworks
    else:
        logging.error(
            'Переменные timestamp и homeworks не соответствуют своему типу'
        )


def parse_status(homework: list) -> str:
    """function(list) -> str.
    Извлекает из информации о конкретной домашней работе статус этой.
    работы. В качестве параметра функция получает только один элемент
    из списка домашних работ. В случае успеха, функция возвращает
    подготовленную для отправки в Telegram строку, содержащую один из
    вердиктов словаря HOMEWORK_STATUSES.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        return f'Статус не изменился "{homework_name}". {verdict}'


def check_tokens():
    """function() -> bool.
    Проверяет доступность переменных окружения, которые необходимы для.
    работы программы. Если отсутствует хотя бы одна переменная окружения
    — функция должна вернуть False, иначе — True.
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        filename='program.log',
        format=('%(asctime)s, %(levelname)s, %(filename)s,'
                '%(funcName)s, %(lineno)s, %(message)s')
    )

    if not check_tokens():
        sys.exit(1)
        sys.stderr('Отсутствует переменная окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            logging.info(f'Получен список работ {response}')
            if len(homeworks) > 0:
                send_message(bot, parse_status(homeworks[0]))
            elif len(homeworks) == 0:
                logging.debug('Нет новых статусов')
                send_message(bot, 'Нет новых статусов')
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)
        else:
            send_message(bot, 'Удачная отправка сообщения в Telegram')
            logging.info('Удачная отправка сообщения в Telegram')


if __name__ == '__main__':
    main()
