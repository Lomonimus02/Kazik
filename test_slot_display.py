#!/usr/bin/env python3
"""
Тест отображения слот-машины для поиска проблемы с 6 символами
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.slot_machine import format_slot_result

def test_slot_display():
    """Тестирует отображение результатов слот-машины"""
    print("🎰 ТЕСТ ОТОБРАЖЕНИЯ СЛОТ-МАШИНЫ")
    print("=" * 60)
    
    # Тестируем выигрышную комбинацию
    result = format_slot_result(
        slot1="🍊", slot2="🍊", slot3="🍊", 
        is_win=True, 
        reward_text="10₽", 
        prize_name="Апельсин", 
        reward_type="money"
    )
    
    print("РЕЗУЛЬТАТ ФУНКЦИИ format_slot_result:")
    print(result)
    print("\n" + "=" * 60)
    
    # Проверяем, сколько символов 🍊 в строке "Комбинация"
    lines = result.split('\n')
    for line in lines:
        if 'Комбинация:' in line:
            print(f"СТРОКА С КОМБИНАЦИЕЙ: {line}")
            orange_count = line.count('🍊')
            print(f"КОЛИЧЕСТВО СИМВОЛОВ 🍊: {orange_count}")
            if orange_count != 3:
                print(f"❌ ОШИБКА: Ожидалось 3 символа, найдено {orange_count}")
            else:
                print("✅ Количество символов корректно")
            break
    
    # Тестируем проигрышную комбинацию
    print("\n" + "=" * 60)
    print("ТЕСТ ПРОИГРЫШНОЙ КОМБИНАЦИИ:")
    
    result2 = format_slot_result(
        slot1="🍒", slot2="🍋", slot3="🍊", 
        is_win=False
    )
    
    print(result2)

if __name__ == '__main__':
    test_slot_display()
