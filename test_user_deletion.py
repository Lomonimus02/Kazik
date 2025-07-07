#!/usr/bin/env python3
"""
Тест функциональности удаления пользователей
"""
import asyncio
import sqlite3
import os
import sys
import logging
from datetime import datetime

# Добавляем путь к проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.chdir(current_dir)

from app.database.models import (
    init_db, get_or_create_user, get_user_profile,
    delete_user_everywhere_full, update_balance
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_test_db():
    """Создает тестовую базу данных"""
    # Создаем резервную копию если есть
    if os.path.exists('data/users.db'):
        os.rename('data/users.db', 'data/users_backup_test.db')
        logger.info("✅ Создана резервная копия базы данных")
    
    # Инициализируем новую БД
    init_db()
    logger.info("✅ Тестовая база данных создана")

def restore_db():
    """Восстанавливает оригинальную базу данных"""
    if os.path.exists('data/users_backup_test.db'):
        if os.path.exists('data/users.db'):
            os.remove('data/users.db')
        os.rename('data/users_backup_test.db', 'data/users.db')
        logger.info("✅ Оригинальная база данных восстановлена")

def create_test_user():
    """Создает тестового пользователя с данными"""
    test_tg_id = 999999999
    test_username = "test_user_delete"
    test_full_name = "Test User Delete"
    reg_date = datetime.now().strftime("%Y-%m-%d")
    
    # Создаем пользователя
    user = get_or_create_user(test_tg_id, test_full_name, test_username, reg_date)
    logger.info(f"✅ Создан тестовый пользователь: {test_username} (ID: {test_tg_id})")
    
    # Добавляем баланс
    update_balance(test_tg_id, 100.0)
    
    # Создаем заказ
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO orders (user_id, order_type, amount, status, created_at) 
                     VALUES (?, ?, ?, ?, ?)''', 
                  (user['id'], 'stars', 50, 'pending', datetime.now().isoformat()))
    
    # Добавляем отзыв
    cursor.execute('''INSERT INTO reviews (user_id, text, status, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (user['id'], 'Тестовый отзыв', 'pending', datetime.now().isoformat()))
    
    # Добавляем активность в календарь
    cursor.execute('''INSERT INTO activity_calendar (user_id, date, activity_type, reward_type, reward_amount) 
                     VALUES (?, ?, ?, ?, ?)''', 
                  (user['id'], datetime.now().strftime("%Y-%m-%d"), 'daily', 'money', 10.0))
    
    # Добавляем в слот-машину
    cursor.execute('''INSERT INTO slot_machine (user_id, combination, reward_type, reward_amount, created_at) 
                     VALUES (?, ?, ?, ?, ?)''', 
                  (user['id'], '🍒🍒🍒', 'money', 25.0, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    logger.info("✅ Добавлены тестовые данные пользователя")
    return test_tg_id, user['id']

def check_user_data_exists(tg_id, user_id):
    """Проверяет существование данных пользователя в базе"""
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    
    tables_to_check = [
        ('users', 'tg_id', tg_id),
        ('orders', 'user_id', user_id),
        ('reviews', 'user_id', user_id),
        ('activity_calendar', 'user_id', user_id),
        ('slot_machine', 'user_id', user_id),
        ('withdrawals', 'user_id', user_id),
        ('roulette_attempts', 'user_id', user_id),
        ('roulette_history', 'user_id', user_id),
    ]
    
    results = {}
    for table, column, value in tables_to_check:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE {column} = ?', (value,))
            count = cursor.fetchone()[0]
            results[table] = count
        except sqlite3.OperationalError:
            # Таблица не существует
            results[table] = 0
    
    conn.close()
    return results

def test_user_deletion():
    """Основной тест удаления пользователя"""
    logger.info("🧪 Начинаем тест удаления пользователя")
    
    try:
        # 1. Настройка тестовой среды
        setup_test_db()
        
        # 2. Создание тестового пользователя
        test_tg_id, test_user_id = create_test_user()
        
        # 3. Проверка данных до удаления
        logger.info("📊 Проверяем данные до удаления...")
        data_before = check_user_data_exists(test_tg_id, test_user_id)
        logger.info(f"Данные до удаления: {data_before}")
        
        # Проверяем, что пользователь существует
        user_profile = get_user_profile(test_tg_id)
        assert user_profile is not None, "Пользователь должен существовать"
        assert user_profile['balance'] == 100.0, "Баланс должен быть 100.0"
        logger.info("✅ Пользователь найден в базе данных")
        
        # 4. Удаление пользователя
        logger.info("🗑️ Удаляем пользователя...")
        delete_user_everywhere_full(test_tg_id)
        
        # 5. Проверка данных после удаления
        logger.info("📊 Проверяем данные после удаления...")
        data_after = check_user_data_exists(test_tg_id, test_user_id)
        logger.info(f"Данные после удаления: {data_after}")
        
        # Проверяем, что пользователь удален
        user_profile_after = get_user_profile(test_tg_id)
        assert user_profile_after is None, "Пользователь должен быть удален"
        logger.info("✅ Пользователь удален из основной таблицы")
        
        # Проверяем, что все связанные данные удалены
        for table, count in data_after.items():
            assert count == 0, f"В таблице {table} должно быть 0 записей, найдено: {count}"
        
        logger.info("✅ Все связанные данные удалены")
        
        # 6. Тест повторного создания пользователя (симуляция /start)
        logger.info("🔄 Тестируем повторное создание пользователя...")
        new_user = get_or_create_user(test_tg_id, "Test User Delete", "test_user_delete", 
                                     datetime.now().strftime("%Y-%m-%d"))
        
        assert new_user is not None, "Новый пользователь должен быть создан"
        assert new_user['balance'] == 0.0, "Баланс нового пользователя должен быть 0"
        logger.info("✅ Пользователь успешно создан заново как новый")
        
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
        
    except Exception as e:
        logger.error(f"❌ ТЕСТ ПРОВАЛЕН: {str(e)}")
        return False
    
    finally:
        # Восстанавливаем оригинальную БД
        restore_db()

if __name__ == "__main__":
    success = test_user_deletion()
    if success:
        print("\n✅ Функция удаления пользователей работает корректно!")
        print("📝 Результат: Пользователь полностью удаляется из всех таблиц")
        print("🔄 При повторном запуске бота пользователь создается как новый")
    else:
        print("\n❌ Тест провален! Проверьте логи для деталей.")
        sys.exit(1)
