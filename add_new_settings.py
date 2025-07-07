#!/usr/bin/env python3
"""
Скрипт для добавления новых настроек в существующую базу данных
"""

import sqlite3
import os

def add_new_settings():
    """Добавляет новые настройки в базу данных"""
    db_path = "data/users.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Новые настройки для добавления
        new_settings = [
            ('profile_description', '🚀 <b>Ваш профиль</b>\n\nЗдесь вы можете посмотреть информацию о своем аккаунте, балансе и истории операций.', 'Описание профиля'),
            ('profile_photo', 'https://imgur.com/a/TkOPe7c.jpeg', 'Фото профиля'),
            ('slot_description', '🎰 <b>Слот-машина</b>\n\nСлот-машина — это бесплатная игра от Legal Stars.\n\n🎁Выигрывайте деньги, звёзды и TON!', 'Описание слот-машины'),
            ('slot_photo', 'https://imgur.com/a/TkOPe7c.jpeg', 'Фото слот-машины'),
            ('calendar_description', '📅 <b>Календарь активности</b>\n\nОтмечайте активность каждый день и получайте награды за постоянство!', 'Описание календаря'),
            ('calendar_photo', 'https://imgur.com/a/TkOPe7c.jpeg', 'Фото календаря'),
        ]
        
        added_count = 0
        
        for key, value, description in new_settings:
            # Проверяем, существует ли уже настройка
            cursor.execute("SELECT key FROM admin_settings WHERE key = ?", (key,))
            if cursor.fetchone():
                print(f"⚠️ Настройка {key} уже существует, пропускаем")
                continue
            
            # Добавляем новую настройку
            cursor.execute(
                "INSERT INTO admin_settings (key, value, description) VALUES (?, ?, ?)",
                (key, value, description)
            )
            print(f"✅ Добавлена настройка: {key}")
            added_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"\n📊 Результат: добавлено {added_count} новых настроек")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении настроек: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 Добавление новых настроек в базу данных...")
    
    if add_new_settings():
        print("🎉 Новые настройки успешно добавлены!")
        return True
    else:
        print("❌ Не удалось добавить настройки")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
