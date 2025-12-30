# Конфигурация всех сервисов

SERVICES = {
    'user': {
        'url': 'http://localhost:5000',
        'name': 'User Service'
    },
    'master': {
        'url': 'http://localhost:5001',
        'name': 'Master Service'
    },
    'booking': {
        'url': 'http://localhost:5002',
        'name': 'Booking Service'
    },
    'confirmation': {
        'url': 'http://localhost:5003',
        'name': 'Confirmation Service'
    },
    'history': {
        'url': 'http://localhost:5004',
        'name': 'History Service'
    },
    'sync': {
        'url': 'ws://localhost:5005',
        'name': 'Sync Service'
    }
}

# Настройки WebSocket
SOCKETIO_CONFIG = {
    'cors_allowed_origins': "*",
    'async_mode': 'threading',
    'ping_timeout': 60,
    'ping_interval': 25,
    'logger': True,
    'engineio_logger': False
}

# Общие настройки
COMMON_CONFIG = {
    'debug': True,
    'host': '0.0.0.0',
    'use_reloader': False
}