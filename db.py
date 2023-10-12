import sqlite3 as sql
import logging
from config1 import *
from sentry_sdk.integrations.logging import LoggingIntegration

sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.WARNING
)
logging.basicConfig(
    level=logging.INFO,
    format=LOGGER_FORMAT,
    filename='db.log',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)


def inicialize_db() -> None:
    logger.info('Initializing database...')
    conn = sql.connect('user_ip.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT NOT NULL,
        node_ip TEXT
    )''')
    conn.commit()
    conn.close()


def set_user_id(user_id: str) -> None:
    logger.info("Setting user_id...")
    try:
        conn = sql.connect('user_ip.db')
        c = conn.cursor()
        c.execute('''INSERT INTO users (user_id) VALUES (?)''', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error set user_id: {e}")


def set_user_ip(user_id: str, node_ip: str) -> None:
    logger.info("Setting user_ip...")
    try:
        conn = sql.connect('user_ip.db')
        c = conn.cursor()
        c.execute('''UPDATE users SET node_ip =? WHERE user_id =?''', (node_ip, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error set user_ip: {e}")


def check_user_in_db(user_id: str) -> bool:
    logger.info("Checking user_id in db...")
    try:
        conn = sql.connect('user_ip.db')
        c = conn.cursor()
        c.execute('''SELECT * FROM users WHERE user_id =?''', (user_id,))
        result = c.fetchone()
        conn.commit()
        conn.close()
        if result:
            logger.info(f"User {user_id} found in db.")
            return True
        else:
            logger.info(f"User {user_id} not found in db.")
            return False
    except Exception as e:
        logger.error(f"Error checking user_id in db: {e}")


def get_user_ip(user_id: str) -> str | None:
    try:
        logger.info("Getting user_ip...")
        conn = sql.connect('user_ip.db')
        c = conn.cursor()
        c.execute('''SELECT * FROM users WHERE user_id =?''', (user_id,))
        result = c.fetchone()
        conn.commit()
        conn.close()
        if result:
            logger.info(f"User {user_id} found in db -> return ip.")
            return result[1]
        else:
            logger.info(f"User {user_id} not found in db -> return None.")
            return None
    except Exception as e:
        logger.error(f"Error getting user_ip: {e}")
        return None
