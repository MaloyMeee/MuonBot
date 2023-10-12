import telebot
from telebot import types
from config1 import *
from process_handler import *
import db
import logging
import sentry_sdk
from config1 import *
from sentry_sdk.integrations.logging import LoggingIntegration

sentry_sdk.init(
    dsn=DSN,
    traces_sample_rate=0.85,
)
sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.WARNING
)
logging.basicConfig(
    level=logging.INFO,
    format=LOGGER_FORMAT,
    filename='bot.log',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)
db.inicialize_db()


@bot.message_handler(commands=['start'])
def handler_command_start(message: str) -> None:
    processing_handler_command_start(message)


@bot.message_handler(commands=['status'])
def handler_command_status(message: str) -> None:
    processing_handler_command_status(message)


@bot.message_handler(commands=['about'])
def handler_command_about(message: str) -> None:
    processing_handler_command_about(message)


@bot.message_handler(commands=['help'])
def handler_command_help(message: str) -> None:
    processing_handler_command_help(message)


def main() -> None:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)


main()
