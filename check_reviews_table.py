#!/usr/bin/env python3
"""
Проверка структуры таблицы отзывов
"""
import sqlite3

def check_reviews_table():
    """Проверяет структуру таблицы reviews"""
    print("🔍 ПРОВЕРКА ТАБЛИЦЫ REVIEWS")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(reviews)")
        columns = cursor.fetchall()
        
        print("Колонки в таблице reviews:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} ({col[2]})")
        
        # Проверяем данные
        cursor.execute("SELECT * FROM reviews LIMIT 3")
        rows = cursor.fetchall()
        
        print(f"\nПримеры данных ({len(rows)} записей):")
        for i, row in enumerate(rows):
            print(f"  Запись {i+1}: {row}")
        
        # Проверяем SQL создания таблицы
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reviews'")
        sql = cursor.fetchone()
        if sql:
            print(f"\nSQL создания таблицы:\n{sql[0]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    check_reviews_table()
