import telebot
from db import *
from config1 import *
import logging
from sentry_sdk.integrations.logging import LoggingIntegration
import ipaddress
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import lxml
import re

sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.WARNING
)
logging.basicConfig(
    level=logging.INFO,
    format=LOGGER_FORMAT,
    filename='process_handler.log',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)


def processing_handler_command_start(message: str):
    try:
        logger.info(f"Processing handler command start")
        user_id = message.from_user.id
        if not check_user_in_db(user_id):
            set_user_id(user_id)
            welcome_message(message)
    except Exception as e:
        logger.error(f"Error while processing handler command start: {e}")


def processing_handler_command_status(message: str):
    logger.info(f"Processing handler command status")
    try:
        with requests.Session() as session:
            response = session.get(MUON_NODES_URL)
            response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, features='lxml')
        info = get_info_from_xml(soup)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        messages = f"Muon Nodes Status:\n"
        messages += "============================\n"
        messages += f"⚙️ Total Nodes: {info[0]}\n"
        messages += f"✔️ Active Nodes: {info[1]}\n"
        deactive_nodes = int(int(info[0])-int(info[2]))
        messages += f"❌ Deactive Nodes: {deactive_nodes}\n"
        messages += "============================\n"
        messages += f"Data as of {current_time}\n"
        bot.send_message(message.chat.id, messages)
    except Exception as e:
        logger.error(f'Parsing status error: {str(e)}')
    pass


def processing_handler_command_about(message: str) -> None:
    logger.info(f"Processing handler command about")
    try:
        bot.send_message(message.chat.id, ABOUT)
    except Exception as e:
        logger.error(f"Error while processing handler command about: {e}")


def processing_handler_command_help(message: str) -> None:
    logger.info(f"Processing handler command help")
    try:
        bot.send_message(message.chat.id, HELP)
    except Exception as e:
        logger.error(f"Error while processing handler command help: {e}")


def welcome_message(message: str) -> None:
    logger.info(f"Sending welcome message to {message.from_user.first_name}")
    bot.send_message(message.chat.id, f"Hello {message.from_user.first_name}!\n\nEnter the IP of you Muon node")


def check_ip_address(message: str, ip_address: str) -> bool:
    logger.info(f"Checking IP address {ip_address}")
    try:
        ipaddress.ip_address(ip_address)
        logger.info(f"IP address {ip_address} is valid")
        return True
    except ValueError as e:
        logger.error(f'Invalid IP address: {str(e)}')
        bot.send_message(
            chat_id=message.chat.id,
            text="The IP address is incorrect. Please try again.")
        return False


def get_info_from_xml(soup: str) -> None:
    logger.info(f"Getting info from XML")
    tag_total_div = soup.find('div', attrs={
        'class': 'col-md-4 col-12 d-flex align-items-end'})
    total_nodes = tag_total_div.find_all(
        'h4', class_='fw-bold mb-0')
    total_nodes= total_nodes[0].get_text()
    tag_active_div = soup.find('div', attrs={
        'class': 'col-md-7 col-12 d-flex align-items-end justify-content-lg-start justify-content-md-end ms-lg-4 ps-xl-4'})
    active_nodes = tag_active_div.find_all(
        'h4', class_='sc-d9568944-6 jRQSOr fw-bold mb-0')
    active_nodes = active_nodes[0].get_text()
    number_active = re.findall(r'\d+', active_nodes)
    info = [total_nodes, active_nodes, number_active[0]]
    return info
