from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'masters.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app, resources={r"/*": {"origins": "*"}})

class Master(db.Model):
    __tablename__ = 'masters'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class BookedSlot(db.Model):
    __tablename__ = 'booked_slots'
    id = db.Column(db.Integer, primary_key=True)
    master_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    client_id = db.Column(db.Integer, nullable=False)

class MasterVisitHistory(db.Model):
    __tablename__ = 'master_visit_history'
    id = db.Column(db.Integer, primary_key=True)
    master_id = db.Column(db.Integer, nullable=False)
    client_id = db.Column(db.Integer, nullable=False)
    client_name = db.Column(db.String(100))
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_database():
    with app.app_context():
        db.create_all()
        
        if not Master.query.first():
            masters = [
                {'id': 1, 'name': 'Мастер Анна'},
                {'id': 2, 'name': 'Мастер Борис'}
            ]
            for master_data in masters:
                master = Master(**master_data)
                db.session.add(master)
            db.session.commit()

init_database()

@app.route('/')
def index():
    return jsonify({'service': 'Master Service', 'status': 'running'})

@app.route('/masters', methods=['GET', 'OPTIONS'])
def get_masters():
    if request.method == 'OPTIONS':
        return '', 200
    
    masters = Master.query.all()
    return jsonify({str(m.id): m.name for m in masters})

@app.route('/schedule/<int:master_id>/<date>', methods=['GET', 'OPTIONS'])
def get_schedule(master_id, date):
    if request.method == 'OPTIONS':
        return '', 200
    
    master = Master.query.get(master_id)
    if not master:
        return jsonify({'error': 'Мастер не найден'}), 404
    
    try:
        all_slots = generate_full_schedule(date)
        booked = BookedSlot.query.filter_by(master_id=master_id, date=date).all()
        booked_times = [b.time for b in booked]
        available = [t for t in all_slots if t not in booked_times]
        
        return jsonify({
            'master_id': master_id,
            'master_name': master.name,
            'date': date,
            'available_times': available,
            'booked_times': booked_times,
            'all_slots': all_slots
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка получения расписания: {str(e)}'}), 500

def generate_full_schedule(date):
    try:
        dt = datetime.strptime(date, '%Y-%m-%d')
        weekday = dt.weekday()
        
        if weekday >= 5:
            return []
        
        start = datetime.strptime(f'{date} 10:00', '%Y-%m-%d %H:%M')
        slots = []
        for i in range(8):
            slots.append(start.strftime('%H:%M'))
            start += timedelta(hours=1)
        return slots
    except:
        return []

@app.route('/book_slot/<int:master_id>/<date>/<time>', methods=['POST', 'OPTIONS'])
def book_slot(master_id, date, time):
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.json
    client_id = data.get('client_id')
    
    if not client_id:
        return jsonify({'error': 'Не указан client_id'}), 400
    
    master = Master.query.get(master_id)
    if not master:
        return jsonify({'error': 'Мастер не найден'}), 404
    
    existing = BookedSlot.query.filter_by(master_id=master_id, date=date, time=time).first()
    if existing:
        return jsonify({'success': False, 'error': 'Слот уже забронирован'})
    
    slot = BookedSlot(master_id=master_id, date=date, time=time, client_id=client_id)
    db.session.add(slot)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Слот успешно забронирован',
        'booking_id': slot.id
    })

@app.route('/master_bookings_api/<int:master_id>', methods=['GET', 'OPTIONS'])
def get_master_bookings_api(master_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        bookings = BookedSlot.query.filter_by(master_id=master_id).all()
        result = []
        for b in bookings:
            result.append({
                'id': b.id,
                'date': b.date,
                'time': b.time,
                'client_id': b.client_id
            })
        
        return jsonify({
            'success': True,
            'master_id': master_id,
            'bookings': result,
            'total': len(result)
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка получения записей мастера: {str(e)}'}), 500

@app.route('/add_master_visit', methods=['POST', 'OPTIONS'])
def add_master_visit():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        master_id = data.get('master_id')
        client_id = data.get('client_id')
        client_name = data.get('client_name', f'Клиент #{client_id}')
        date = data.get('date')
        time = data.get('time')
        status = data.get('status', 'completed')
        
        if not all([master_id, date, time]):
            return jsonify({'error': 'Не все параметры указаны'}), 400
        
        # Создаем запись в истории мастера
        visit = MasterVisitHistory(
            master_id=master_id,
            client_id=client_id,
            client_name=client_name,
            date=date,
            time=time,
            status=status
        )
        
        db.session.add(visit)
        
        # Удаляем из активных записей если статус completed
        if status == 'completed':
            slot = BookedSlot.query.filter_by(
                master_id=master_id,
                date=date,
                time=time
            ).first()
            
            if slot:
                db.session.delete(slot)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Посещение добавлено в историю мастера',
            'visit_id': visit.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сохранения: {str(e)}'}), 500

@app.route('/master_visit_history/<int:master_id>', methods=['GET', 'OPTIONS'])
def get_master_visit_history(master_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        visits = MasterVisitHistory.query.filter_by(master_id=master_id)\
            .order_by(MasterVisitHistory.date.desc(), MasterVisitHistory.time.desc())\
            .all()
        
        result = []
        for visit in visits:
            result.append({
                'id': visit.id,
                'master_id': visit.master_id,
                'client_id': visit.client_id,
                'client_name': visit.client_name,
                'date': visit.date,
                'time': visit.time,
                'status': visit.status
            })
        
        return jsonify({
            'success': True,
            'master_id': master_id,
            'visits': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения истории: {str(e)}'}), 500

@app.route('/free_slot/<int:master_id>/<date>/<time>', methods=['DELETE', 'OPTIONS'])
def free_slot(master_id, date, time):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        slot = BookedSlot.query.filter_by(master_id=master_id, date=date, time=time).first()
        
        if slot:
            db.session.delete(slot)
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Слот освобожден'
            })
        
        return jsonify({'error': 'Слот не найден'}), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка освобождения слота: {str(e)}'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск Master Service...")
    print(f"📊 База данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🌐 Адрес: http://localhost:5001")
    print("=" * 50)
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    except Exception as e:
        print(f"❌ Ошибка запуска сервиса: {e}")