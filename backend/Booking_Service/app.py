from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
from flask_cors import CORS
import logging
from functools import wraps

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настраиваем CORS для всех доменов
CORS(app, resources={r"/*": {"origins": "*"}})

# URL сервисов
SERVICES = {
    'master': 'http://localhost:5001',
    'confirmation': 'http://localhost:5003',
    'user': 'http://localhost:5000',
    'history': 'http://localhost:5004',
    'sync': 'ws://localhost:5005'
}

# Декоратор для обработки ошибок
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.exceptions.ConnectionError:
            logger.error("Connection error with external service")
            return jsonify({'error': 'Нет соединения с одним из сервисов'}), 500
        except Exception as e:
            logger.error(f"Internal server error: {str(e)}")
            return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500
    return decorated_function

@app.route('/')
def index():
    return jsonify({
        'service': 'Booking Service', 
        'status': 'running',
        'version': '2.0',
        'features': [
            'Бронирование слотов',
            'Альтернативные времена',
            'Проверка доступности',
            'Синхронизация в реальном времени'
        ]
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервиса и зависимостей"""
    dependencies = {}
    
    try:
        # Проверяем Master Service
        master_res = requests.get(f"{SERVICES['master']}/", timeout=3)
        dependencies['master_service'] = 'healthy' if master_res.status_code == 200 else 'unhealthy'
    except:
        dependencies['master_service'] = 'unreachable'
    
    try:
        # Проверяем Confirmation Service
        conf_res = requests.get(f"{SERVICES['confirmation']}/", timeout=3)
        dependencies['confirmation_service'] = 'healthy' if conf_res.status_code == 200 else 'unhealthy'
    except:
        dependencies['confirmation_service'] = 'unreachable'
    
    all_healthy = all(status == 'healthy' for status in dependencies.values())
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'timestamp': datetime.utcnow().isoformat(),
        'dependencies': dependencies
    })

@app.route('/book', methods=['POST', 'OPTIONS'])
@handle_errors
def book():
    """Основной метод бронирования"""
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.json
    if not data:
        return jsonify({'error': 'Нет данных'}), 400
    
    user_id = data.get('user_id')
    master_id = data.get('master_id')
    date = data.get('date')
    time = data.get('time')
    
    # Валидация входных данных
    if not all([user_id, master_id, date, time]):
        return jsonify({'error': 'Не все обязательные параметры указаны'}), 400
    
    # Проверяем валидность даты
    try:
        datetime.strptime(date, '%Y-%m-%d')
        datetime.strptime(time, '%H:%M')
    except ValueError:
        return jsonify({'error': 'Неверный формат даты или времени'}), 400
    
    logger.info(f"Бронирование: user={user_id}, master={master_id}, date={date}, time={time}")
    
    # Проверяем доступность мастера
    master_info = get_master_info(master_id)
    if not master_info:
        return jsonify({'error': 'Мастер не найден'}), 404
    
    # Получаем расписание мастера
    schedule = get_master_schedule(master_id, date)
    if not schedule:
        return jsonify({'error': 'Ошибка получения расписания'}), 500
    
    available_times = schedule.get('available_times', [])
    
    # Проверяем доступно ли выбранное время
    if time in available_times:
        return process_booking(user_id, master_id, date, time, master_info)
    else:
        # Ищем альтернативные варианты
        return handle_alternative_slots(master_id, date, time, available_times, master_info)

def get_master_info(master_id):
    """Получение информации о мастере"""
    try:
        response = requests.get(f"{SERVICES['master']}/masters", timeout=5)
        if response.status_code == 200:
            masters = response.json()
            master_name = masters.get(str(master_id)) or f'Мастер #{master_id}'
            return {'id': master_id, 'name': master_name}
    except Exception as e:
        logger.error(f"Error getting master info: {e}")
    return None

def get_master_schedule(master_id, date):
    """Получение расписания мастера"""
    try:
        response = requests.get(f"{SERVICES['master']}/schedule/{master_id}/{date}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error getting master schedule: {e}")
    return None

def process_booking(user_id, master_id, date, time, master_info):
    """Обработка успешного бронирования"""
    # Бронируем слот
    booking_result = book_slot(master_id, date, time, user_id)
    
    if booking_result.get('success'):
        # Подтверждаем бронирование
        confirmation = confirm_booking(user_id, master_id, date, time, master_info['name'])
        
        if confirmation.get('success'):
            # Сохраняем в историю
            save_to_history(user_id, master_id, master_info['name'], date, time)
            
            # Отправляем уведомление в реальном времени
            notify_booking_created(user_id, master_id, date, time)
            
            logger.info(f"Бронирование успешно: booking_id={confirmation.get('booking_id')}")
            
            return jsonify({
                'success': True,
                'message': 'Запись успешно создана',
                'booking_id': confirmation.get('booking_id'),
                'booking': confirmation.get('booking'),
                'master_name': master_info['name']
            })
        else:
            # Отменяем бронирование если подтверждение не удалось
            cancel_booking(master_id, date, time)
            return jsonify({'error': 'Ошибка подтверждения записи'}), 500
    else:
        return jsonify({'error': 'Не удалось забронировать слот'}), 500

def book_slot(master_id, date, time, user_id):
    """Бронирование слота у мастера"""
    try:
        response = requests.post(
            f"{SERVICES['master']}/book_slot/{master_id}/{date}/{time}",
            json={'client_id': user_id},
            timeout=5
        )
        return response.json() if response.status_code == 200 else {'success': False}
    except:
        return {'success': False}

def confirm_booking(user_id, master_id, date, time, master_name):
    """Подтверждение бронирования"""
    try:
        response = requests.post(
            f"{SERVICES['confirmation']}/confirm",
            json={
                'user_id': user_id,
                'master_id': master_id,
                'date': date,
                'time': time,
                'master_name': master_name
            },
            timeout=5
        )
        return response.json() if response.status_code == 200 else {'success': False}
    except:
        return {'success': False}

def save_to_history(user_id, master_id, master_name, date, time):
    """Сохранение в историю сеансов"""
    try:
        requests.post(
            f"{SERVICES['history']}/add_session",
            json={
                'user_id': user_id,
                'master_id': master_id,
                'master_name': master_name,
                'date': date,
                'time': time,
                'status': 'pending'
            },
            timeout=3
        )
    except:
        logger.warning("Не удалось сохранить в историю")

def notify_booking_created(user_id, master_id, date, time):
    """Уведомление о создании бронирования"""
    try:
        # В реальном приложении здесь будет WebSocket
        logger.info(f"Booking created notification: user={user_id}, master={master_id}")
    except:
        pass

def cancel_booking(master_id, date, time):
    """Отмена бронирования"""
    try:
        requests.delete(
            f"{SERVICES['master']}/free_slot/{master_id}/{date}/{time}",
            timeout=3
        )
    except:
        logger.warning("Не удалось отменить бронирование")

def handle_alternative_slots(master_id, date, time, available_times, master_info):
    """Обработка альтернативных вариантов при занятом слоте"""
    try:
        target_dt = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        
        # Фильтруем доступные слоты
        available_slots = []
        for slot_time in available_times:
            slot_dt = datetime.strptime(f'{date} {slot_time}', '%Y-%m-%d %H:%M')
            if slot_dt > target_dt:  # Только слоты после запрошенного времени
                available_slots.append({
                    'time': slot_time,
                    'datetime': slot_dt,
                    'difference': (slot_dt - target_dt).total_seconds() / 60  # разница в минутах
                })
        
        # Сортируем по близости к запрошенному времени
        available_slots.sort(key=lambda x: x['difference'])
        
        # Берем 3 ближайших варианта
        alternatives = [slot['time'] for slot in available_slots[:3]]
        
        if alternatives:
            return jsonify({
                'success': False,
                'error': 'Выбранное время занято',
                'alternative_times': alternatives,
                'message': f'Доступные альтернативные времена: {", ".join(alternatives)}',
                'master_name': master_info['name']
            }), 409
        else:
            # Проверяем доступность на другие даты
            next_dates = get_next_available_dates(master_id, date, time)
            
            if next_dates:
                return jsonify({
                    'success': False,
                    'error': 'Нет доступных слотов в этот день',
                    'alternative_dates': next_dates,
                    'message': 'Попробуйте другие даты',
                    'master_name': master_info['name']
                }), 409
            else:
                return jsonify({
                    'success': False,
                    'error': 'Нет доступных слотов',
                    'message': 'Пожалуйста, выберите другую дату или мастера',
                    'master_name': master_info['name']
                }), 409
                
    except Exception as e:
        logger.error(f"Error handling alternatives: {e}")
        return jsonify({'error': 'Ошибка поиска альтернативных вариантов'}), 500

def get_next_available_dates(master_id, original_date, original_time):
    """Поиск доступных дат в будущем"""
    try:
        original_dt = datetime.strptime(original_date, '%Y-%m-%d')
        alternative_dates = []
        
        # Проверяем следующие 7 дней
        for i in range(1, 8):
            check_date = (original_dt + timedelta(days=i)).strftime('%Y-%m-%d')
            
            schedule = get_master_schedule(master_id, check_date)
            if schedule and original_time in schedule.get('available_times', []):
                alternative_dates.append({
                    'date': check_date,
                    'day_of_week': (original_dt.weekday() + i) % 7,
                    'formatted': format_date_for_display(check_date)
                })
            
            if len(alternative_dates) >= 3:
                break
        
        return alternative_dates
    except:
        return []

def format_date_for_display(date_string):
    """Форматирование даты для отображения"""
    try:
        date = datetime.strptime(date_string, '%Y-%m-%d')
        days = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
        months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 
                  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
        
        return f"{date.day} {months[date.month-1]} ({days[date.weekday()]})"
    except:
        return date_string

@app.route('/check_availability/<int:master_id>/<date>/<time>', methods=['GET'])
@handle_errors
def check_availability(master_id, date, time):
    """Проверка доступности конкретного времени"""
    try:
        schedule = get_master_schedule(master_id, date)
        if not schedule:
            return jsonify({'error': 'Ошибка получения расписания'}), 500
        
        available = time in schedule.get('available_times', [])
        
        return jsonify({
            'available': available,
            'master_id': master_id,
            'date': date,
            'time': time,
            'master_name': schedule.get('master_name', f'Мастер #{master_id}')
        })
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return jsonify({'error': 'Ошибка проверки доступности'}), 500

@app.route('/quick_book', methods=['POST'])
@handle_errors
def quick_book():
    """Быстрое бронирование по рекомендации"""
    data = request.json
    
    user_id = data.get('user_id')
    master_id = data.get('master_id')
    date = data.get('date')
    time = data.get('time')
    
    if not all([user_id, master_id, date, time]):
        return jsonify({'error': 'Не все параметры указаны'}), 400
    
    # Проверяем доступность
    schedule = get_master_schedule(master_id, date)
    if not schedule:
        return jsonify({'error': 'Ошибка проверки расписания'}), 500
    
    if time not in schedule.get('available_times', []):
        return jsonify({'error': 'Время уже занято'}), 409
    
    # Выполняем бронирование
    master_info = get_master_info(master_id)
    if not master_info:
        return jsonify({'error': 'Мастер не найден'}), 404
    
    return process_booking(user_id, master_id, date, time, master_info)

@app.route('/get_master_availability/<int:master_id>', methods=['GET'])
@handle_errors
def get_master_availability(master_id):
    """Получение доступности мастера на ближайшие дни"""
    try:
        today = datetime.now().date()
        availability = {}
        
        # Проверяем следующие 5 дней
        for i in range(5):
            check_date = today + timedelta(days=i)
            date_str = check_date.strftime('%Y-%m-%d')
            
            schedule = get_master_schedule(master_id, date_str)
            if schedule:
                availability[date_str] = {
                    'available': len(schedule.get('available_times', [])) > 0,
                    'available_slots': schedule.get('available_times', []),
                    'day_of_week': check_date.weekday(),
                    'formatted_date': format_date_for_display(date_str)
                }
        
        master_info = get_master_info(master_id)
        
        return jsonify({
            'success': True,
            'master_id': master_id,
            'master_name': master_info['name'] if master_info else f'Мастер #{master_id}',
            'availability': availability,
            'next_available': get_next_available_date(availability)
        })
    except Exception as e:
        logger.error(f"Error getting master availability: {e}")
        return jsonify({'error': 'Ошибка получения доступности'}), 500

def get_next_available_date(availability):
    """Получение следующей доступной даты"""
    for date, info in sorted(availability.items()):
        if info['available']:
            return date
    return None

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск Booking Service v2.0...")
    print(f"🌐 Адрес: http://localhost:5002")
    print("📋 Функции:")
    print("   • Основное бронирование")
    print("   • Альтернативные времена")
    print("   • Проверка доступности")
    print("   • Быстрое бронирование")
    print("   • Уведомления в реальном времени")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5002, debug=True)