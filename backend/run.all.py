import subprocess
import time
import sys
import os
import socket
import atexit

def run_service(name, command, port, delay=2):
    """Запускает сервис и отслеживает его вывод"""
    print(f"🚀 Запуск {name} на порту {port}...")
    
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                command,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        print(f"✅ {name} запущен")
        time.sleep(delay)
        return process
        
    except Exception as e:
        print(f"❌ Ошибка запуска {name}: {e}")
        return None

def check_port(port, timeout=10):
    """Проверяет доступность порта"""
    for _ in range(timeout):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                return True
        except:
            pass
        
        time.sleep(0.5)
    
    return False

def install_dependencies():
    """Установка только необходимых зависимостей"""
    print("\n📦 Установка базовых зависимостей...")
    
    try:
        import importlib.util
        
        # Проверяем только Flask и requests
        required = [
            ('flask', 'Flask'),
            ('flask_cors', 'flask-cors'),
            ('requests', 'requests')
        ]
        
        missing = []
        for import_name, package_name in required:
            try:
                importlib.util.find_spec(import_name.split('.')[0])
            except:
                missing.append(package_name)
        
        if missing:
            print(f"   Установка: {', '.join(missing)}")
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing, 
                          check=False, capture_output=True)
            print(" Зависимости установлены")
        else:
            print(" Все зависимости уже установлены")
            
    except Exception as e:
        print(f"⚠ Предупреждение: {e}")

def main():
    print("=" * 60)
    print("          ПАРИКМАХЕРСКИЙ САЛОН - СИСТЕМА БРОНИРОВАНИЯ")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Устанавливаем зависимости
    install_dependencies()
    
    # Сервисы для запуска
    services = [
        {
            "name": "User Service",
            "port": 5000,
            "cmd": f'cd "{os.path.join(base_dir, "User_Service")}" && python app.py',
            "delay": 2
        },
        {
            "name": "Master Service", 
            "port": 5001,
            "cmd": f'cd "{os.path.join(base_dir, "Master_Service")}" && python app.py',
            "delay": 2
        },
        {
            "name": "Booking Service",
            "port": 5002, 
            "cmd": f'cd "{os.path.join(base_dir, "Booking_Service")}" && python app.py',
            "delay": 2
        },
        {
            "name": "Confirmation Service",
            "port": 5003,
            "cmd": f'cd "{os.path.join(base_dir, "Confirmation_Service")}" && python app.py',
            "delay": 2
        },
        {
            "name": "History Service",
            "port": 5004,
            "cmd": f'cd "{os.path.join(base_dir, "History_Service")}" && python app.py',
            "delay": 2
        },
        {
            "name": "Sync Service",
            "port": 5005,
            "cmd": f'cd "{base_dir}" && python sync_service.py',
            "delay": 2
        }
    ]
    
    processes = []
    
    print("\n" + "=" * 60)
    print("🚀 Запуск сервисов...")
    print("=" * 60)
    
    # Запускаем сервисы
    for service in services:
        process = run_service(
            service["name"], 
            service["cmd"], 
            service["port"],
            service.get("delay", 2)
        )
        if process:
            processes.append((service["name"], process, service["port"]))
    
    print("\n" + "=" * 60)
    print("⏳ Проверка доступности сервисов...")
    print("=" * 60)
    
    # Проверяем доступность
    for name, process, port in processes:
        if check_port(port):
            print(f"✅ {name} (порт {port}): ЗАПУЩЕН")
        else:
            print(f"⚠ {name} (порт {port}): ПРОВЕРКА НЕ УДАЛАСЬ")
    

    print("\n🛑 Для остановки: Нажмите Ctrl+C")
    print("=" * 60)
    
    # Основной цикл
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка системы...")
        for name, process, port in processes:
            try:
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /pid {process.pid} /f /t", 
                                  shell=True, capture_output=True)
                else:
                    process.terminate()
                print(f"   Остановлен: {name}")
            except:
                pass
        
        print("\n✅ Все сервисы остановлены")

if __name__ == "__main__":
    main()