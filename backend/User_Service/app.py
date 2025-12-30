from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настраиваем CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Создаем экземпляр SQLAlchemy
db = SQLAlchemy(app)

# Определяем модель User
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

def init_database():
    with app.app_context():
        try:
            # Создаем таблицы если их нет
            db.create_all()
            
            # Проверяем есть ли админ
            admin = User.query.filter_by(email='admin@admin.com').first()
            if not admin:
                # Добавляем админа
                hashed = generate_password_hash('admin123')
                admin = User(
                    name='Администратор', 
                    email='admin@admin.com', 
                    password_hash=hashed, 
                    role='admin'
                )
                db.session.add(admin)
                print("✅ Администратор создан")
            
            # Проверяем есть ли мастера
            masters = User.query.filter_by(role='master').all()
            if not masters:
                # Добавляем мастеров как пользователей с ролью master
                masters_data = [
                    {'name': 'Мастер Анна', 'email': 'anna@master.com', 'password': 'masterpass', 'role': 'master'},
                    {'name': 'Мастер Борис', 'email': 'boris@master.com', 'password': 'masterpass', 'role': 'master'}
                ]
                
                for master_data in masters_data:
                    # Проверяем не существует ли уже
                    existing = User.query.filter_by(email=master_data['email']).first()
                    if not existing:
                        hashed = generate_password_hash(master_data['password'])
                        master = User(
                            name=master_data['name'],
                            email=master_data['email'],
                            password_hash=hashed,
                            role=master_data['role']
                        )
                        db.session.add(master)
                        print(f"✅ Мастер {master_data['name']} создан")
            
            db.session.commit()
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации базы данных: {e}")
            db.session.rollback()
            raise e

# Основные эндпоинты (остальное без изменений)
@app.route('/')
def index():
    return jsonify({
        'service': 'User Service',
        'status': 'running',
        'version': '1.0',
        'endpoints': {
            'register': '/register [POST]',
            'login': '/login [POST]',
            'get_user': '/user/<id> [GET]',
            'get_all_users': '/users [GET]',
            'admin_update_user': '/admin/update_user/<id> [PUT]',
            'admin_delete_user': '/admin/delete_user/<id> [DELETE]'
        }
    })

@app.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not all([name, email, password]):
            return jsonify({'error': 'Не все поля заполнены'}), 400
        
        # Проверяем уникальность email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email уже зарегистрирован'}), 400
        
        # Создаем пользователя
        hashed_password = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=hashed_password,
            role='client'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user_id': new_user.id,
            'role': new_user.role,
            'name': new_user.name,
            'message': 'Клиент зарегистрирован'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка регистрации: {str(e)}'}), 500

@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Не все поля заполнены'}), 400
        
        # Ищем пользователя
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        # Проверяем пароль
        if not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Неверный пароль'}), 401
        
        return jsonify({
            'success': True,
            'user_id': user.id,
            'role': user.role,
            'name': user.name,
            'message': 'Вход успешен'
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка входа: {str(e)}'}), 500

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        return jsonify(user.to_dict())
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения пользователя: {str(e)}'}), 500

# Админ эндпоинты
@app.route('/users', methods=['GET'])
def get_all_users():
    try:
        users = User.query.all()
        users_list = [user.to_dict() for user in users]
        
        return jsonify({
            'success': True,
            'total': len(users_list),
            'users': users_list
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения пользователей: {str(e)}'}), 500

@app.route('/admin/update_user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        # Обновляем данные
        if 'name' in data:
            user.name = data['name']
        
        if 'email' in data:
            # Проверяем уникальность email
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user_id:
                return jsonify({'error': 'Email уже используется другим пользователем'}), 400
            user.email = data['email']
        
        if 'role' in data:
            user.role = data['role']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Пользователь обновлен',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка обновления пользователя: {str(e)}'}), 500

@app.route('/admin/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        # Не позволяем удалить последнего админа
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({'error': 'Нельзя удалить последнего администратора'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Пользователь удален'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка удаления пользователя: {str(e)}'}), 500

@app.route('/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        total_users = User.query.count()
        total_masters = User.query.filter_by(role='master').count()
        total_clients = User.query.filter_by(role='client').count()
        total_admins = User.query.filter_by(role='admin').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_masters': total_masters,
                'total_clients': total_clients,
                'total_admins': total_admins
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения статистики: {str(e)}'}), 500

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
    print("🚀 Запуск User Service...")
    print(f"📊 База данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🌐 Адрес: http://localhost:5000")
    print("=" * 50)
    
    # Инициализируем базу данных
    init_database()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"❌ Ошибка запуска сервиса: {e}")