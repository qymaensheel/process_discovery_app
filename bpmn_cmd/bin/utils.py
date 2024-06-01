import logging

def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    
    log_path = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'bpmn.log')
    file_handler = logging.FileHandler(log_path)
    logger.addHandler(logging.FileHandler('/var/log/splunk/bpmn.log'))

    return logger