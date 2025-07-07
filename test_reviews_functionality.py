#!/usr/bin/env python3
"""
Тест функциональности отзывов
"""
import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.models import (
    create_review, get_review_by_id, get_all_reviews, 
    update_review_status, delete_review, clear_all_reviews
)

def test_reviews_system():
    """Тестирует систему отзывов"""
    print("🧪 ТЕСТ СИСТЕМЫ ОТЗЫВОВ")
    print("=" * 60)
    
    try:
        # 1. Создание отзыва
        print("\n1. Создание тестового отзыва...")
        review_id = create_review(
            user_id=123456789,
            content="Отличный сервис! Быстро и качественно!",
            file_id=None,
            status="pending"
        )
        print(f"   Отзыв создан с ID: {review_id}")
        
        # 2. Получение отзыва по ID
        print("\n2. Получение отзыва по ID...")
        review = get_review_by_id(review_id)
        if review:
            print(f"   Отзыв найден: {review['content'][:50]}...")
            print(f"   Статус: {review['status']}")
        else:
            print("   ❌ Отзыв не найден")
            return
        
        # 3. Обновление статуса отзыва
        print("\n3. Обновление статуса отзыва...")
        update_review_status(review_id, status="published")
        updated_review = get_review_by_id(review_id)
        if updated_review and updated_review['status'] == 'published':
            print("   ✅ Статус успешно обновлен на 'published'")
        else:
            print("   ❌ Ошибка обновления статуса")
        
        # 4. Получение всех отзывов
        print("\n4. Получение всех отзывов...")
        all_reviews = get_all_reviews()
        print(f"   Всего отзывов в БД: {len(all_reviews)}")
        
        # 5. Проверка структуры таблицы
        print("\n5. Проверка структуры таблицы reviews...")
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(reviews)")
        columns = cursor.fetchall()
        print("   Колонки таблицы:")
        for col in columns:
            print(f"     - {col[1]} ({col[2]})")
        
        # 6. Проверка данных в таблице
        cursor.execute("SELECT COUNT(*) FROM reviews")
        count = cursor.fetchone()[0]
        print(f"   Записей в таблице: {count}")
        
        conn.close()
        
        # 7. Удаление тестового отзыва
        print("\n6. Удаление тестового отзыва...")
        delete_review(review_id)
        deleted_review = get_review_by_id(review_id)
        if not deleted_review:
            print("   ✅ Отзыв успешно удален")
        else:
            print("   ❌ Ошибка удаления отзыва")
        
        print("\n✅ Тест системы отзывов ЗАВЕРШЕН!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reviews_system()
