from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import threading
import time
from datetime import datetime
from collections import defaultdict
import logging

app = Flask(__name__)
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище для клиентов и обновлений
connected_clients = defaultdict(list)  # user_id -> список соединений
updates_queue = []

class SimpleWebSocket:
    """Простая реализация WebSocket на основе long-polling"""
    
    def __init__(self):
        self.subscriptions = defaultdict(list)
        self.messages = defaultdict(list)
    
    def subscribe(self, user_id, callback_url):
        """Подписка пользователя на обновления"""
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = []
        
        if callback_url not in self.subscriptions[user_id]:
            self.subscriptions[user_id].append(callback_url)
            logger.info(f"User {user_id} subscribed from {callback_url}")
    
    def unsubscribe(self, user_id, callback_url):
        """Отписка пользователя"""
        if user_id in self.subscriptions and callback_url in self.subscriptions[user_id]:
            self.subscriptions[user_id].remove(callback_url)
            logger.info(f"User {user_id} unsubscribed from {callback_url}")
    
    def send_to_user(self, user_id, message):
        """Отправка сообщения конкретному пользователю"""
        if user_id in self.subscriptions:
            # В реальном приложении здесь бы отправлялись HTTP запросы
            # или использовались бы реальные WebSocket
            self.messages[user_id].append({
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"Message queued for user {user_id}: {message}")
    
    def broadcast(self, message):
        """Широковещательная рассылка"""
        for user_id in self.subscriptions:
            self.send_to_user(user_id, message)
        logger.info(f"Broadcast message: {message}")
    
    def get_messages(self, user_id, clear=True):
        """Получение сообщений для пользователя"""
        if user_id in self.messages and self.messages[user_id]:
            messages = self.messages[user_id].copy()
            if clear:
                self.messages[user_id].clear()
            return messages
        return []

# Создаем экземпляр нашего простого WebSocket
websocket = SimpleWebSocket()

@app.route('/')
def index():
    return jsonify({
        'service': 'Sync Service',
        'status': 'running',
        'version': '1.0',
        'connected_users': len(websocket.subscriptions)
    })

@app.route('/subscribe', methods=['POST'])
def subscribe():
    """Подписка на обновления"""
    data = request.json
    user_id = data.get('user_id')
    callback_url = data.get('callback_url', '')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    websocket.subscribe(user_id, callback_url)
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'message': 'Subscribed successfully',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Отписка от обновлений"""
    data = request.json
    user_id = data.get('user_id')
    callback_url = data.get('callback_url', '')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    websocket.unsubscribe(user_id, callback_url)
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'message': 'Unsubscribed successfully'
    })

@app.route('/send', methods=['POST'])
def send_message():
    """Отправка сообщения пользователю"""
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    message_type = data.get('type', 'notification')
    
    if not user_id or not message:
        return jsonify({'error': 'user_id and message required'}), 400
    
    websocket.send_to_user(user_id, {
        'type': message_type,
        'message': message,
        'data': data.get('data', {}),
        'timestamp': datetime.now().isoformat()
    })
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'message': 'Message sent'
    })

@app.route('/broadcast', methods=['POST'])
def broadcast():
    """Широковещательная рассылка"""
    data = request.json
    message = data.get('message')
    message_type = data.get('type', 'broadcast')
    
    if not message:
        return jsonify({'error': 'message required'}), 400
    
    websocket.broadcast({
        'type': message_type,
        'message': message,
        'data': data.get('data', {}),
        'timestamp': datetime.now().isoformat()
    })
    
    return jsonify({
        'success': True,
        'recipients': len(websocket.subscriptions),
        'message': 'Broadcast sent'
    })

@app.route('/poll/<int:user_id>', methods=['GET'])
def poll_messages(user_id):
    """Long-polling для получения сообщений"""
    timeout = int(request.args.get('timeout', 30))
    start_time = time.time()
    
    # Ждем новые сообщения с таймаутом
    while time.time() - start_time < timeout:
        messages = websocket.get_messages(user_id, clear=False)
        if messages:
            # Очищаем только после успешной отправки
            websocket.get_messages(user_id, clear=True)
            return jsonify({
                'success': True,
                'user_id': user_id,
                'messages': messages,
                'timestamp': datetime.now().isoformat()
            })
        time.sleep(1)  # Проверяем каждую секунду
    
    # Таймаут - возвращаем пустой список
    return jsonify({
        'success': True,
        'user_id': user_id,
        'messages': [],
        'timeout': True,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/status/<int:user_id>', methods=['GET'])
def get_user_status(user_id):
    """Получение статуса пользователя"""
    is_subscribed = user_id in websocket.subscriptions and len(websocket.subscriptions[user_id]) > 0
    pending_messages = len(websocket.get_messages(user_id, clear=False))
    
    return jsonify({
        'user_id': user_id,
        'subscribed': is_subscribed,
        'pending_messages': pending_messages,
        'subscription_count': len(websocket.subscriptions.get(user_id, [])),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/booking_created', methods=['POST'])
def booking_created():
    """Событие создания бронирования"""
    data = request.json
    
    user_id = data.get('user_id')
    master_id = data.get('master_id')
    date = data.get('date')
    time = data.get('time')
    booking_id = data.get('booking_id')
    
    if not all([user_id, master_id, date, time]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Отправляем уведомление пользователю
    websocket.send_to_user(user_id, {
        'type': 'booking_created',
        'message': f'Запись создана на {date} в {time}',
        'data': {
            'booking_id': booking_id,
            'master_id': master_id,
            'date': date,
            'time': time
        },
        'timestamp': datetime.now().isoformat()
    })
    
    # Широковещательное обновление для всех подписчиков (админы, мастера)
    websocket.broadcast({
        'type': 'booking_update',
        'message': f'Новая запись создана',
        'data': {
            'user_id': user_id,
            'master_id': master_id,
            'date': date,
            'time': time,
            'action': 'created'
        },
        'timestamp': datetime.now().isoformat()
    })
    
    logger.info(f"Booking created: user={user_id}, master={master_id}, {date} {time}")
    
    return jsonify({
        'success': True,
        'message': 'Booking notification sent'
    })

@app.route('/booking_updated', methods=['POST'])
def booking_updated():
    """Событие обновления бронирования"""
    data = request.json
    
    booking_id = data.get('booking_id')
    user_id = data.get('user_id')
    action = data.get('action')  # cancelled, confirmed, rescheduled
    
    if not booking_id or not user_id:
        return jsonify({'error': 'booking_id and user_id required'}), 400
    
    message_map = {
        'cancelled': 'Запись отменена',
        'confirmed': 'Запись подтверждена',
        'rescheduled': 'Запись перенесена'
    }
    
    message = message_map.get(action, 'Запись обновлена')
    
    websocket.send_to_user(user_id, {
        'type': 'booking_updated',
        'message': message,
        'data': data,
        'timestamp': datetime.now().isoformat()
    })
    
    logger.info(f"Booking updated: {booking_id}, action={action}")
    
    return jsonify({
        'success': True,
        'message': 'Booking update notification sent'
    })

@app.route('/session_updated', methods=['POST'])
def session_updated():
    """Событие обновления сеанса"""
    data = request.json
    
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    status = data.get('status')  # completed, cancelled
    
    if not all([session_id, user_id, status]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    message = f'Сеанс {status}'
    
    websocket.send_to_user(user_id, {
        'type': 'session_updated',
        'message': message,
        'data': data,
        'timestamp': datetime.now().isoformat()
    })
    
    logger.info(f"Session updated: {session_id}, status={status}")
    
    return jsonify({
        'success': True,
        'message': 'Session update notification sent'
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Получение статистики сервиса"""
    total_users = len(websocket.subscriptions)
    total_subscriptions = sum(len(subs) for subs in websocket.subscriptions.values())
    total_messages = sum(len(msgs) for msgs in websocket.messages.values())
    
    return jsonify({
        'service': 'Sync Service',
        'status': 'running',
        'total_subscribed_users': total_users,
        'total_subscriptions': total_subscriptions,
        'pending_messages': total_messages,
        'timestamp': datetime.now().isoformat(),
        'uptime': get_uptime()
    })

# Храним время запуска для расчета uptime
start_time = datetime.now()

def get_uptime():
    """Получение времени работы сервиса"""
    delta = datetime.now() - start_time
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

if __name__ == '__main__':
    print("=" * 60)
    print(" Запуск Sync Service (HTTP Long-Polling)...")

    app.run(host='0.0.0.0', port=5005, debug=True, threaded=True)