import time

import telebot
from db import *
from config import *
import logging
from sentry_sdk.integrations.logging import LoggingIntegration
import ipaddress
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import lxml
import re
import threading as th

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
watchdog = False


def processing_handler_command_start(message: str):
    try:
        logger.info(f"Processing handler command start")
        user_id = message.from_user.id
        if not check_user_in_db(user_id):
            set_user_id(user_id)
            processing_handler_command_status(message)
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
        deactive_nodes = int(int(info[0]) - int(info[2]))
        messages += f"❌ Deactive Nodes: {deactive_nodes}\n"
        messages += "============================\n"
        messages += f"Data as of {current_time}\n"
        bot.send_message(message.chat.id, messages)
    except Exception as e:
        logger.error(f'Parsing status error: {str(e)}')


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


def processing_handler_command_watchdog(message: str) -> None:
    logger.info(f"Processing handler watchdog command")
    try:
        global watchdog
        if watchdog is False:
            watchdog = True
            bot.send_message(
                chat_id=message.chat.id,
                text="Start monitor the node",
                parse_mode='Markdown')
            while True:
                if watchdog is True:
                    text = message.text.split(' ')[1]
                    if check_ip_address(message, text):
                        req = connect(message, text)
                        if not req:
                            logger.error(f"ERROR while connecting")
                            bot.send_message(
                                chat_id=message.chat.id,
                                text="No connection. Check node status",
                                parse_mode='Markdown')
                        else:
                            bot.send_message(
                                chat_id=message.chat.id,
                                text="All ok!",
                                parse_mode='Markdown')
                    time.sleep(5)
                else:
                    break
    except Exception as e:
        logger.error(f"ERROR in watchdog: {e}")


def processing_handler_command_watchdog_stop(message):
    global watchdog
    watchdog = False
    bot.send_message(
        chat_id=message.chat.id,
        text="Stop monitor the node",
        parse_mode='Markdown')


def processing_handler_command_check_node(message: str) -> None:
    logger.info(f"Processing handler text message")
    text = message.text.split(' ')[1]
    if check_ip_address(message, text):
        req = connect(message, text)
        if req.status_code == 200:
            message_text = get_node_info(req)
            bot.send_message(
                chat_id=message.chat.id,
                text=message_text,
                parse_mode='Markdown')


def processing_handler_text_message(message):
    processing_handler_command_help(message)


def get_node_info(req):
    json_data = req.json()
    node = json_data.get('network', {}).get('nodeInfo', {})
    tier = node.get('tier', '')
    node_id = node.get('id', '')
    node_active = node.get('active', '')
    node_id_link = f"[{node_id}](https://explorer.muon.net/nodes/{node_id})"
    uptime_info = json_data.get('node', {}).get('uptime', '')
    networking_port = json_data.get('node', {}).get('networkingPort', '')
    network = json_data.get('managerContract', {}).get('network', '')
    staker = json_data.get('staker', '')
    node_address = json_data.get('address', '')
    perr_id = json_data.get('peerId', '')
    try:
        links_nodes = NODE_ID_URL + f'{node_id}'
        response = requests.get(links_nodes, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        tag_div = soup.find(
            'div', class_='number rounded-circle d-flex justify-content-center align-items-center')
        if tag_div:
            uptime_value = next(
                (tag_h6.text for tag_h6 in tag_div.find_all('h6') if '%' in tag_h6.text),
                'Error parsing id data')
            uptime_value = float(''.join(filter(str.isdigit, uptime_value))) / 100
        else:
            uptime_value = 'Error parsing id data'
    except Exception as e:
        logger.error(f'Error parsing id data: {e}')
        uptime_value = 'Error parsing id data'

    node_address_short = f"{node_address[:6]}...{node_address[-6:]}"
    staker_info_short = f"{staker[:6]}...{staker[-6:]}"
    perr_id_info_short = f"{perr_id[:6]}...{perr_id[-6:]}"

    message_text = (
        f"👤 Node ID: {node_id_link}\n"
        f"📱 Node: `{node_address_short}`\n"
        f"⏰ Uptime: `{uptime_info}`\n"
        f"⏱ Uptime: {uptime_value} %\n"
        f"🟢 Active: {node_active}\n"
        f"📈 Tier : {tier}\n"
        f"⚙️ Network: {network}\n"
        f"💻 Staker: `{staker_info_short}`\n"
        f"🔢 Peer id: `{perr_id_info_short}`\n"
        f"#️⃣ NetworkingPort: `{networking_port}`\n"
    )
    return message_text


def connect(message: str, ip: str) -> None | str:
    logger.info("Try connecting to ip")
    try:
        req = requests.get(f"http://{ip}:8011/status", timeout=20)
        logger.info(f"Take node info")
        return req
    except requests.exceptions.Timeout as e:
        logger.error(f"ERROR Timeout while connecting to ip {e}")
        bot.send_message(
            chat_id=message.chat.id,
            text='Connection is not established. You have entered the wrong IP address. Try again')
    except requests.exceptions.RequestException as e:
        logger.error(f"ERROR getting node info {e}")
        bot.send_message(message.chat.id, f"ERROR {e}")
        return None


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
    total_nodes = total_nodes[0].get_text()
    tag_active_div = soup.find('div', attrs={
        'class': 'col-md-7 col-12 d-flex align-items-end justify-content-lg-start justify-content-md-end ms-lg-4 ps-xl-4'})
    active_nodes = tag_active_div.find_all(
        'h4', class_='sc-d9568944-6 jRQSOr fw-bold mb-0')
    active_nodes = active_nodes[0].get_text()
    number_active = re.findall(r'\d+', active_nodes)
    info = [total_nodes, active_nodes, number_active[0]]
    return info
