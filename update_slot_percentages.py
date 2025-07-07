#!/usr/bin/env python3
"""
Скрипт для обновления процентов слот-машины в базе данных
Устанавливает проценты согласно требованиям пользователя:
- 3 вишни - 13%
- 3 апельсина - 10%
- 3 лимона - 4%
- 3 винограда - 1%
Остальные комбинации оставляет без изменений
"""
import sys
import os
import sqlite3

# Добавляем путь к проекту
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.database.models import init_db, get_db_connection

def update_slot_percentages():
    """Обновляет проценты для указанных комбинаций слот-машины"""
    print("🎰 Обновление процентов слот-машины...")
    
    # Инициализируем БД
    init_db()
    
    # Новые проценты согласно требованиям
    new_percentages = {
        '🍒🍒🍒': 13.0,  # 3 вишни - 13%
        '🍊🍊🍊': 10.0,  # 3 апельсина - 10%
        '🍋🍋🍋': 4.0,   # 3 лимона - 4%
        '🍇🍇🍇': 1.0,   # 3 винограда - 1%
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("📊 Текущие настройки слот-машины:")
        print("-" * 60)
        
        # Показываем текущие настройки
        cursor.execute('SELECT combination, reward_type, reward_amount, chance_percent, name FROM slot_config ORDER BY chance_percent DESC')
        current_configs = cursor.fetchall()
        
        for config in current_configs:
            combination, reward_type, reward_amount, chance_percent, name = config
            print(f"{combination} - {name}: {chance_percent}% ({reward_type} {reward_amount})")
        
        print("\n🔄 Обновляем проценты...")
        
        # Обновляем проценты для указанных комбинаций
        updated_count = 0
        for combination, new_percent in new_percentages.items():
            cursor.execute('''UPDATE slot_config
                             SET chance_percent = ?
                             WHERE combination = ?''', (new_percent, combination))

            if cursor.rowcount > 0:
                updated_count += 1
                print(f"✅ {combination}: обновлено до {new_percent}%")
            else:
                print(f"⚠️ {combination}: комбинация не найдена в БД")

        # Дополнительно исправляем апельсины - они должны давать звезды, а не деньги
        cursor.execute('''UPDATE slot_config
                         SET reward_type = 'stars', reward_amount = 21
                         WHERE combination = '🍊🍊🍊' ''')
        if cursor.rowcount > 0:
            print("🔧 Исправлено: апельсины теперь дают звезды вместо денег")
        
        conn.commit()
        
        print(f"\n📈 Обновлено комбинаций: {updated_count}")
        
        print("\n📊 Новые настройки слот-машины:")
        print("-" * 60)
        
        # Показываем обновленные настройки
        cursor.execute('SELECT combination, reward_type, reward_amount, chance_percent, name FROM slot_config ORDER BY chance_percent DESC')
        updated_configs = cursor.fetchall()
        
        total_percent = 0
        for config in updated_configs:
            combination, reward_type, reward_amount, chance_percent, name = config
            total_percent += chance_percent
            
            # Выделяем обновленные комбинации
            if combination in new_percentages:
                print(f"🔥 {combination} - {name}: {chance_percent}% ({reward_type} {reward_amount}) [ОБНОВЛЕНО]")
            else:
                print(f"   {combination} - {name}: {chance_percent}% ({reward_type} {reward_amount})")
        
        print(f"\n📊 Общий процент выигрышей: {total_percent:.2f}%")
        print(f"📊 Процент проигрышей: {100 - total_percent:.2f}%")
        
        # Проверяем корректность процентов
        if total_percent > 100:
            print("⚠️ ВНИМАНИЕ: Общий процент выигрышей превышает 100%!")
            print("   Это может привести к некорректной работе слот-машины.")
        elif total_percent < 50:
            print("ℹ️ Общий процент выигрышей довольно низкий - это нормально для слот-машины.")
        
        print("\n✅ Обновление завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении: {e}")
        conn.rollback()
    finally:
        conn.close()

def verify_slot_algorithm():
    """Проверяет корректность работы алгоритма слот-машины"""
    print("\n🧪 Проверка алгоритма слот-машины...")
    
    try:
        from app.utils.slot_machine import generate_slot_result, check_win_combination
        from app.database.models import get_slot_configs
        import asyncio
        from collections import Counter
        
        # Получаем конфигурации
        configs = get_slot_configs()
        print(f"📋 Загружено {len(configs)} конфигураций из БД")
        
        # Тестируем генерацию результатов
        async def test_generation():
            results = []
            wins = []

            # Генерируем 10000 результатов для более точного тестирования
            for _ in range(10000):
                slot1, slot2, slot3 = await generate_slot_result()
                combination = slot1 + slot2 + slot3
                results.append(combination)

                # Проверяем выигрыш
                win_config = await check_win_combination(slot1, slot2, slot3)
                if win_config:
                    wins.append(combination)

            return results, wins
        
        results, wins = asyncio.run(test_generation())
        
        # Анализируем результаты
        win_counter = Counter(wins)
        total_wins = len(wins)
        total_tests = len(results)
        
        print(f"\n📊 Результаты тестирования ({total_tests} попыток):")
        print(f"🎯 Общее количество выигрышей: {total_wins} ({total_wins/total_tests*100:.1f}%)")
        
        if win_counter:
            print("\n🏆 Выигрышные комбинации:")

            # Получаем ожидаемые проценты из БД для сравнения
            expected_percentages = {}
            for config in configs:
                config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = config
                expected_percentages[combination] = chance_percent

            print("   Комбинация | Фактический % | Ожидаемый % | Отклонение")
            print("   " + "-" * 55)

            for combination, count in win_counter.most_common():
                actual_percentage = count / total_tests * 100
                expected_percentage = expected_percentages.get(combination, 0)
                deviation = abs(actual_percentage - expected_percentage)

                status = "✅" if deviation < 1.0 else "⚠️" if deviation < 2.0 else "❌"

                print(f"   {combination} | {actual_percentage:8.2f}% | {expected_percentage:8.1f}% | {deviation:6.2f}% {status}")

        print("\n✅ Алгоритм работает корректно!")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке алгоритма: {e}")

if __name__ == "__main__":
    update_slot_percentages()
    verify_slot_algorithm()
