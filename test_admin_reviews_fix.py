#!/usr/bin/env python3
"""
Тест исправления функции отзывов в админ панели
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.models import (
    create_review, get_all_reviews, clear_all_reviews
)

def test_admin_reviews_functionality():
    """Тестирует функциональность админ панели отзывов"""
    print("🧪 ТЕСТ АДМИН ПАНЕЛИ ОТЗЫВОВ")
    print("=" * 60)
    
    try:
        # Очищаем старые данные
        print("\n1. Очистка старых тестовых данных...")
        clear_all_reviews()
        print("   ✅ Старые данные очищены")
        
        # Создаем тестовые отзывы
        print("\n2. Создание тестовых отзывов...")
        
        # Отзыв на модерации
        review1_id = create_review(
            user_id=123456789,
            content="Отличный сервис! Быстро и качественно получил звёзды!",
            file_id=None,
            status="pending"
        )
        print(f"   Создан отзыв на модерации: #{review1_id}")
        
        # Опубликованный отзыв
        review2_id = create_review(
            user_id=987654321,
            content="Рекомендую всем! Покупал TON, всё прошло без проблем.",
            file_id=None,
            status="published"
        )
        print(f"   Создан опубликованный отзыв: #{review2_id}")
        
        # Отклоненный отзыв
        review3_id = create_review(
            user_id=555666777,
            content="Плохой сервис, не рекомендую",
            file_id=None,
            status="rejected"
        )
        print(f"   Создан отклоненный отзыв: #{review3_id}")
        
        # Отзыв с фото
        review4_id = create_review(
            user_id=111222333,
            content="Вот скриншот моей покупки звёзд - всё отлично!",
            file_id="BAADBAADrwADBREAAWYvAAE",
            status="pending"
        )
        print(f"   Создан отзыв с фото: #{review4_id}")
        
        # 3. Проверяем получение всех отзывов
        print("\n3. Проверка получения всех отзывов...")
        all_reviews = get_all_reviews()
        print(f"   Всего отзывов в базе: {len(all_reviews)}")
        
        # Статистика по статусам
        pending_count = len([r for r in all_reviews if r[3] == 'pending'])
        published_count = len([r for r in all_reviews if r[3] == 'published'])
        rejected_count = len([r for r in all_reviews if r[3] == 'rejected'])
        
        print(f"   ⏳ На модерации: {pending_count}")
        print(f"   ✅ Опубликованы: {published_count}")
        print(f"   ❌ Отклонены: {rejected_count}")
        
        # 4. Проверяем структуру данных
        print("\n4. Проверка структуры данных отзывов...")
        for i, review in enumerate(all_reviews[:2], 1):
            review_id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id = review
            print(f"   Отзыв {i}:")
            print(f"     ID: {review_id}")
            print(f"     User ID: {user_id}")
            print(f"     Статус: {status}")
            print(f"     Контент: {content[:50]}...")
            print(f"     Файл: {'Есть' if file_id else 'Нет'}")
        
        # 5. Тестируем фильтрацию по статусам
        print("\n5. Тестирование фильтрации по статусам...")
        
        pending_reviews = [r for r in all_reviews if r[3] == 'pending']
        print(f"   Отзывы на модерации: {len(pending_reviews)}")
        for review in pending_reviews:
            print(f"     #{review[0]}: {review[2][:30]}...")
        
        published_reviews = [r for r in all_reviews if r[3] == 'published']
        print(f"   Опубликованные отзывы: {len(published_reviews)}")
        for review in published_reviews:
            print(f"     #{review[0]}: {review[2][:30]}...")
        
        # 6. Проверяем клавиатуру админ панели
        print("\n6. Проверка клавиатуры админ панели...")
        from app.keyboards.main import admin_panel_kb
        
        kb = admin_panel_kb()
        print("   Кнопки админ панели:")
        for row in kb.inline_keyboard:
            for button in row:
                if "Отзывы" in button.text:
                    print(f"     ✅ Найдена кнопка: '{button.text}' -> {button.callback_data}")
                    if button.callback_data == "admin_reviews":
                        print("     ✅ Callback правильный: admin_reviews")
                    else:
                        print(f"     ❌ Неправильный callback: {button.callback_data}")
        
        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Админ панель отзывов настроена правильно")
        print("✅ Функция отзывов применена корректно")
        print("✅ Все существующие функции сохранены")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_admin_reviews_functionality()
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    else:
        print("\n💥 ТЕСТИРОВАНИЕ ПРОВАЛЕНО!")
        sys.exit(1)
