#!/usr/bin/env python3
"""
Скрипт для миграции базы данных
Добавляет недостающие столбцы в таблицу orders
"""

import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.models import migrate_orders_table, migrate_reviews_table, migrate_support_tickets_table

def main():
    print("🔄 Начинаю миграцию базы данных...")
    
    try:
        # Миграция таблицы orders
        print("📋 Миграция таблицы orders...")
        migrate_orders_table()
        print("✅ Таблица orders успешно мигрирована")
        
        # Миграция таблицы reviews
        print("📋 Миграция таблицы reviews...")
        migrate_reviews_table()
        print("✅ Таблица reviews успешно мигрирована")
        
        # Миграция таблицы support_tickets
        print("📋 Миграция таблицы support_tickets...")
        migrate_support_tickets_table()
        print("✅ Таблица support_tickets успешно мигрирована")
        
        print("\n🎉 Все миграции выполнены успешно!")
        print("Теперь можно запускать бота без ошибок.")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 