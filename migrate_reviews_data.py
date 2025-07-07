#!/usr/bin/env python3
"""
Миграция данных отзывов из колонки text в content
"""
import sqlite3

def migrate_reviews_data():
    """Мигрирует данные из text в content и удаляет дублирующую колонку"""
    print("🔄 МИГРАЦИЯ ДАННЫХ ОТЗЫВОВ")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        
        # Проверяем наличие данных в колонке text
        cursor.execute("SELECT id, text, content FROM reviews WHERE text IS NOT NULL AND text != ''")
        text_data = cursor.fetchall()
        
        print(f"Найдено записей с данными в колонке 'text': {len(text_data)}")
        
        # Мигрируем данные из text в content, если content пустой
        migrated = 0
        for review_id, text_content, current_content in text_data:
            if not current_content or current_content.strip() == '':
                cursor.execute("UPDATE reviews SET content = ? WHERE id = ?", (text_content, review_id))
                migrated += 1
                print(f"  Мигрирована запись {review_id}: {text_content[:50]}...")
        
        print(f"Мигрировано записей: {migrated}")
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM reviews WHERE content IS NOT NULL AND content != ''")
        content_count = cursor.fetchone()[0]
        print(f"Записей с данными в 'content': {content_count}")
        
        conn.commit()
        conn.close()
        
        print("✅ Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    migrate_reviews_data()
