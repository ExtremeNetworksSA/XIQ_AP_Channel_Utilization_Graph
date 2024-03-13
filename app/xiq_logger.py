#!/usr/bin/env python3
import logging
import os
import sys
import inspect
from logging.handlers import RotatingFileHandler
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


# check for logs directory and create if missing
os.makedirs('{}/logs'.format(current_dir), exist_ok=True) 
log_dir = '{}/logs'.format(current_dir)

class CustomFormatter(logging.Formatter):
	# Git Shell Coloring - https://gist.github.com/vratiu/9780109
	GREY = "\x1b[38;20m"
	RED   = "\033[1;31m"  
	BLUE  = "\033[1;34m"
	GREEN = "\033[0;32m"
	YELLOW = "\033[0;33m"
	BOLD_RED = "\x1b[31;1m"
	RESET = "\033[0;0m"
	format = '%(levelname)s: %(message)s'
	
	FORMATS = {
	        logging.DEBUG: GREEN + format + RESET,
	        logging.INFO: BLUE + format + RESET,
	        logging.WARNING: YELLOW + format + RESET,
	        logging.ERROR: RED + format + RESET,
	        logging.CRITICAL: BOLD_RED + format + RESET
	    }
	
	def format(self, record):
		log_fmt = self.FORMATS.get(record.levelno)
		formatter = logging.Formatter(log_fmt)
		return formatter.format(record)
	
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # this is needed to get all levels, and therefore filter on each handler


PATH = os.path.dirname(os.path.abspath(__file__))
log_formatter = logging.Formatter('%(asctime)s: %(name)s - %(levelname)s - %(message)s')

logFile = '{}/channel_utilization.log'.format(log_dir)

fileHandler = RotatingFileHandler(logFile, mode='a', maxBytes=50*1024*1024, # TODO max size is ?
                                 backupCount=5, encoding=None, delay=0)

fileHandler.setFormatter(log_formatter)
fileHandler.setLevel(logging.DEBUG)
logger.addHandler(fileHandler)


# create console handler for logger.
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setLevel(level=logging.INFO)
consoleHandler.setFormatter(CustomFormatter())
logger.addHandler(consoleHandler)
