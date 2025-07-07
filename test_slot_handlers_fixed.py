#!/usr/bin/env python3
"""
Тест исправленных обработчиков статистики и призов слот-машины
"""
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.models import get_slot_wins_async, get_slot_configs

async def test_fixed_handlers():
    """Тестирует логику исправленных обработчиков"""
    print("🧪 ТЕСТ ИСПРАВЛЕННЫХ ОБРАБОТЧИКОВ")
    print("=" * 60)
    
    try:
        # Получаем все выигрыши
        all_wins = await get_slot_wins_async()
        print(f"Всего записей в БД: {len(all_wins)}")
        
        if not all_wins:
            print("❌ Нет данных для тестирования")
            return
        
        # Тестируем логику my_prizes_handler
        print("\n📊 ТЕСТ MY_PRIZES_HANDLER:")
        
        # Берем первого пользователя с данными
        test_user_id = all_wins[0][2]  # tg_id
        print(f"Тестируем пользователя: {test_user_id}")
        
        user_wins = await get_slot_wins_async(user_id=test_user_id)
        print(f"Записей пользователя: {len(user_wins)}")
        
        # Фильтруем выигрыши (исправленная логика)
        actual_wins = [win for win in user_wins if win[7] in (True, 1)]
        print(f"Реальных выигрышей: {len(actual_wins)}")
        
        if actual_wins:
            print("Примеры выигрышей:")
            for win in actual_wins[:3]:  # Первые 3
                combination = win[4]
                reward_type = win[5]
                reward_amount = win[6]
                is_win = win[7]
                status = win[9] if len(win) > 9 else "pending"
                
                if reward_type == "money":
                    reward_text = f"{int(reward_amount)}₽"
                    status_text = "✅ Зачислено"
                elif reward_type == "stars":
                    reward_text = f"{int(reward_amount)}⭐️"
                    status_text = "✅ Зачислено" if status == "completed" else "⏳ Ожидает подтверждения"
                elif reward_type == "ton":
                    reward_text = f"{reward_amount} TON"
                    status_text = "✅ Зачислено" if status == "completed" else "⏳ Ожидает подтверждения"
                else:
                    reward_text = str(reward_amount)
                    status_text = "✅ Зачислено" if status == "completed" else "⏳ Ожидает подтверждения"
                
                print(f"  - {combination}: {reward_text} ({status_text})")
        
        # Тестируем логику slot_stats_handler
        print("\n📈 ТЕСТ SLOT_STATS_HANDLER:")
        
        total_spins = len(user_wins)
        winning_spins = len([win for win in user_wins if win[7] in (True, 1)])
        
        print(f"Всего вращений: {total_spins}")
        print(f"Выигрышных вращений: {winning_spins}")
        
        # Находим самый крупный выигрыш
        biggest_win = 0
        biggest_win_type = ""
        for win in user_wins:
            if win[7] in (True, 1):  # Если выигрыш
                reward_amount = win[6]
                reward_type = win[5]
                
                # Конвертируем в условные единицы для сравнения
                if reward_type == "money":
                    value = reward_amount
                elif reward_type == "stars":
                    value = reward_amount * 2
                elif reward_type == "ton":
                    value = reward_amount * 1000
                else:
                    value = 0
                
                if value > biggest_win:
                    biggest_win = value
                    if reward_type == "money":
                        biggest_win_type = f"{reward_amount}₽"
                    elif reward_type == "stars":
                        biggest_win_type = f"{reward_amount}⭐️"
                    elif reward_type == "ton":
                        biggest_win_type = f"{reward_amount} TON"
        
        win_rate = (winning_spins / total_spins * 100) if total_spins > 0 else 0
        
        print(f"Процент выигрышей: {win_rate:.1f}%")
        print(f"Самый крупный выигрыш: {biggest_win_type if biggest_win_type else 'Нет выигрышей'}")
        
        print("\n✅ Тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_handlers())
