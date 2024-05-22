import logging
import os
import requests
import time
from dotenv import load_dotenv
from telebot import TeleBot
from http import HTTPStatus
from logging import StreamHandler

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    variables = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return all(variables)


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        logger.info(f'Попытка отправки сообщения: {message}')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f'{message}'
        )
        logger.debug(f'Сообщение успешно отправлено: {message}')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения в телеграм: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса.
    Принимает временную метку, возвращает ответ API,
    приведенный к типам данных Python.
    """
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise Exception(f'Получен код ответа {response.status_code}')
        response = response.json()
    except requests.RequestException as error:
        logger.error(f'Ошибка запроса к экдпоинту: {error}')
    return response


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Структура ответа не соответствует документации')
    response = response.get('homeworks')
    if not isinstance(response, list):
        raise TypeError(
            'Под ключом homeworks данные приходят не в виде списка.')
    if response:
        return response[0]
    else:
        logger.debug('Новой домашки нет')


def parse_status(homework):
    """Извлекает статус из информации о конкретной домашней работе."""
    if 'homework_name' not in homework:
        raise Exception('Нет ключа homework_name')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise Exception('Недокументированный статус')


def get_current_date(response):
    """Извлекает временную метку из ответа API."""
    return response.get('current_date')


def main():
    """Основная логика работы бота."""
    if check_tokens():
        logger.info('Все переменные окружения найдены')
    else:
        logger.critical('Не все переменные окружения найдены')
        raise SystemExit
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None
    message = None
    while True:
        try:
            answer = get_api_answer(timestamp)
            timestamp = get_current_date(answer)
            check = check_response(answer)
            if check:
                message = parse_status(check)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        if message and last_message != message:
            send_message(bot, message)
            last_message = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
