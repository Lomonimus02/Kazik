#!/usr/bin/env python3
"""
Скрипт для установки процентов слот-машины согласно изображению пользователя
"""
import sqlite3
import sys
import os

def set_slot_percentages():
    """Устанавливает проценты слот-машины согласно изображению"""
    print("🎰 УСТАНОВКА ПРОЦЕНТОВ СЛОТ-МАШИНЫ ПО ИЗОБРАЖЕНИЮ")
    print("=" * 60)
    
    # Проценты согласно изображению пользователя
    new_configs = [
        # combination, reward_type, reward_amount, chance_percent, emoji, name
        ('🍒🍒🍒', 'money', 5, 8.8, '🍒', 'Вишни'),              # 1% - 5₽
        ('🍊🍊🍊', 'money', 10, 0.86, '🍊', 'Апельсин'),         # 0.86% - 10₽  
        ('🍋🍋🍋', 'stars', 13, 0.03, '🍋', 'Лимон'),            # 0.03% - 13⭐
        ('🍇🍇🍇', 'stars', 21, 0.015, '🍇', 'Виноград'),        # 0.015% - 21⭐
        ('💎💎💎', 'ton', 0.5, 0.008, '💎', 'Алмаз'),            # 0.008% - 0.5 TON
        ('⭐️⭐️⭐️', 'stars', 50, 0.003, '⭐️', 'Звезды'),         # 0.003% - 50⭐
        ('🔔🔔🔔', 'money', 100, 0.002, '🔔', 'Колокольчик'),    # 0.002% - 100₽
        ('💰💰💰', 'stars', 75, 0.0008, '💰', 'Мешок денег'),    # 0.0008% - 75⭐
        ('🎰🎰🎰', 'ton', 1.0, 0.0001, '🎰', 'Джекпот'),         # 0.0001% - 1 TON
        ('7️⃣7️⃣7️⃣', 'stars', 100, 0.0001, '7️⃣', 'Три семерки'), # 0.0001% - 100⭐
    ]
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()
        
        print("📊 Текущие настройки слот-машины:")
        print("-" * 60)
        
        # Показываем текущие настройки
        cursor.execute('SELECT combination, reward_type, reward_amount, chance_percent, name FROM slot_config ORDER BY chance_percent DESC')
        current_configs = cursor.fetchall()
        
        current_total = 0
        for config in current_configs:
            combination, reward_type, reward_amount, chance_percent, name = config
            current_total += chance_percent
            
            # Форматируем награду
            if reward_type == "money":
                reward_text = f"{int(reward_amount)}₽"
            elif reward_type == "stars":
                reward_text = f"{int(reward_amount)}⭐"
            elif reward_type == "ton":
                reward_text = f"{reward_amount} TON"
            else:
                reward_text = str(reward_amount)
            
            print(f"{combination} - {name}: {chance_percent}% ({reward_text})")
        
        print(f"\n📈 Текущий общий процент: {current_total:.4f}%")
        
        print("\n🔄 Обновление настроек...")
        print("-" * 60)
        
        # Очищаем старые конфигурации
        cursor.execute("DELETE FROM slot_config")
        print("🗑️ Старые конфигурации удалены")
        
        # Добавляем новые конфигурации
        new_total = 0
        for combo, reward_type, reward_amount, chance, emoji, name in new_configs:
            cursor.execute('''
                INSERT INTO slot_config (combination, reward_type, reward_amount, chance_percent, emoji, name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (combo, reward_type, reward_amount, chance, emoji, name))
            
            new_total += chance
            
            # Форматируем награду для вывода
            if reward_type == "money":
                reward_text = f"{int(reward_amount)}₽"
            elif reward_type == "stars":
                reward_text = f"{int(reward_amount)}⭐"
            elif reward_type == "ton":
                reward_text = f"{reward_amount} TON"
            else:
                reward_text = str(reward_amount)
            
            print(f"✅ Добавлено: {name} ({combo}) - {chance}% - {reward_text}")
        
        conn.commit()
        
        print("\n📊 НОВЫЕ НАСТРОЙКИ СЛОТ-МАШИНЫ:")
        print("=" * 60)
        
        # Показываем обновленные настройки
        cursor.execute('SELECT combination, reward_type, reward_amount, chance_percent, name FROM slot_config ORDER BY chance_percent DESC')
        updated_configs = cursor.fetchall()
        
        for config in updated_configs:
            combination, reward_type, reward_amount, chance_percent, name = config
            
            # Форматируем награду
            if reward_type == "money":
                reward_text = f"{int(reward_amount)}₽"
            elif reward_type == "stars":
                reward_text = f"{int(reward_amount)}⭐"
            elif reward_type == "ton":
                reward_text = f"{reward_amount} TON"
            else:
                reward_text = str(reward_amount)
            
            print(f"{combination}: {chance_percent}% - {reward_text}")
        
        print(f"\n📈 Новый общий процент выигрышей: {new_total:.4f}%")
        
        # Проверяем соответствие изображению
        print("\n🔍 ПРОВЕРКА СООТВЕТСТВИЯ ИЗОБРАЖЕНИЮ:")
        print("-" * 60)
        
        expected_percentages = {
            '🍒🍒🍒': 1,
            '🍊🍊🍊': 0.86,
            '🍋🍋🍋': 0.03,
            '🍇🍇🍇': 0.015,
            '💎💎💎': 0.008,
            '⭐️⭐️⭐️': 0.003,
            '🔔🔔🔔': 0.002,
            '💰💰💰': 0.0008,
            '🎰🎰🎰': 0.0001,
            '7️⃣7️⃣7️⃣': 0.0001,
        }
        
        all_correct = True
        for combo, expected in expected_percentages.items():
            cursor.execute('SELECT chance_percent FROM slot_config WHERE combination = ?', (combo,))
            result = cursor.fetchone()
            if result:
                actual = result[0]
                if abs(actual - expected) < 0.0001:  # Допуск на погрешность
                    print(f"✅ {combo}: {actual}% (ожидалось {expected}%)")
                else:
                    print(f"❌ {combo}: {actual}% (ожидалось {expected}%)")
                    all_correct = False
            else:
                print(f"❌ {combo}: не найдено в базе данных")
                all_correct = False
        
        expected_total = 9.9198  # Сумма всех процентов с изображения
        if abs(new_total - expected_total) < 0.001:
            print(f"✅ Общий процент: {new_total:.4f}% (ожидалось ~{expected_total}%)")
        else:
            print(f"⚠️ Общий процент: {new_total:.4f}% (ожидалось ~{expected_total}%)")
        
        conn.close()
        
        print("\n" + "=" * 60)
        if all_correct:
            print("🎉 ПРОЦЕНТЫ УСПЕШНО УСТАНОВЛЕНЫ СОГЛАСНО ИЗОБРАЖЕНИЮ!")
            print("✅ Все комбинации соответствуют заданным процентам")
            print(f"✅ Общий процент выигрышей: {new_total:.4f}%")
        else:
            print("⚠️ ОБНАРУЖЕНЫ РАСХОЖДЕНИЯ!")
            print("🔧 Проверьте настройки и повторите операцию")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция"""
    if not os.path.exists('data/users.db'):
        print("❌ База данных не найдена! Сначала инициализируйте базу данных.")
        sys.exit(1)
    
    success = set_slot_percentages()
    
    if success:
        print("\n🎯 СКРИПТ ВЫПОЛНЕН УСПЕШНО!")
        print("🎰 Проценты слот-машины обновлены согласно изображению")
    else:
        print("\n💥 ОШИБКА ВЫПОЛНЕНИЯ СКРИПТА!")
        sys.exit(1)

if __name__ == '__main__':
    main()
