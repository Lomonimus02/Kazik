#!/usr/bin/env python3
"""
Тесты генерации результатов слот-машины
"""
import sys
import os
import asyncio
import random
from collections import Counter
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Мокаем функции БД
def mock_get_slot_configs():
    return [
        (1, '🍒🍒🍒', 'money', 5, 20.0, '🍒', 'Вишни'),
        (2, '🍋🍋🍋', 'money', 10, 15.0, '🍋', 'Лимон'),
        (3, '🍇🍇🍇', 'stars', 13, 5.0, '🍇', 'Виноград'),
        (4, '🍊🍊🍊', 'stars', 21, 7.0, '🍊', 'Апельсин'),
        (5, '💎💎💎', 'ton', 0.5, 1.0, '💎', 'Алмаз'),
        (6, '⭐️⭐️⭐️', 'stars', 50, 0.7, '⭐️', 'Звезды'),
        (7, '🔔🔔🔔', 'money', 100, 0.4, '🔔', 'Колокольчик'),
        (8, '💰💰💰', 'stars', 75, 0.3, '💰', 'Мешок денег'),
        (9, '🎰🎰🎰', 'ton', 1.0, 0.1, '🎰', 'Джекпот'),
        (10, '7️⃣7️⃣7️⃣', 'stars', 100, 0.05, '7️⃣', 'Счастливая семерка'),
    ]

# Патчим импорты
with patch.dict('sys.modules', {
    'app.database.models': MagicMock(),
    'app.keyboards.main': MagicMock(),
    'app.utils.misc': MagicMock()
}):
    # Импортируем после патчинга
    from app.utils.slot_machine import generate_slot_result, check_win_combination

async def test_generate_slot_result_distribution():
    """Тестирует распределение результатов генерации слот-машины"""
    print("🎰 Тестирование генерации результатов слот-машины")
    print("=" * 60)
    
    # Патчим get_slot_configs
    with patch('app.utils.slot_machine.get_slot_configs', mock_get_slot_configs):
        # Генерируем большое количество результатов
        num_tests = 10000
        results = []
        
        print(f"Генерируем {num_tests} результатов...")
        
        for i in range(num_tests):
            if i % 1000 == 0:
                print(f"Прогресс: {i}/{num_tests}")
            
            slot1, slot2, slot3 = await generate_slot_result()
            combination = slot1 + slot2 + slot3
            results.append(combination)
        
        # Анализируем результаты
        counter = Counter(results)
        
        print("\n📊 Результаты анализа:")
        print("-" * 60)
        
        # Ожидаемые проценты
        expected_combinations = {
            '🍒🍒🍒': 20.0,
            '🍋🍋🍋': 15.0,
            '🍇🍇🍇': 5.0,
            '🍊🍊🍊': 7.0,
            '💎💎💎': 1.0,
            '⭐️⭐️⭐️': 0.7,
            '🔔🔔🔔': 0.4,
            '💰💰💰': 0.3,
            '🎰🎰🎰': 0.1,
            '7️⃣7️⃣7️⃣': 0.05,
        }
        
        total_wins = 0
        issues = []
        
        for combo, expected_percent in expected_combinations.items():
            actual_count = counter.get(combo, 0)
            actual_percent = (actual_count / num_tests) * 100
            total_wins += actual_count
            
            # Допустимое отклонение (±2% для больших процентов, ±0.5% для малых)
            tolerance = 2.0 if expected_percent >= 5.0 else 0.5
            
            status = "✅" if abs(actual_percent - expected_percent) <= tolerance else "❌"
            
            print(f"{combo} | Ожидалось: {expected_percent:5.2f}% | Получено: {actual_percent:5.2f}% | {status}")
            
            if abs(actual_percent - expected_percent) > tolerance:
                issues.append(f"Комбинация {combo}: отклонение {actual_percent - expected_percent:+.2f}%")
        
        # Общая статистика
        total_win_percent = (total_wins / num_tests) * 100
        expected_total = sum(expected_combinations.values())
        
        print("-" * 60)
        print(f"Общий процент выигрышей: {total_win_percent:.2f}% (ожидалось {expected_total:.2f}%)")
        print(f"Процент проигрышей: {100 - total_win_percent:.2f}%")
        
        # Проверяем наиболее частые проигрышные комбинации
        losing_combos = {k: v for k, v in counter.items() if k not in expected_combinations}
        if losing_combos:
            print(f"\nТоп-5 проигрышных комбинаций:")
            for combo, count in sorted(losing_combos.items(), key=lambda x: x[1], reverse=True)[:5]:
                percent = (count / num_tests) * 100
                print(f"  {combo}: {count} раз ({percent:.2f}%)")
        
        print("\n" + "=" * 60)
        if issues:
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В РАСПРЕДЕЛЕНИИ:")
            for issue in issues:
                print(f"  {issue}")
            return False
        else:
            print("✅ Распределение результатов соответствует ожиданиям")
            return True

async def test_check_win_combination():
    """Тестирует функцию проверки выигрышных комбинаций"""
    print("\n🔍 Тестирование проверки выигрышных комбинаций")
    print("=" * 60)
    
    with patch('app.utils.slot_machine.get_slot_configs', mock_get_slot_configs):
        test_cases = [
            # Выигрышные комбинации
            ('🍒', '🍒', '🍒', True, 'money', 5),
            ('🍋', '🍋', '🍋', True, 'money', 10),
            ('🍇', '🍇', '🍇', True, 'stars', 13),
            ('🍊', '🍊', '🍊', True, 'stars', 21),
            ('💎', '💎', '💎', True, 'ton', 0.5),
            ('⭐️', '⭐️', '⭐️', True, 'stars', 50),
            ('🔔', '🔔', '🔔', True, 'money', 100),
            ('💰', '💰', '💰', True, 'stars', 75),
            ('🎰', '🎰', '🎰', True, 'ton', 1.0),
            ('7️⃣', '7️⃣', '7️⃣', True, 'stars', 100),
            
            # Проигрышные комбинации
            ('🍒', '🍋', '🍊', False, None, None),
            ('🍇', '💎', '🔔', False, None, None),
            ('🎰', '7️⃣', '🍒', False, None, None),
            ('⭐️', '🍋', '💰', False, None, None),
        ]
        
        issues = []
        
        for slot1, slot2, slot3, should_win, expected_type, expected_amount in test_cases:
            result = await check_win_combination(slot1, slot2, slot3)
            
            if should_win:
                if result is None:
                    issues.append(f"❌ {slot1}{slot2}{slot3} должна быть выигрышной, но не распознана")
                else:
                    _, _, reward_type, reward_amount, _, _, _ = result
                    if reward_type != expected_type or reward_amount != expected_amount:
                        issues.append(f"❌ {slot1}{slot2}{slot3}: ожидалось {expected_type} {expected_amount}, получено {reward_type} {reward_amount}")
                    else:
                        print(f"✅ {slot1}{slot2}{slot3} -> {reward_type} {reward_amount}")
            else:
                if result is not None:
                    issues.append(f"❌ {slot1}{slot2}{slot3} должна быть проигрышной, но распознана как выигрышная")
                else:
                    print(f"✅ {slot1}{slot2}{slot3} -> проигрыш")
        
        print("\n" + "=" * 60)
        if issues:
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В ПРОВЕРКЕ КОМБИНАЦИЙ:")
            for issue in issues:
                print(f"  {issue}")
            return False
        else:
            print("✅ Проверка выигрышных комбинаций работает корректно")
            return True

async def main():
    """Запускает все тесты"""
    print("🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ СЛОТ-МАШИНЫ")
    print("=" * 80)
    
    # Устанавливаем seed для воспроизводимости
    random.seed(42)
    
    test1_passed = await test_generate_slot_result_distribution()
    test2_passed = await test_check_win_combination()
    
    print("\n" + "=" * 80)
    print("📋 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    
    if test1_passed and test2_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        return True
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        return False

if __name__ == "__main__":
    asyncio.run(main())
