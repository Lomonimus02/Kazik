#!/usr/bin/env python3
"""
Скрипт для обновления шансов слот-машины
Уменьшает все шансы кроме вишен в 10 раз
"""
import sqlite3
import os
import sys

# Добавляем путь к проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.chdir(current_dir)

def update_slot_chances():
    """Обновляет шансы в базе данных"""
    try:
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        
        print("🎰 Обновление шансов слот-машины...")
        
        # Новые конфигурации (шансы уменьшены в 10 раз кроме вишен)
        new_configs = [
            ('🍒🍒🍒', 'money', 5, 0.8, '🍒', 'Вишни'),           # 0.8% - 5₽ (НЕ ИЗМЕНЕНО)
            ('🍊🍊🍊', 'money', 10, 0.06, '🍊', 'Апельсин'),      # 0.06% - 10₽ (было 0.6%)
            ('🍋🍋🍋', 'stars', 13, 0.03, '🍋', 'Лимон'),         # 0.03% - 13⭐ (было 0.3%)
            ('🍇🍇🍇', 'stars', 21, 0.015, '🍇', 'Виноград'),     # 0.015% - 21⭐ (было 0.15%)
            ('💎💎💎', 'ton', 0.5, 0.008, '💎', 'Алмаз'),         # 0.008% - 0.5 TON (было 0.08%)
            ('⭐️⭐️⭐️', 'stars', 50, 0.003, '⭐️', 'Звезды'),      # 0.003% - 50⭐ (было 0.03%)
            ('🔔🔔🔔', 'money', 100, 0.002, '🔔', 'Колокольчик'), # 0.002% - 100₽ (было 0.02%)
            ('💰💰💰', 'stars', 75, 0.0008, '💰', 'Мешок денег'), # 0.0008% - 75⭐ (было 0.008%)
            ('🎰🎰🎰', 'ton', 1.0, 0.0001, '🎰', 'Джекпот'),      # 0.0001% - 1 TON (было 0.001%)
            ('7️⃣7️⃣7️⃣', 'stars', 100, 0.0001, '7️⃣', 'Три семерки'), # 0.0001% - 100⭐ (было 0.001%)
        ]
        
        # Очищаем старые конфигурации
        cursor.execute("DELETE FROM slot_config")
        
        # Добавляем новые конфигурации
        for config in new_configs:
            cursor.execute('''INSERT INTO slot_config (combination, reward_type, reward_amount, chance_percent, emoji, name) 
                             VALUES (?, ?, ?, ?, ?, ?)''', config)
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT combination, chance_percent FROM slot_config ORDER BY chance_percent DESC")
        results = cursor.fetchall()
        
        print("\n✅ Обновленные шансы:")
        total_chance = 0
        for combination, chance in results:
            print(f"  {combination}: {chance}%")
            total_chance += chance
        
        print(f"\n📊 Общий процент выигрышей: {total_chance:.4f}%")
        print("🍒 Вишни остались без изменений: 0.8%")
        print("📉 Остальные комбинации уменьшены в 10 раз")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении шансов: {e}")
        return False

if __name__ == "__main__":
    success = update_slot_chances()
    if success:
        print("\n🎉 Шансы слот-машины успешно обновлены!")
    else:
        print("\n💥 Не удалось обновить шансы!")
        sys.exit(1)
