from flask import Flask, request, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'bookings.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app, resources={r"/*": {"origins": "*"}})

USER_URL = 'http://localhost:5000'
MASTER_URL = 'http://localhost:5001'
HISTORY_URL = 'http://localhost:5004'

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    user_name = db.Column(db.String(100))
    master_id = db.Column(db.Integer, nullable=False)
    master_name = db.Column(db.String(100))
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_database():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Таблицы созданы/проверены")
        except Exception as e:
            print(f"❌ Ошибка при инициализации базы данных: {e}")
            db.session.rollback()
            raise e

with app.app_context():
    init_database()

@app.route('/')
def index():
    return jsonify({'service': 'Confirmation Service', 'status': 'running'})

@app.route('/confirm', methods=['POST', 'OPTIONS'])
def confirm():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        user_id = data.get('user_id')
        master_id = data.get('master_id')
        date = data.get('date')
        time = data.get('time')
        
        if not all([user_id, master_id, date, time]):
            return jsonify({'error': 'Не все параметры указаны'}), 400

        # Получаем информацию о пользователе
        user_res = requests.get(f'{USER_URL}/user/{user_id}', timeout=5)
        if user_res.status_code != 200:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        user = user_res.json()
        user_name = user.get('name', f'Пользователь #{user_id}')

        # Получаем информацию о мастере
        try:
            master_res = requests.get(f'{MASTER_URL}/masters', timeout=5)
            if master_res.status_code == 200:
                masters = master_res.json()
                master_name = masters.get(str(master_id), f'Мастер #{master_id}')
            else:
                master_name = f'Мастер #{master_id}'
        except:
            master_name = f'Мастер #{master_id}'

        # Проверяем нет ли уже такой записи у этого пользователя
        existing_booking = Booking.query.filter_by(
            user_id=user_id, 
            master_id=master_id, 
            date=date, 
            time=time
        ).first()
        
        if existing_booking:
            return jsonify({'error': 'У вас уже есть запись на это время'}), 400

        # Создаем запись
        booking = Booking(
            user_id=user_id,
            user_name=user_name,
            master_id=master_id,
            master_name=master_name,
            date=date,
            time=time
        )
        
        db.session.add(booking)
        db.session.commit()

        # Добавляем сеанс в историю
        try:
            history_data = {
                'user_id': user_id,
                'user_name': user_name,
                'master_id': master_id,
                'master_name': master_name,
                'date': date,
                'time': time
            }
            requests.post(f'{HISTORY_URL}/add_session', json=history_data, timeout=5)
        except:
            print("⚠ Не удалось добавить сеанс в историю")

        return jsonify({
            'success': True,
            'message': 'Запись подтверждена',
            'booking_id': booking.id,
            'booking': {
                'id': booking.id,
                'user_id': booking.user_id,
                'user': booking.user_name,
                'master_id': booking.master_id,
                'master': booking.master_name,
                'date': booking.date,
                'time': booking.time,
                'created_at': booking.created_at.isoformat() if booking.created_at else None
            }
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Нет соединения с сервисом пользователей или мастеров'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500

@app.route('/active_bookings', methods=['GET', 'OPTIONS'])
def get_active_bookings():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        bookings = Booking.query.order_by(Booking.date.desc(), Booking.time.desc()).all()
        result = []
        for b in bookings:
            result.append({
                'id': b.id,
                'user_id': b.user_id,
                'user': b.user_name,
                'master_id': b.master_id,
                'master': b.master_name,
                'date': b.date,
                'time': b.time,
                'created_at': b.created_at.isoformat() if b.created_at else None
            })
        return jsonify({'success': True, 'active_bookings': result})
    except Exception as e:
        return jsonify({'error': f'Ошибка получения записей: {str(e)}'}), 500

@app.route('/user_bookings/<int:user_id>', methods=['GET', 'OPTIONS'])
def get_user_bookings(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        bookings = Booking.query.filter_by(user_id=user_id).order_by(
            Booking.date.desc(), 
            Booking.time.desc()
        ).all()
        
        result = []
        for b in bookings:
            result.append({
                'id': b.id,
                'user_id': b.user_id,
                'user': b.user_name,
                'master_id': b.master_id,
                'master': b.master_name,
                'date': b.date,
                'time': b.time,
                'created_at': b.created_at.isoformat() if b.created_at else None
            })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'user_bookings': result,
            'total': len(result)
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка получения записей пользователя: {str(e)}'}), 500

@app.route('/cancel_booking/<int:booking_id>', methods=['DELETE', 'OPTIONS'])
def cancel_booking(booking_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Запись не найдена'}), 404
        
        booking_data = {
            'master_id': booking.master_id,
            'date': booking.date,
            'time': booking.time
        }
        
        db.session.delete(booking)
        db.session.commit()
        
        # Уведомляем Master Service об отмене
        try:
            requests.delete(
                f'http://localhost:5001/free_slot/{booking_data["master_id"]}/{booking_data["date"]}/{booking_data["time"]}',
                timeout=5
            )
        except:
            print("⚠ Не удалось уведомить Master Service об отмене")
        
        return jsonify({
            'success': True,
            'message': 'Запись отменена',
            'cancelled_booking': booking_data
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка отмены записи: {str(e)}'}), 500

@app.route('/master_bookings/<int:master_id>', methods=['GET', 'OPTIONS'])
def get_master_bookings(master_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        bookings = Booking.query.filter_by(master_id=master_id).order_by(
            Booking.date, 
            Booking.time
        ).all()
        
        result = []
        for b in bookings:
            result.append({
                'id': b.id,
                'user_id': b.user_id,
                'user': b.user_name,
                'client_id': b.user_id,  # Для совместимости с фронтендом
                'master_id': b.master_id,
                'master': b.master_name,
                'date': b.date,
                'time': b.time
            })
        
        return jsonify({
            'success': True,
            'master_id': master_id,
            'master_bookings': result,
            'total': len(result)
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка получения записей мастера: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск Confirmation Service...")
    print(f"📊 База данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🌐 Адрес: http://localhost:5003")
    print("=" * 50)
    
    try:
        app.run(host='0.0.0.0', port=5003, debug=True)
    except Exception as e:
        print(f"❌ Ошибка запуска сервиса: {e}")