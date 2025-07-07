#!/usr/bin/env python3
"""
Скрипт для исправления структуры базы данных черного списка
"""
import asyncio
import aiosqlite
import os

async def fix_blacklist_database():
    """Исправляет структуру базы данных черного списка"""
    db_path = 'data/blacklist.db'
    
    print("🔧 Исправление структуры базы данных черного списка...")
    
    # Создаем директорию data если её нет
    os.makedirs('data', exist_ok=True)
    
    async with aiosqlite.connect(db_path) as db:
        # Проверяем существующую структуру
        cursor = await db.execute("PRAGMA table_info(blacklist)")
        columns = await cursor.fetchall()
        
        if columns:
            print("Существующие столбцы:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Проверяем, есть ли столбец date
            column_names = [col[1] for col in columns]
            if 'date' not in column_names:
                print("Добавляем столбец 'date'...")
                await db.execute("ALTER TABLE blacklist ADD COLUMN date TEXT DEFAULT ''")
                await db.commit()
                print("✅ Столбец 'date' добавлен")
            else:
                print("✅ Столбец 'date' уже существует")
        else:
            print("Таблица не существует, создаем новую...")
            await db.execute('''
                CREATE TABLE blacklist (
                    tg_id INTEGER PRIMARY KEY,
                    reason TEXT,
                    date TEXT
                )
            ''')
            await db.commit()
            print("✅ Таблица blacklist создана")
        
        # Проверяем финальную структуру
        cursor = await db.execute("PRAGMA table_info(blacklist)")
        columns = await cursor.fetchall()
        print("\nФинальная структура таблицы:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

if __name__ == "__main__":
    asyncio.run(fix_blacklist_database())
