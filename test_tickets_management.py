#!/usr/bin/env python3
"""
Тест функциональности управления заявками и тикетами
"""

import os
import sys
import shutil
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath('.'))

from app.database.models import (
    init_db, get_or_create_user, create_order, get_all_orders, clear_all_orders,
    create_support_ticket, get_all_support_tickets, delete_support_ticket, clear_all_support_tickets
)

def setup_test_db():
    """Создает тестовую базу данных"""
    # Создаем резервную копию оригинальной базы
    if os.path.exists('users.db'):
        shutil.copy2('users.db', 'users_backup_tickets_test.db')
        logging.info("✅ Создана резервная копия базы данных")
    
    # Удаляем текущую базу и создаем новую
    if os.path.exists('users.db'):
        os.remove('users.db')
    
    init_db()
    logging.info("✅ Тестовая база данных создана")

def create_test_data():
    """Создает тестовые данные"""
    # Создаем тестового пользователя
    test_tg_id = 888888888
    user = get_or_create_user(test_tg_id, "Test User Tickets", "test_user_tickets", datetime.now().isoformat())
    logging.info(f"✅ Создан тестовый пользователь: {user['username']} (ID: {test_tg_id})")
    
    # Создаем тестовые заявки
    create_order(user['id'], 'premium', 100.0, 'pending', extra_data='{"description": "Тестовая заявка премиум"}')
    create_order(user['id'], 'stars', 50.0, 'pending', extra_data='{"description": "Тестовая заявка звезды"}')
    create_order(user['id'], 'crypto', 200.0, 'pending', extra_data='{"description": "Тестовая заявка крипта"}')
    logging.info("✅ Созданы тестовые заявки")
    
    # Создаем тестовые тикеты
    create_support_ticket(user['id'], user['username'], user['full_name'], "Тестовый тикет 1")
    create_support_ticket(user['id'], user['username'], user['full_name'], "Тестовый тикет 2")
    create_support_ticket(user['id'], user['username'], user['full_name'], "Тестовый тикет 3")
    logging.info("✅ Созданы тестовые тикеты")
    
    return user

def test_orders_management():
    """Тестирует управление заявками"""
    logging.info("📋 Тестируем управление заявками...")
    
    # Проверяем, что заявки созданы
    orders = get_all_orders()
    if len(orders) != 3:
        raise Exception(f"Ожидалось 3 заявки, найдено {len(orders)}")
    logging.info(f"✅ Найдено {len(orders)} заявок")
    
    # Тестируем удаление всех заявок
    clear_all_orders()
    orders_after = get_all_orders()
    if len(orders_after) != 0:
        raise Exception(f"После удаления должно быть 0 заявок, найдено {len(orders_after)}")
    logging.info("✅ Все заявки успешно удалены")

def test_tickets_management():
    """Тестирует управление тикетами"""
    logging.info("🎟️ Тестируем управление тикетами...")
    
    # Проверяем, что тикеты созданы
    tickets = get_all_support_tickets()
    if len(tickets) != 3:
        raise Exception(f"Ожидалось 3 тикета, найдено {len(tickets)}")
    logging.info(f"✅ Найдено {len(tickets)} тикетов")
    
    # Тестируем удаление отдельного тикета
    first_ticket_id = tickets[0][0]  # ID первого тикета
    delete_support_ticket(first_ticket_id)
    tickets_after_single_delete = get_all_support_tickets()
    if len(tickets_after_single_delete) != 2:
        raise Exception(f"После удаления одного тикета должно остаться 2, найдено {len(tickets_after_single_delete)}")
    logging.info(f"✅ Тикет #{first_ticket_id} успешно удален")
    
    # Тестируем удаление всех тикетов
    clear_all_support_tickets()
    tickets_after_clear = get_all_support_tickets()
    if len(tickets_after_clear) != 0:
        raise Exception(f"После удаления всех тикетов должно быть 0, найдено {len(tickets_after_clear)}")
    logging.info("✅ Все тикеты успешно удалены")

def restore_original_db():
    """Восстанавливает оригинальную базу данных"""
    if os.path.exists('users_backup_tickets_test.db'):
        if os.path.exists('users.db'):
            os.remove('users.db')
        shutil.move('users_backup_tickets_test.db', 'users.db')
        logging.info("✅ Оригинальная база данных восстановлена")

def main():
    """Основная функция теста"""
    try:
        logging.info("🧪 Начинаем тест управления заявками и тикетами")
        
        # Настройка тестовой среды
        setup_test_db()
        
        # Создание тестовых данных
        user = create_test_data()
        
        # Тестирование функций
        test_orders_management()
        test_tickets_management()
        
        logging.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\n✅ Функциональность управления заявками и тикетами работает корректно!")
        print("📝 Результат:")
        print("  - Удаление всех заявок: ✅")
        print("  - Удаление отдельных тикетов: ✅") 
        print("  - Удаление всех тикетов: ✅")
        
    except Exception as e:
        logging.error(f"❌ ТЕСТ ПРОВАЛЕН: {e}")
        print(f"\n❌ Тест провален! Проверьте логи для деталей.")
        return False
    finally:
        restore_original_db()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
