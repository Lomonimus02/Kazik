#!/usr/bin/env python3
"""
Тест размера рамки слот-машины
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.slot_machine import CENTERED_FRAME, format_slot_result

def test_frame_size():
    """Тестирует размер рамки слот-машины"""
    print("🎰 ТЕСТ РАЗМЕРА РАМКИ СЛОТ-МАШИНЫ")
    print("=" * 50)
    
    # Тестируем рамку с разными эмодзи
    frame = CENTERED_FRAME.format(s1="🍋", s2="💎", s3="🎰")
    print("Текущая рамка:")
    print(frame)
    print()
    
    # Проверяем длину строк
    lines = frame.split('\n')
    print("Анализ размера:")
    for i, line in enumerate(lines):
        print(f"Строка {i+1}: '{line}' (длина: {len(line)})")
    
    # Проверяем, что рамка компактная
    max_length = max(len(line) for line in lines)
    print(f"\nМаксимальная длина строки: {max_length}")
    
    if max_length <= 12:  # Компактная рамка
        print("✅ Рамка компактная и точно по размеру")
    else:
        print("❌ Рамка слишком большая")
    
    # Тестируем в контексте полного сообщения
    print("\n" + "=" * 50)
    print("ТЕСТ В КОНТЕКСТЕ ПОЛНОГО СООБЩЕНИЯ:")
    
    result = format_slot_result(
        slot1="🍊", slot2="🍊", slot3="🍊", 
        is_win=True, 
        reward_text="10₽", 
        prize_name="Апельсин", 
        reward_type="money"
    )
    print(result)

if __name__ == '__main__':
    test_frame_size()
