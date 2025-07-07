#!/usr/bin/env python3
"""
Тест функций статистики и призов слот-машины
"""
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.models import get_slot_wins_async, get_slot_configs

async def test_slot_functions():
    """Тестирует функции статистики и призов"""
    print("🧪 ТЕСТ ФУНКЦИЙ СЛОТ-МАШИНЫ")
    print("=" * 60)
    
    try:
        # Тест 1: Получение конфигураций слот-машины
        print("\n1. Тест get_slot_configs():")
        configs = get_slot_configs()
        print(f"   Найдено конфигураций: {len(configs)}")
        for config in configs[:3]:  # Показываем первые 3
            print(f"   - {config[1]} ({config[6]}): {config[3]}% шанс, {config[4]} {config[2]}")
        
        # Тест 2: Получение выигрышей пользователя (тестовый ID)
        print("\n2. Тест get_slot_wins_async(user_id=123456789):")
        test_user_id = 123456789  # Тестовый ID
        wins = await get_slot_wins_async(user_id=test_user_id)
        print(f"   Найдено записей для пользователя {test_user_id}: {len(wins)}")
        
        # Тест 3: Получение всех выигрышей
        print("\n3. Тест get_slot_wins_async() (все записи):")
        all_wins = await get_slot_wins_async()
        print(f"   Всего записей в БД: {len(all_wins)}")
        
        if all_wins:
            print("   Структура записи:")
            sample = all_wins[0]
            print(f"   - ID: {sample[0]}")
            print(f"   - User ID: {sample[1]}")
            print(f"   - TG ID: {sample[2]}")
            print(f"   - Full Name: {sample[3]}")
            print(f"   - Combination: {sample[4]}")
            print(f"   - Reward Type: {sample[5]}")
            print(f"   - Reward Amount: {sample[6]}")
            print(f"   - Is Win: {sample[7]}")
            print(f"   - Created At: {sample[8]}")
            print(f"   - Status: {sample[9]}")
        
        # Тест 4: Фильтрация выигрышей
        if all_wins:
            print("\n4. Тест фильтрации выигрышей:")
            actual_wins = [win for win in all_wins if win[7] == True]  # is_win = True
            print(f"   Реальных выигрышей: {len(actual_wins)}")
            
            money_wins = [win for win in actual_wins if win[5] == "money"]
            stars_wins = [win for win in actual_wins if win[5] == "stars"]
            ton_wins = [win for win in actual_wins if win[5] == "ton"]
            
            print(f"   - Денежных выигрышей: {len(money_wins)}")
            print(f"   - Звездных выигрышей: {len(stars_wins)}")
            print(f"   - TON выигрышей: {len(ton_wins)}")
        
        print("\n✅ Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_slot_functions())
