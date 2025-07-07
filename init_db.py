#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""
from app.database.models import init_db, create_roulette_tables, init_roulette_configs

def main():
    print("🔧 Инициализация базы данных...")
    
    # Инициализируем основную базу данных
    init_db()
    print("✅ Основная база данных инициализирована")
    
    # Создаем таблицы рулетки
    create_roulette_tables()
    print("✅ Таблицы рулетки созданы")
    
    # Инициализируем конфиги рулетки
    init_roulette_configs()
    print("✅ Конфиги рулетки инициализированы")
    
    print("🎉 База данных полностью инициализирована!")

if __name__ == "__main__":
    main() 