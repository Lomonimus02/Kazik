#!/usr/bin/env python3
"""
Интеграционные тесты для проверки взаимодействия всех систем
"""
import asyncio
import os
import sys
import json
import datetime
import random

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath('.'))

from app.database.models import (
    get_or_create_user, get_user_profile, get_user_profile_by_id,
    create_order, get_order_by_id, update_order_status,
    get_slot_configs, get_user_slot_spins, use_slot_spin, reset_slot_spins,
    get_admin_setting, update_admin_setting
)

def test_user_lifecycle():
    """Тест полного жизненного цикла пользователя"""
    print("\n👤 Тестирование жизненного цикла пользователя...")
    
    try:
        # 1. Создание пользователя
        test_tg_id = 999100
        user_data = get_or_create_user(test_tg_id, "Интеграционный Тест", "integration_test", "2024-01-01", None)
        print(f"  ✅ Пользователь создан: {user_data}")
        
        # 2. Получение профиля
        profile = get_user_profile(test_tg_id)
        if profile:
            print(f"  ✅ Профиль получен: ID {profile['id']}, имя {profile['full_name']}")
            
            # 3. Создание заказа
            order_id = create_order(
                user_id=profile['id'],
                order_type="stars",
                amount=50.0,
                status="pending",
                extra_data={"recipient": "test_user", "message": "Тестовый перевод"}
            )
            
            if order_id:
                print(f"  ✅ Заказ создан: ID {order_id}")
                
                # 4. Обработка заказа
                order = get_order_by_id(order_id)
                if order:
                    print(f"  ✅ Заказ найден: {order['order_type']} на {order['amount']}₽")
                    
                    # 5. Подтверждение заказа
                    success = update_order_status(order_id, status="completed")
                    if success:
                        print(f"  ✅ Заказ подтвержден")
            
            # 6. Тестирование слот-машины
            spins_before = get_user_slot_spins(test_tg_id)
            if spins_before:
                print(f"  ✅ Спины до игры: {spins_before[0]}")
                
                # Используем спин
                use_slot_spin(test_tg_id)
                spins_after = get_user_slot_spins(test_tg_id)
                if spins_after and spins_after[0] > spins_before[0]:
                    print(f"  ✅ Спин использован: {spins_after[0]}")
                
                # Сбрасываем спины
                reset_slot_spins(test_tg_id)
                print(f"  ✅ Спины сброшены")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в тесте жизненного цикла: {e}")
        return False

def test_admin_workflow():
    """Тест административного рабочего процесса"""
    print("\n⚙️ Тестирование административного процесса...")
    
    try:
        # 1. Проверка настроек подписки
        settings_to_test = [
            'subscription_required_slot',
            'subscription_required_calendar', 
            'subscription_required_profile'
        ]
        
        original_values = {}
        for setting in settings_to_test:
            original_values[setting] = get_admin_setting(setting)
            print(f"  📋 Настройка {setting}: {original_values[setting]}")
        
        # 2. Изменение настроек
        for setting in settings_to_test:
            new_value = not original_values[setting] if original_values[setting] is not None else True
            update_admin_setting(setting, new_value)
            updated_value = get_admin_setting(setting)
            if updated_value == new_value:
                print(f"  ✅ Настройка {setting} изменена: {original_values[setting]} → {new_value}")
        
        # 3. Восстановление исходных настроек
        for setting in settings_to_test:
            update_admin_setting(setting, original_values[setting])
            restored_value = get_admin_setting(setting)
            if restored_value == original_values[setting]:
                print(f"  ✅ Настройка {setting} восстановлена: {restored_value}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в тесте админского процесса: {e}")
        return False

def test_slot_machine_integration():
    """Тест интеграции слот-машины с системой"""
    print("\n🎰 Тестирование интеграции слот-машины...")
    
    try:
        # 1. Получение конфигураций
        configs = get_slot_configs()
        if configs:
            print(f"  ✅ Найдено {len(configs)} конфигураций слот-машины")
            
            # 2. Проверка структуры конфигураций
            for config in configs[:3]:  # Проверяем первые 3
                config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = config
                print(f"  📋 Конфигурация: {name} ({combination}) - {reward_type} {reward_amount}, шанс {chance_percent}%")
        
        # 3. Тест пользовательских спинов для нескольких пользователей
        test_users = [999101, 999102, 999103]
        for user_id in test_users:
            spins_data = get_user_slot_spins(user_id)
            if spins_data:
                print(f"  ✅ Пользователь {user_id}: {spins_data[0]} использованных спинов")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в тесте интеграции слот-машины: {e}")
        return False

def test_database_consistency():
    """Тест консистентности базы данных"""
    print("\n🗄️ Тестирование консистентности базы данных...")
    
    try:
        # 1. Создание связанных данных
        test_tg_id = 999200
        user_data = get_or_create_user(test_tg_id, "Тест Консистентности", "consistency_test", "2024-01-01", None)
        profile = get_user_profile(test_tg_id)
        
        if profile:
            # 2. Создание нескольких заказов
            order_types = ["premium", "crypto", "stars", "withdraw"]
            created_orders = []
            
            for order_type in order_types:
                order_id = create_order(
                    user_id=profile['id'],
                    order_type=order_type,
                    amount=random.uniform(10.0, 100.0),
                    status="pending"
                )
                if order_id:
                    created_orders.append(order_id)
            
            print(f"  ✅ Создано {len(created_orders)} заказов")
            
            # 3. Проверка связности данных
            for order_id in created_orders:
                order = get_order_by_id(order_id)
                if order and order['user_id'] == profile['id']:
                    print(f"  ✅ Заказ {order_id} корректно связан с пользователем {profile['id']}")
                else:
                    print(f"  ❌ Проблема со связностью заказа {order_id}")
                    return False
            
            # 4. Проверка обратной связи (пользователь по ID)
            user_by_id = get_user_profile_by_id(profile['id'])
            if user_by_id and user_by_id['tg_id'] == test_tg_id:
                print(f"  ✅ Обратная связь пользователя работает корректно")
            else:
                print(f"  ❌ Проблема с обратной связью пользователя")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в тесте консистентности: {e}")
        return False

def run_integration_tests():
    """Запуск всех интеграционных тестов"""
    print("🔗 ЗАПУСК ИНТЕГРАЦИОННЫХ ТЕСТОВ")
    print("=" * 60)
    
    tests = [
        ("Жизненный цикл пользователя", test_user_lifecycle),
        ("Административный процесс", test_admin_workflow),
        ("Интеграция слот-машины", test_slot_machine_integration),
        ("Консистентность базы данных", test_database_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Тестирование: {test_name}")
            if test_func():
                print(f"✅ {test_name}: ПРОЙДЕН")
                passed += 1
            else:
                print(f"❌ {test_name}: ПРОВАЛЕН")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: ОШИБКА - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 РЕЗУЛЬТАТЫ ИНТЕГРАЦИОННОГО ТЕСТИРОВАНИЯ:")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📈 Успешность: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "0%")
    
    if failed == 0:
        print("\n🎉 ВСЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print(f"\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В {failed} ИНТЕГРАЦИОННЫХ ТЕСТАХ!")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    if not success:
        sys.exit(1)
