"""The AWS ssh script"""

import logging.config

__author__ = 'Aru Sahni'
__version__ = '0.0.2'
__licence__ = 'MIT'

APP_NAME = 'aws-ssh'

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        }
    },
    'handlers': {
        'stream': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'NOTSET',
        },
    },
    'loggers': {
        '': {
            'handlers': ['stream'],
            'level': 'NOTSET',
            'propagate': True,
        },
        'aws_ssh': {
            'handlers': ['stream'],
            'level': 'WARN',
            'propagate': False,
        },
        'botocore': {
            'handlers': ['stream'],
            'level': 'ERROR',
            'propagate': False,
        }
    },
})
