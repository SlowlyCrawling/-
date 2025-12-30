from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'history.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app, resources={r"/*": {"origins": "*"}})

class SessionHistory(db.Model):
    __tablename__ = 'session_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(100))
    master_id = db.Column(db.Integer, nullable=False)
    master_name = db.Column(db.String(100))
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    session_date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VisitHistory(db.Model):
    __tablename__ = 'visit_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    master_id = db.Column(db.Integer, nullable=False)
    master_name = db.Column(db.String(100))
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    day_of_week = db.Column(db.Integer)
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_database():
    with app.app_context():
        try:
            db.create_all()
            print("✅ История сеансов: таблицы созданы")
        except Exception as e:
            print(f"❌ Ошибка при инициализации истории: {e}")
            db.session.rollback()
            raise e

with app.app_context():
    init_database()

@app.route('/')
def index():
    return jsonify({'service': 'History Service', 'status': 'running'})

@app.route('/get_recommendation/<int:user_id>', methods=['GET'])
def get_recommendation(user_id):
    try:
        # Ищем последнее успешное посещение
        last_visit = VisitHistory.query.filter_by(
            user_id=user_id,
            status='completed'
        ).order_by(VisitHistory.date.desc()).first()
        
        if not last_visit:
            # Если нет в VisitHistory, ищем в SessionHistory
            last_session = SessionHistory.query.filter_by(
                user_id=user_id,
                status='completed'
            ).order_by(SessionHistory.date.desc()).first()
            
            if not last_session:
                return jsonify({'success': False, 'has_recommendation': False})
            
            # Создаем запись посещения на основе сеанса
            visit_date = datetime.strptime(last_session.date, '%Y-%m-%d').date()
            last_visit = VisitHistory(
                user_id=user_id,
                master_id=last_session.master_id,
                master_name=last_session.master_name,
                date=last_session.date,
                time=last_session.time,
                day_of_week=visit_date.weekday(),
                status='completed'
            )
            db.session.add(last_visit)
            db.session.commit()
        
        today = datetime.now().date()
        
        # Предлагаем на ЗАВТРА в то же время
        tomorrow = today + timedelta(days=1)
        
        # Проверяем доступность мастера на завтра
        try:
            schedule_res = requests.get(
                f'http://localhost:5001/schedule/{last_visit.master_id}/{tomorrow}',
                timeout=5
            )
            
            if schedule_res.status_code == 200:
                schedule_data = schedule_res.json()
                available_times = schedule_data.get('available_times', [])
                master_name = schedule_data.get('master_name', last_visit.master_name)
                
                # Проверяем то же самое время
                if last_visit.time in available_times:
                    return jsonify({
                        'success': True,
                        'has_recommendation': True,
                        'recommendation': {
                            'master_id': last_visit.master_id,
                            'master_name': master_name,
                            'date': tomorrow.strftime('%Y-%m-%d'),
                            'time': last_visit.time,
                            'message': f'Хотите записаться на завтра ({tomorrow.strftime("%d.%m.%Y")}) в {last_visit.time} к {master_name}?'
                        }
                    })
                else:
                    # Ищем ближайшее доступное время
                    for alt_time in available_times:
                        if abs(int(alt_time[:2]) - int(last_visit.time[:2])) <= 2:
                            return jsonify({
                                'success': True,
                                'has_recommendation': True,
                                'recommendation': {
                                    'master_id': last_visit.master_id,
                                    'master_name': master_name,
                                    'date': tomorrow.strftime('%Y-%m-%d'),
                                    'time': alt_time,
                                    'message': f'{master_name} свободен завтра в {alt_time}'
                                }
                            })
            
        except Exception as e:
            print(f"Ошибка при проверке расписания: {e}")
        
        return jsonify({'success': False, 'has_recommendation': False})
        
    except Exception as e:
        print(f"Ошибка получения рекомендации: {e}")
        return jsonify({'success': False, 'has_recommendation': False})

@app.route('/complete_visit', methods=['POST', 'OPTIONS'])
def complete_visit():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        user_id = data.get('user_id')
        master_id = data.get('master_id')
        date = data.get('date')
        time = data.get('time')
        status = data.get('status', 'completed')
        
        if not all([user_id, master_id, date, time]):
            return jsonify({'error': 'Не все параметры указаны'}), 400
        
        # Получаем день недели
        visit_date = datetime.strptime(date, '%Y-%m-%d')
        day_of_week = visit_date.weekday()
        
        # Получаем имя мастера
        master_name = data.get('master_name', f'Мастер #{master_id}')
        
        # Сохраняем в историю посещений
        visit = VisitHistory(
            user_id=user_id,
            master_id=master_id,
            master_name=master_name,
            date=date,
            time=time,
            day_of_week=day_of_week,
            status=status
        )
        
        db.session.add(visit)
        db.session.commit()
        
        # Обновляем статус в сессиях
        session = SessionHistory.query.filter_by(
            user_id=user_id,
            master_id=master_id,
            date=date,
            time=time
        ).first()
        
        if session:
            session.status = status
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Статус посещения сохранен',
            'visit_id': visit.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сохранения: {str(e)}'}), 500

@app.route('/add_session', methods=['POST', 'OPTIONS'])
def add_session():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        existing = SessionHistory.query.filter_by(
            user_id=data['user_id'],
            master_id=data['master_id'],
            date=data['date'],
            time=data['time']
        ).first()
        
        if existing:
            return jsonify({'error': 'Запись уже существует'}), 400
        
        session = SessionHistory(
            user_id=data['user_id'],
            user_name=data.get('user_name', f'Клиент #{data["user_id"]}'),
            master_id=data['master_id'],
            master_name=data.get('master_name', f'Мастер #{data["master_id"]}'),
            date=data['date'],
            time=data['time'],
            session_date=data['date'],
            status='pending'
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Сеанс добавлен в историю',
            'session_id': session.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка добавления сеанса: {str(e)}'}), 500

@app.route('/user_sessions/<int:user_id>', methods=['GET', 'OPTIONS'])
def get_user_sessions(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        sessions = SessionHistory.query.filter(
            SessionHistory.user_id == user_id,
            SessionHistory.session_date >= week_ago
        ).order_by(SessionHistory.session_date.desc(), SessionHistory.time.desc()).all()
        
        result = []
        for s in sessions:
            result.append({
                'id': s.id,
                'user_id': s.user_id,
                'user_name': s.user_name,
                'master_id': s.master_id,
                'master_name': s.master_name,
                'date': s.date,
                'time': s.time,
                'session_date': s.session_date,
                'status': s.status,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None
            })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'sessions': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения сеансов: {str(e)}'}), 500

@app.route('/update_session/<int:session_id>', methods=['PUT', 'OPTIONS'])
def update_session(session_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data or 'status' not in data:
            return jsonify({'error': 'Не указан статус'}), 400
        
        session = SessionHistory.query.get(session_id)
        if not session:
            return jsonify({'error': 'Сеанс не найден'}), 404
        
        if session.status != 'pending':
            return jsonify({'error': f'Сеанс уже {session.status}'}), 400
        
        old_status = session.status
        session.status = data['status']
        db.session.commit()
        
        # Если сеанс завершен, добавляем в VisitHistory
        if data['status'] == 'completed':
            visit = VisitHistory(
                user_id=session.user_id,
                master_id=session.master_id,
                master_name=session.master_name,
                date=session.date,
                time=session.time,
                day_of_week=datetime.strptime(session.date, '%Y-%m-%d').weekday(),
                status='completed'
            )
            db.session.add(visit)
            db.session.commit()
        
        # Если сеанс отменен - освобождаем слот у мастера
        if data['status'] == 'cancelled':
            try:
                requests.delete(
                    f'http://localhost:5001/free_slot/{session.master_id}/{session.date}/{session.time}',
                    timeout=5
                )
            except:
                print("⚠ Не удалось освободить слот у мастера")
        
        return jsonify({
            'success': True,
            'message': f'Статус сеанса изменен с {old_status} на {data["status"]}',
            'session': {
                'id': session.id,
                'status': session.status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления сеанса: {str(e)}'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("📚 Запуск History Service...")
    print(f"📊 База данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🌐 Адрес: http://localhost:5004")
    print("=" * 50)
    
    try:
        app.run(host='0.0.0.0', port=5004, debug=True)
    except Exception as e:
        print(f"❌ Ошибка запуска сервиса: {e}")