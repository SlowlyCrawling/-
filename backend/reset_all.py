import os
import subprocess
import time
import sys

def reset_all_services():
    """Полный сброс всех сервисов"""
    print("🔄 ПОЛНЫЙ СБРОС ВСЕХ СЕРВИСОВ")
    print("=" * 60)
    
    # 1. Останавливаем все сервисы
    print("1. Остановка всех сервисов...")
    try:
        subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                      capture_output=True, shell=True)
        time.sleep(3)
        print("✅ Все сервисы остановлены")
    except:
        print("⚠ Не удалось остановить сервисы")
    
    # 2. Удаляем базы данных
    print("\n2. Удаление баз данных...")
    services = [
        ("User_Service", "users.db"),
        ("Master_Service", "masters.db"), 
        ("Booking_Service", None),
        ("Confirmation_Service", "bookings.db")
    ]
    
    for service_dir, db_file in services:
        if db_file:
            db_path = os.path.join(service_dir, db_file)
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"   ✅ {service_dir}/{db_file} удален")
            else:
                print(f"   ⏭ {service_dir}/{db_file} не найден")
    
    # 3. Перезапускаем сервисы
    print("\n3. Перезапуск сервисов...")
    
    # Запускаем User Service
    print("   🚀 Запуск User Service...")
    subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="User_Service",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    time.sleep(3)
    
    # Запускаем Master Service
    print("   🚀 Запуск Master Service...")
    subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="Master_Service",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    time.sleep(3)
    
    # Запускаем Booking Service
    print("   🚀 Запуск Booking Service...")
    subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="Booking_Service",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    time.sleep(2)
    
    # Запускаем Confirmation Service
    print("   🚀 Запуск Confirmation Service...")
    subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="Confirmation_Service",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ СЕРВИСЫ ПЕРЕЗАПУЩЕНЫ С ЧИСТЫМИ БАЗАМИ")
    print("\n🌐 АДРЕСА:")
    print("   User Service:        http://localhost:5000")
    print("   Master Service:      http://localhost:5001")
    print("   Booking Service:     http://localhost:5002")
    print("   Confirmation Service:http://localhost:5003")
    print("\n👑 АДМИН ДОСТУП:")
    print("   Email: admin@admin.com")
    print("   Password: admin123")
    print("=" * 60)

if __name__ == "__main__":
    reset_all_services()
    print("\n📌 Нажмите Enter для выхода...")
    input()