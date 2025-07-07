#!/usr/bin/env python3
"""
Скрипт для проверки структуры базы данных
"""

import sys
import os
import sqlite3

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_orders_table():
    """Проверяет структуру таблицы orders"""
    try:
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        
        # Получаем информацию о столбцах таблицы orders
        cursor.execute("PRAGMA table_info(orders)")
        columns = cursor.fetchall()
        
        print("📋 Структура таблицы orders:")
        print("-" * 50)
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'} - {'PRIMARY KEY' if col[5] else ''}")
        
        # Проверяем наличие необходимых столбцов
        column_names = [col[1] for col in columns]
        required_columns = ['id', 'user_id', 'order_type', 'amount', 'status', 'created_at', 'file_id', 'extra_data']
        
        print("\n✅ Проверка необходимых столбцов:")
        for col in required_columns:
            if col in column_names:
                print(f"  ✅ {col}")
            else:
                print(f"  ❌ {col} - ОТСУТСТВУЕТ!")
        
        # Проверяем количество записей
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        print(f"\n📊 Количество записей в таблице orders: {count}")
        
        conn.close()
        
        # Проверяем, что все необходимые столбцы есть
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            print(f"\n❌ ОШИБКА: Отсутствуют столбцы: {missing_columns}")
            return False
        else:
            print("\n🎉 Все необходимые столбцы присутствуют!")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
        return False

def main():
    print("🔍 Проверка структуры базы данных...")
    print("=" * 50)
    
    success = check_orders_table()
    
    if success:
        print("\n✅ База данных готова к работе!")
        print("Бот должен запускаться без ошибок.")
    else:
        print("\n❌ Проблемы с базой данных!")
        print("Необходимо выполнить миграцию.")

if __name__ == "__main__":
    main() 