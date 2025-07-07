#!/usr/bin/env python3
"""
Тест вероятностей слот-машины
"""
import asyncio
import sys
import sqlite3
from collections import defaultdict

# Добавляем путь к проекту
sys.path.append('.')

from app.utils.slot_machine import generate_slot_result
from app.database.models import get_slot_configs

async def test_slot_probabilities(num_tests=1000):
    """Тестирует реальные вероятности слот-машины"""
    print(f"🎰 ТЕСТ ВЕРОЯТНОСТЕЙ СЛОТ-МАШИНЫ ({num_tests} попыток)")
    print("=" * 60)
    
    # Получаем конфигурации из БД
    configs = get_slot_configs()
    print("КОНФИГУРАЦИИ ИЗ БД:")
    total_expected_wins = 0
    for config in configs:
        config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = config
        total_expected_wins += chance_percent
        print(f"  {name:20} | {emoji} | {chance_percent:6.2f}%")
    
    print(f"\nОЖИДАЕМЫЙ ПРОЦЕНТ ВЫИГРЫШЕЙ: {total_expected_wins:.2f}%")
    print("=" * 60)
    
    # Счетчики результатов
    win_counts = defaultdict(int)
    total_wins = 0
    
    # Проводим тесты
    for i in range(num_tests):
        slot1, slot2, slot3 = await generate_slot_result()
        combination = slot1 + slot2 + slot3
        
        # Проверяем, является ли это выигрышной комбинацией
        is_win = False
        win_name = None
        
        for config in configs:
            config_id, combo, reward_type, reward_amount, chance_percent, emoji, name = config
            
            # Проверяем точное совпадение комбинации или тройку одинаковых эмодзи
            if combo == combination or (slot1 == slot2 == slot3 == emoji):
                is_win = True
                win_name = name
                win_counts[name] += 1
                total_wins += 1
                break
        
        if i % 100 == 0:
            print(f"Обработано: {i}/{num_tests}")
    
    print("\nРЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("=" * 60)
    
    actual_win_rate = (total_wins / num_tests) * 100
    print(f"ФАКТИЧЕСКИЙ ПРОЦЕНТ ВЫИГРЫШЕЙ: {actual_win_rate:.2f}%")
    print(f"ОЖИДАЕМЫЙ ПРОЦЕНТ ВЫИГРЫШЕЙ: {total_expected_wins:.2f}%")
    print(f"РАЗНИЦА: {actual_win_rate - total_expected_wins:.2f}%")
    
    print("\nДЕТАЛИЗАЦИЯ ПО ПРИЗАМ:")
    for config in configs:
        config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = config
        actual_count = win_counts[name]
        actual_percent = (actual_count / num_tests) * 100
        expected_count = int(num_tests * chance_percent / 100)
        
        print(f"  {name:20} | Ожидалось: {expected_count:3d} ({chance_percent:5.2f}%) | "
              f"Получено: {actual_count:3d} ({actual_percent:5.2f}%) | "
              f"Разница: {actual_count - expected_count:+3d}")
    
    print("=" * 60)
    
    if abs(actual_win_rate - total_expected_wins) > 2:
        print("❌ ПРОБЛЕМА: Фактический процент сильно отличается от ожидаемого!")
        return False
    else:
        print("✅ Вероятности работают корректно")
        return True

def analyze_current_logic():
    """Анализирует текущую логику генерации"""
    print("\n🔍 АНАЛИЗ ТЕКУЩЕЙ ЛОГИКИ:")
    print("=" * 60)
    
    configs = get_slot_configs()
    total_chance = sum(config[4] for config in configs)  # chance_percent
    
    print(f"Общий процент выигрышей в БД: {total_chance:.2f}%")
    print("Это означает, что из 100 попыток должно быть ~{:.0f} выигрышей".format(total_chance))
    
    if total_chance > 25:
        print("⚠️ ВНИМАНИЕ: Процент выигрышей слишком высокий для слот-машины!")
        print("   Рекомендуется снизить проценты в 2-3 раза")
    
    print("\nПРЕДЛАГАЕМЫЕ ПРОЦЕНТЫ (общий ~10%):")
    suggested_configs = [
        ('Вишни', '🍒', 5.0),
        ('Апельсин', '🍊', 2.5),
        ('Лимон', '🍋', 1.5),
        ('Виноград', '🍇', 0.5),
        ('Алмаз', '💎', 0.3),
        ('Звезды', '⭐️', 0.15),
        ('Колокольчик', '🔔', 0.08),
        ('Мешок денег', '💰', 0.05),
        ('Джекпот', '🎰', 0.02),
        ('Счастливая семерка', '7️⃣', 0.01),
    ]
    
    total_suggested = sum(config[2] for config in suggested_configs)
    for name, emoji, percent in suggested_configs:
        print(f"  {name:20} | {emoji} | {percent:6.2f}%")
    print(f"  {'ИТОГО':20} |   | {total_suggested:6.2f}%")

async def main():
    """Основная функция тестирования"""
    print("🎰 ДИАГНОСТИКА СЛОТ-МАШИНЫ")
    print("=" * 60)
    
    # Анализ логики
    analyze_current_logic()
    
    # Тест вероятностей
    success = await test_slot_probabilities(1000)
    
    if not success:
        print("\n🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
        print("1. Снизить проценты в базе данных")
        print("2. Общий процент выигрышей должен быть 8-12%")
        print("3. Самые частые призы не должны превышать 3-5%")

if __name__ == "__main__":
    asyncio.run(main())
