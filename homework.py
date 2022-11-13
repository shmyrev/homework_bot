import logging
import os
import time

import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

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


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат, определяемый переменной окружения.
    TELEGRAM_CHAT_ID. Принимает на вход два параметра: экземпляр класса
    Bot и строку с текстом сообщения.
    """
    bot_send_message = bot.send_message(TELEGRAM_CHAT_ID, message)
    return bot_send_message


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса. В качестве.
    параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата
    JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    response = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    response_content = response.json()
    if response.status_code == HTTPStatus.OK:
        return response_content
    else:
        raise Exception(
            'Ошибка при обращении к API Яндекс.Практикума: ',
            f'Код ответа: {response_content.get("code")}',
            f'Сообщение сервера: {response_content.get("message")}'
        )


def check_response(response):
    """Проверяет ответ API на корректность. В качестве параметра функция.
    получает ответ API, приведенный к типам данных Python. Если ответ
    API соответствует ожиданиям, то функция должна вернуть список
    домашних работ (он может быть и пустым), доступный в ответе API по
    ключу 'homeworks'.
    """
    try:
        timestamp = response['current_date']
    except KeyError:
        logging.error(
            'Ключ current_date в ответе API Яндекс.Практикум отсутствует'
        )
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error(
            'Ключ homeworks в ответе API Яндекс.Практикум отсутствует'
        )
    if isinstance(timestamp, int) and isinstance(homeworks, list):
        return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой.
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
        assert False


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы для.
    работы программы. Если отсутствует хотя бы одна переменная окружения
    — функция должна вернуть False, иначе — True.
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)

            homeworks = check_response(response)
            if len(homeworks) > 0:
                homework = homeworks[0]
                verdict_status = parse_status(homework)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)
        else:
            send_message(bot, verdict_status)
            logging.info('Удачная отправка сообщения в Telegram')


if __name__ == '__main__':
    main()
