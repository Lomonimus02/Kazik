#!/usr/bin/env python3
"""
Простой тест для проверки добавления новых настроек в админ панель
"""

import sqlite3
import os

def test_admin_settings():
    """Проверяет наличие новых настроек в базе данных"""
    db_path = "data/users.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных users.db не найдена")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем наличие таблицы admin_settings
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_settings'")
        if not cursor.fetchone():
            print("❌ Таблица admin_settings не найдена")
            return False
        
        # Проверяем новые настройки
        new_settings = [
            'profile_description',
            'profile_photo', 
            'slot_description',
            'slot_photo',
            'calendar_description',
            'calendar_photo'
        ]
        
        found_settings = []
        missing_settings = []
        
        for setting in new_settings:
            cursor.execute("SELECT value FROM admin_settings WHERE key = ?", (setting,))
            result = cursor.fetchone()
            if result:
                found_settings.append(setting)
                print(f"✅ Найдена настройка: {setting} = {result[0][:50]}...")
            else:
                missing_settings.append(setting)
                print(f"❌ Отсутствует настройка: {setting}")
        
        conn.close()
        
        print(f"\n📊 Результат: {len(found_settings)}/{len(new_settings)} новых настроек найдено")
        
        if missing_settings:
            print(f"⚠️ Отсутствующие настройки: {', '.join(missing_settings)}")
            return False
        else:
            print("🎉 Все новые настройки найдены в базе данных!")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")
        return False

def test_admin_handlers():
    """Проверяет наличие новых обработчиков в admin_settings.py"""
    admin_file = "app/handlers/admin_settings.py"
    
    if not os.path.exists(admin_file):
        print("❌ Файл admin_settings.py не найден")
        return False
    
    try:
        with open(admin_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие новых кнопок в меню
        checks = [
            ('Описание профиля', 'admin_setting_profile_description'),
            ('Описание слот-машины', 'admin_setting_slot_description'), 
            ('Описание календаря', 'admin_setting_calendar_description'),
            ('Изменить фото профиля', 'admin_setting_profile_photo'),
            ('Изменить фото слот-машины', 'admin_setting_slot_photo'),
            ('Изменить фото календаря', 'admin_setting_calendar_photo')
        ]
        
        found_checks = []
        missing_checks = []
        
        for description, callback_data in checks:
            if callback_data in content:
                found_checks.append(description)
                print(f"✅ Найден обработчик: {description}")
            else:
                missing_checks.append(description)
                print(f"❌ Отсутствует обработчик: {description}")
        
        print(f"\n📊 Результат: {len(found_checks)}/{len(checks)} обработчиков найдено")
        
        if missing_checks:
            print(f"⚠️ Отсутствующие обработчики: {', '.join(missing_checks)}")
            return False
        else:
            print("🎉 Все новые обработчики найдены!")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при проверке файла: {e}")
        return False

def test_handler_updates():
    """Проверяет обновления в обработчиках пользователей"""
    files_to_check = [
        ('app/handlers/user.py', ['get_admin_setting', 'profile_description', 'profile_photo']),
        ('app/handlers/slot_machine.py', ['get_admin_setting', 'slot_description', 'slot_photo']),
        ('app/handlers/activity_calendar.py', ['get_admin_setting', 'calendar_description', 'calendar_photo'])
    ]
    
    all_passed = True
    
    for file_path, required_strings in files_to_check:
        if not os.path.exists(file_path):
            print(f"❌ Файл {file_path} не найден")
            all_passed = False
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_strings = []
            missing_strings = []
            
            for required_string in required_strings:
                if required_string in content:
                    found_strings.append(required_string)
                else:
                    missing_strings.append(required_string)
            
            print(f"\n📁 Файл: {file_path}")
            print(f"✅ Найдено: {', '.join(found_strings)}")
            
            if missing_strings:
                print(f"❌ Отсутствует: {', '.join(missing_strings)}")
                all_passed = False
            else:
                print("🎉 Все требуемые изменения найдены!")
                
        except Exception as e:
            print(f"❌ Ошибка при проверке {file_path}: {e}")
            all_passed = False
    
    return all_passed

def main():
    """Главная функция теста"""
    print("🚀 Запуск простого теста системы редактирования контента...")
    
    tests = [
        ("Проверка настроек в БД", test_admin_settings),
        ("Проверка обработчиков админ панели", test_admin_handlers),
        ("Проверка обновлений обработчиков", test_handler_updates)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}...")
        try:
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name}: ПРОЙДЕН")
            else:
                print(f"❌ {test_name}: НЕ ПРОЙДЕН")
        except Exception as e:
            print(f"❌ {test_name}: ОШИБКА - {e}")
    
    print(f"\n🏁 Итоговый результат: {passed_tests}/{total_tests} тестов прошли успешно")
    
    if passed_tests == total_tests:
        print("🎉 Все тесты прошли! Система редактирования контента готова к использованию.")
        return True
    else:
        print("⚠️ Некоторые тесты не прошли. Требуется доработка.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
