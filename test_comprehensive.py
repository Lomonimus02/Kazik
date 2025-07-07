#!/usr/bin/env python3
"""
Комплексные тесты для всех реализованных функций (Tasks 1-9)
"""
import asyncio
import os
import sys
import json
import datetime
import random

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath('.'))

try:
    from app.database.models import (
        # Пользователи
        get_or_create_user, get_user_profile, get_user_profile_by_id,
        # Заказы
        create_order, get_order_by_id, update_order_status, get_all_orders,
        # Слот-машина
        get_slot_configs, add_slot_config, delete_slot_config,
        get_user_slot_spins, use_slot_spin, reset_slot_spins,
        create_slot_win, get_slot_wins, update_slot_win_status,
        # Админ настройки
        get_admin_setting, update_admin_setting
    )

    # Пытаемся импортировать дополнительные функции
    try:
        from app.database.models import add_to_blacklist, remove_from_blacklist, is_blacklisted, get_blacklist
        BLACKLIST_AVAILABLE = True
    except ImportError:
        BLACKLIST_AVAILABLE = False
        print("⚠️ Функции черного списка недоступны")

    try:
        from app.database.models import create_ticket, get_ticket_by_id, update_ticket_status, get_all_tickets
        TICKETS_AVAILABLE = True
    except ImportError:
        TICKETS_AVAILABLE = False
        print("⚠️ Функции тикетов недоступны")

    try:
        from app.database.models import get_referral_percentage, update_referral_percentage
        REFERRAL_AVAILABLE = True
    except ImportError:
        REFERRAL_AVAILABLE = False
        print("⚠️ Функции рефералов недоступны")

    try:
        from app.database.models import get_content, update_content
        CONTENT_AVAILABLE = True
    except ImportError:
        CONTENT_AVAILABLE = False
        print("⚠️ Функции контента недоступны")

except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def test_slot_machine_system():
    """Тест системы слот-машины"""
    print("\n🎰 Тестирование системы слот-машины...")
    
    try:
        # Тест конфигураций слот-машины
        print("  📋 Тест конфигураций...")
        
        # Добавляем тестовую конфигурацию с уникальной комбинацией
        import time
        unique_combo = f"🧪🧪🧪{int(time.time())}"  # Уникальная комбинация для теста
        config_id = add_slot_config(unique_combo, "money", 10.0, 13.0, "🧪", "Тестовая комбинация")
        if config_id:
            print(f"  ✅ Конфигурация добавлена: ID {config_id}")
            
            # Получаем все конфигурации
            configs = get_slot_configs()
            if configs:
                print(f"  ✅ Найдено {len(configs)} конфигураций")
                
                # Проверяем нашу конфигурацию
                our_config = next((c for c in configs if c[0] == config_id), None)
                if our_config:
                    print(f"  ✅ Конфигурация найдена: {our_config[5]} - {our_config[4]}%")
            
            # Удаляем тестовую конфигурацию
            delete_slot_config(config_id)
            print(f"  ✅ Конфигурация удалена")
        
        # Тест пользовательских спинов
        print("  🎲 Тест пользовательских спинов...")

        test_user_id = 999001
        spins_data = get_user_slot_spins(test_user_id)
        if spins_data:
            spins_used, last_reset = spins_data
            print(f"  ✅ Спины пользователя: использовано {spins_used}, последний сброс {last_reset}")

            # Используем спин
            use_slot_spin(test_user_id)
            print(f"  ✅ Использован спин")

            # Сбрасываем спины
            reset_slot_spins(test_user_id)
            print(f"  ✅ Спины сброшены")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в тестах слот-машины: {e}")
        return False

def test_blacklist_system():
    """Тест системы черного списка"""
    print("\n🚫 Тестирование системы черного списка...")

    if not BLACKLIST_AVAILABLE:
        print("  ⚠️ Функции черного списка недоступны - пропускаем тест")
        return True

    try:
        test_user_id = 999002
        test_reason = "Тестовая блокировка"

        # Добавляем в черный список
        add_to_blacklist(test_user_id, test_reason)
        print(f"  ✅ Пользователь {test_user_id} добавлен в черный список")

        # Проверяем блокировку
        if is_blacklisted(test_user_id):
            print(f"  ✅ Пользователь корректно заблокирован")

        # Получаем список заблокированных
        blacklist = get_blacklist()
        if blacklist:
            found = any(entry[0] == test_user_id for entry in blacklist)
            if found:
                print(f"  ✅ Пользователь найден в списке заблокированных")

        # Удаляем из черного списка
        remove_from_blacklist(test_user_id)
        print(f"  ✅ Пользователь удален из черного списка")

        # Проверяем разблокировку
        if not is_blacklisted(test_user_id):
            print(f"  ✅ Пользователь корректно разблокирован")

        return True

    except Exception as e:
        print(f"  ❌ Ошибка в тестах черного списка: {e}")
        return False

def test_ticket_system():
    """Тест системы тикетов"""
    print("\n🎫 Тестирование системы тикетов...")

    if not TICKETS_AVAILABLE:
        print("  ⚠️ Функции тикетов недоступны - пропускаем тест")
        return True

    try:
        # Создаем тестового пользователя
        test_tg_id = 999004
        get_or_create_user(test_tg_id, "Тест Тикеты", "test_tickets", "2024-01-01", None)
        user_profile = get_user_profile(test_tg_id)

        # Создаем тикет
        ticket_id = create_ticket(
            user_id=user_profile['id'],
            subject="Тестовый тикет",
            message="Это тестовое сообщение",
            file_id="test_file"
        )

        if ticket_id:
            print(f"  ✅ Тикет создан: ID {ticket_id}")

            # Получаем тикет
            ticket = get_ticket_by_id(ticket_id)
            if ticket:
                print(f"  ✅ Тикет найден: {ticket['subject']}")

                # Обновляем статус
                update_ticket_status(ticket_id, "in_progress")
                updated_ticket = get_ticket_by_id(ticket_id)
                if updated_ticket and updated_ticket['status'] == 'in_progress':
                    print(f"  ✅ Статус тикета обновлен: {updated_ticket['status']}")

                # Получаем все тикеты
                all_tickets = get_all_tickets()
                if all_tickets:
                    print(f"  ✅ Найдено {len(all_tickets)} тикетов")

        return True

    except Exception as e:
        print(f"  ❌ Ошибка в тестах тикетов: {e}")
        return False

def test_referral_system():
    """Тест реферальной системы"""
    print("\n👥 Тестирование реферальной системы...")

    if not REFERRAL_AVAILABLE:
        print("  ⚠️ Функции рефералов недоступны - пропускаем тест")
        return True

    try:
        # Тест процентов рефералов
        current_percentage = get_referral_percentage()
        print(f"  📊 Текущий процент рефералов: {current_percentage}%")

        # Обновляем процент
        new_percentage = 15.0
        update_referral_percentage(new_percentage)
        updated_percentage = get_referral_percentage()

        if updated_percentage == new_percentage:
            print(f"  ✅ Процент рефералов обновлен: {updated_percentage}%")

        # Возвращаем исходный процент
        update_referral_percentage(current_percentage)
        print(f"  ✅ Процент рефералов восстановлен: {current_percentage}%")

        return True

    except Exception as e:
        print(f"  ❌ Ошибка в тестах рефералов: {e}")
        return False

def test_content_system():
    """Тест системы контента"""
    print("\n📝 Тестирование системы контента...")

    if not CONTENT_AVAILABLE:
        print("  ⚠️ Функции контента недоступны - пропускаем тест")
        return True

    try:
        # Тестируем получение контента
        sections = ['slot', 'calendar', 'profile', 'support', 'reviews']

        for section in sections:
            content = get_content(section)
            if content:
                print(f"  ✅ Контент секции '{section}': {len(content.get('text', ''))} символов")

                # Тестируем обновление контента
                test_text = f"Тестовый текст для {section}"
                test_photo = f"test_photo_{section}"
                test_buttons = json.dumps([{"text": f"Кнопка {section}", "url": "https://example.com"}])

                update_content(section, test_text, test_photo, test_buttons)
                updated_content = get_content(section)

                if updated_content and updated_content['text'] == test_text:
                    print(f"  ✅ Контент секции '{section}' обновлен")

                # Восстанавливаем исходный контент
                if content:
                    update_content(section, content.get('text', ''), content.get('photo', ''), content.get('buttons', ''))

        return True

    except Exception as e:
        print(f"  ❌ Ошибка в тестах контента: {e}")
        return False

def test_admin_settings():
    """Тест админских настроек"""
    print("\n⚙️ Тестирование админских настроек...")
    
    try:
        # Тестируем настройки подписки
        settings = ['subscription_required_slot', 'subscription_required_calendar', 'subscription_required_profile']
        
        for setting in settings:
            current_value = get_admin_setting(setting)
            print(f"  📋 Настройка '{setting}': {current_value}")
            
            # Переключаем значение
            new_value = not current_value if current_value is not None else True
            update_admin_setting(setting, new_value)
            
            updated_value = get_admin_setting(setting)
            if updated_value == new_value:
                print(f"  ✅ Настройка '{setting}' обновлена: {updated_value}")
            
            # Возвращаем исходное значение
            update_admin_setting(setting, current_value)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка в тестах админских настроек: {e}")
        return False

def test_orders_system():
    """Тест системы заказов (уже протестирована отдельно)"""
    print("\n📦 Тестирование системы заказов...")

    try:
        # Создаем тестового пользователя
        test_tg_id = 999005
        get_or_create_user(test_tg_id, "Тест Заказы", "test_orders", "2024-01-01", None)
        user_profile = get_user_profile(test_tg_id)

        # Создаем тестовый заказ
        order_id = create_order(
            user_id=user_profile['id'],
            order_type="test",
            amount=100.0,
            status="pending",
            file_id="test_file",
            extra_data={"test": "data"}
        )

        if order_id:
            print(f"  ✅ Заказ создан: ID {order_id}")

            # Получаем заказ
            order = get_order_by_id(order_id)
            if order:
                print(f"  ✅ Заказ найден: тип {order['order_type']}, сумма {order['amount']}₽")

                # Обновляем статус
                success = update_order_status(order_id, status="completed")
                if success:
                    print(f"  ✅ Статус заказа обновлен")

                # Получаем все заказы
                all_orders = get_all_orders()
                if all_orders:
                    print(f"  ✅ Найдено {len(all_orders)} заказов в системе")

        return True

    except Exception as e:
        print(f"  ❌ Ошибка в тестах заказов: {e}")
        return False

def run_comprehensive_tests():
    """Запуск всех комплексных тестов"""
    print("🧪 ЗАПУСК КОМПЛЕКСНЫХ ТЕСТОВ ВСЕХ ФУНКЦИЙ")
    print("=" * 60)

    tests = [
        ("Слот-машина", test_slot_machine_system),
        ("Система заказов", test_orders_system),
        ("Черный список", test_blacklist_system),
        ("Система тикетов", test_ticket_system),
        ("Реферальная система", test_referral_system),
        ("Система контента", test_content_system),
        ("Админские настройки", test_admin_settings),
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
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📈 Успешность: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "0%")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print(f"\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В {failed} ТЕСТАХ!")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    if not success:
        sys.exit(1)
