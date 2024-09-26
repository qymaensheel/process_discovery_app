import os
import logging


def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    
    log_path = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'bpmn.log')
    file_handler = logging.FileHandler(log_path)
    logger.addHandler(file_handler)

    return logger
