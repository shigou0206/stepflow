# stepflow/utils/logger.py
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def log_info(msg: str):
    logging.info(msg)

def log_error(msg: str):
    logging.error(msg)