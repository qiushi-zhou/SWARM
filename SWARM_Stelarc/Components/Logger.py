
import logging
from logging import FileHandler
import logging.handlers as handlers
import os

# Default levels
# CRITICAL = 50
# ERROR = 40
# WARNING = 30
# INFO = 20
# DEBUG = 10
# NOTSET = 0

def addLoggingLevel(logging, levelName, levelNum, methodName=None):
  """
  Comprehensively adds a new logging level to the `logging` module and the
  currently configured logging class.

  `levelName` becomes an attribute of the `logging` module with the value
  `levelNum`. `methodName` becomes a convenience method for both `logging`
  itself and the class returned by `logging.getLoggerClass()` (usually just
  `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
  used.

  To avoid accidental clobberings of existing attributes, this method will
  raise an `AttributeError` if the level name is already an attribute of the
  `logging` module or if the method name is already present

  Example
  -------
  # >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
  # >>> logging.getLogger(__name__).setLevel("TRACE")
  # >>> logging.getLogger(__name__).trace('that worked')
  # >>> logging.trace('so did this')
  # >>> logging.TRACE
  5

  """
  if not methodName:
    methodName = levelName.lower()

  if hasattr(logging, levelName):
    raise AttributeError('{} already defined in logging module'.format(levelName))
  if hasattr(logging, methodName):
    raise AttributeError('{} already defined in logging module'.format(methodName))
  if hasattr(logging.getLoggerClass(), methodName):
    raise AttributeError('{} already defined in logger class'.format(methodName))

  # This method was inspired by the answers to Stack Overflow post
  # http://stackoverflow.com/q/2183233/2988730, especially
  # http://stackoverflow.com/a/13638084/2988730
  def logForLevel(self, message, *args, **kwargs):
    if self.isEnabledFor(levelNum):
      self._log(levelNum, message, args, **kwargs)

  def logToRoot(message, *args, **kwargs):
    logging.log(levelNum, message, *args, **kwargs)

  logging.addLevelName(levelNum, levelName)
  setattr(logging, levelName, levelNum)
  setattr(logging.getLoggerClass(), methodName, logForLevel)
  setattr(logging, methodName, logToRoot)


addLoggingLevel(logging, 'ARDUINO', logging.CRITICAL + 1)
addLoggingLevel(logging, 'ONLINE', logging.CRITICAL + 2)
addLoggingLevel(logging, 'APP', logging.CRITICAL + 3)

class CustomFormatter(logging.Formatter):
    grey = "\x1b[0;37m"
    cyan = "\x1b[0;36m"
    yellow = "\x1b[33;20m"
    green = "\x1b[0;32m"
    blue = "\x1b[0;34m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    # format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format = "WHAT"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: cyan + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        (logging.CRITICAL + 1): yellow + format + reset,
        (logging.CRITICAL + 2): green + format + reset,
        (logging.CRITICAL + 3): blue + format + reset
    }
    def __init__(self, p_format):
      super(CustomFormatter, self).__init__(p_format)
      CustomFormatter.FORMATS = {
          logging.DEBUG: CustomFormatter.grey + p_format + CustomFormatter.reset,
          logging.INFO: CustomFormatter.cyan + p_format + CustomFormatter.reset,
          logging.WARNING: CustomFormatter.yellow + p_format + CustomFormatter.reset,
          logging.ERROR: CustomFormatter.red + p_format + CustomFormatter.reset,
          logging.CRITICAL: CustomFormatter.bold_red + p_format + CustomFormatter.reset,
          (logging.CRITICAL + 1): CustomFormatter.yellow + p_format + CustomFormatter.reset,
          (logging.CRITICAL + 2): CustomFormatter.green + p_format + CustomFormatter.reset,
          (logging.CRITICAL + 3): CustomFormatter.blue + p_format + CustomFormatter.reset
      }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
format = '%(asctime)s %(levelname).1s [%(filename).5s:%(lineno)s] %(message)s'
streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.DEBUG)
streamHandler.setFormatter(CustomFormatter(format))

logFileHandler = handlers.TimedRotatingFileHandler('swarm_app.log', when='H', interval=24)
logFileHandler.setLevel(logging.DEBUG)
logFileHandler.setFormatter(logging.Formatter(format))

# logging.basicConfig(level=logging.DEBUG,
#                 format='%(asctime)s: %(levelname).1s [%(filename).5s:%(lineno)s] %(message)s',
#                 datefmt='%d-%m-%Y %I:%M:%S',
#                 handlers=[logFileHandler, ch])

app_logger = logging.getLogger("SwarmAPP")
app_logger.setLevel(logging.DEBUG)
app_logger.addHandler(streamHandler)
app_logger.addHandler(logFileHandler)