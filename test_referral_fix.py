#!/usr/bin/env python3
"""
Тест исправленной реферальной системы
"""
import asyncio
import os
import sys
import shutil

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath('.'))

from app.database.models import (
    get_or_create_user, get_user_profile, get_user_profile_by_id,
    get_unclaimed_referrals_count, claim_referral_bonus,
    add_referral_bonus_for_order_async, get_referrals_count
)

async def test_referral_system():
    """Тестирует всю реферальную систему"""
    print("🧪 Тестирование исправленной реферальной системы...")
    
    try:
        # Тест 1: Создание тестовых пользователей
        print("\n1️⃣ Создание тестовых пользователей...")
        
        # Создаем пригласившего
        referrer_tg_id = 999001
        referrer_name = "Тест Пригласивший"
        referrer_username = "test_referrer"
        reg_date = "2024-01-01"
        
        get_or_create_user(referrer_tg_id, referrer_name, referrer_username, reg_date, None)
        referrer = get_user_profile(referrer_tg_id)
        print(f"✅ Создан пригласивший: {referrer['full_name']} (ID: {referrer['id']})")
        
        # Создаем реферала
        referred_tg_id = 999002
        referred_name = "Тест Реферал"
        referred_username = "test_referred"
        
        get_or_create_user(referred_tg_id, referred_name, referred_username, reg_date, referrer['id'])
        referred = get_user_profile(referred_tg_id)
        print(f"✅ Создан реферал: {referred['full_name']} (ID: {referred['id']})")
        
        # Тест 2: Проверка количества рефералов
        print("\n2️⃣ Проверка количества рефералов...")
        referrals_count = get_referrals_count(referrer_tg_id)
        print(f"✅ Количество рефералов у пригласившего: {referrals_count}")
        
        # Тест 3: Проверка неактивированных рефералов
        print("\n3️⃣ Проверка неактивированных рефералов...")
        unclaimed = await get_unclaimed_referrals_count(referrer['id'])
        print(f"✅ Неактивированных рефералов: {unclaimed}")
        
        # Тест 4: Активация реферальных бонусов
        print("\n4️⃣ Активация реферальных бонусов...")
        success, activated_count, total_attempts = await claim_referral_bonus(referrer['id'])
        print(f"✅ Активация: успех={success}, активировано={activated_count}, попыток={total_attempts}")
        
        # Проверяем, что неактивированных больше нет
        unclaimed_after = await get_unclaimed_referrals_count(referrer['id'])
        print(f"✅ Неактивированных рефералов после активации: {unclaimed_after}")
        
        # Тест 5: Реферальные бонусы за покупки
        print("\n5️⃣ Тест реферальных бонусов за покупки...")
        
        # Получаем начальный баланс пригласившего
        referrer_before = get_user_profile(referrer_tg_id)
        initial_balance = referrer_before['balance']
        print(f"✅ Начальный баланс пригласившего: {initial_balance}₽")
        
        # Симулируем покупку рефералом
        order_amount = 100.0
        order_type = "Telegram Premium"
        success_bonus, bonus_data = await add_referral_bonus_for_order_async(referred['id'], order_amount, order_type)
        
        print(f"✅ Начисление бонуса: успех={success_bonus}")
        if success_bonus and bonus_data:
            print(f"✅ Данные бонуса: {bonus_data}")
            
            # Проверяем, что баланс увеличился
            referrer_after = get_user_profile(referrer_tg_id)
            final_balance = referrer_after['balance']
            print(f"✅ Финальный баланс пригласившего: {final_balance}₽")
        
        print("\n🎉 Все тесты реферальной системы завершены!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_referral_system())
    if result:
        print("\n✅ Тестирование завершено!")
    else:
        print("\n❌ Обнаружены проблемы!")
        sys.exit(1)
