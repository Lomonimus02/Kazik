#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import shutil
from datetime import datetime

def backup_database():
    """Создает резервную копию базы данных"""
    if not os.path.exists('data'):
        os.makedirs('data')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"data/users_backup_slot_update_{timestamp}.db"
    
    if os.path.exists('data/users.db'):
        shutil.copy2('data/users.db', backup_path)
        print(f"✅ Создана резервная копия: {backup_path}")
        return backup_path
    else:
        print("❌ Файл базы данных не найден!")
        return None

def update_slot_configurations():
    """Обновляет конфигурации слот-машины согласно новым требованиям"""
    
    # Новые конфигурации с правильными призами и процентами ≤2%
    new_slot_configs = [
        ('🍒🍒🍒', 'money', 5, 0.8, '🍒', 'Вишни'),           # 0.8% - 5₽
        ('🍊🍊🍊', 'money', 10, 0.6, '🍊', 'Апельсин'),       # 0.6% - 10₽
        ('🍋🍋🍋', 'stars', 13, 0.3, '🍋', 'Лимон'),          # 0.3% - 13⭐
        ('🍇🍇🍇', 'stars', 21, 0.15, '🍇', 'Виноград'),      # 0.15% - 21⭐
        ('💎💎💎', 'ton', 0.5, 0.08, '💎', 'Алмаз'),          # 0.08% - 0.5 TON
        ('⭐️⭐️⭐️', 'stars', 50, 0.03, '⭐️', 'Звезды'),       # 0.03% - 50⭐
        ('🔔🔔🔔', 'money', 100, 0.02, '🔔', 'Колокольчик'),   # 0.02% - 100₽
        ('💰💰💰', 'stars', 75, 0.008, '💰', 'Мешок денег'),  # 0.008% - 75⭐
        ('🎰🎰🎰', 'ton', 1.0, 0.001, '🎰', 'Джекпот'),       # 0.001% - 1 TON
        ('7️⃣7️⃣7️⃣', 'stars', 100, 0.001, '7️⃣', 'Три семерки'), # 0.001% - 100⭐
    ]
    
    # Подсчитываем общий процент
    total_percent = sum(config[3] for config in new_slot_configs)
    
    print(f"🎰 ОБНОВЛЕНИЕ КОНФИГУРАЦИЙ СЛОТ-МАШИНЫ")
    print("=" * 50)
    print(f"📊 Новый общий процент выигрышей: {total_percent}%")
    
    if total_percent > 2.0:
        print(f"❌ ОШИБКА: Общий процент ({total_percent}%) превышает 2%!")
        return False
    
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    
    try:
        # Удаляем старые конфигурации
        cursor.execute("DELETE FROM slot_config")
        print("🗑️ Старые конфигурации удалены")
        
        # Добавляем новые конфигурации
        for combo, reward_type, reward_amount, chance, emoji, name in new_slot_configs:
            cursor.execute('''
                INSERT INTO slot_config (combination, reward_type, reward_amount, chance_percent, emoji, name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (combo, reward_type, reward_amount, chance, emoji, name))
            
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
        print(f"\n🎉 Конфигурации обновлены! Общий процент: {total_percent}%")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении конфигураций: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_code_defaults():
    """Обновляет дефолтные конфигурации в коде"""
    
    new_code_configs = '''    # Инициализация дефолтных конфигураций слот-машины (ОБНОВЛЕННЫЕ ПРИЗЫ)
    # Общий процент выигрышей: 2.0% (включая джекпот и семерки)
    default_slot_configs = [
        ('🍒🍒🍒', 'money', 5, 0.8, '🍒', 'Вишни'),           # 0.8% - 5₽
        ('🍊🍊🍊', 'money', 10, 0.6, '🍊', 'Апельсин'),       # 0.6% - 10₽
        ('🍋🍋🍋', 'stars', 13, 0.3, '🍋', 'Лимон'),          # 0.3% - 13⭐
        ('🍇🍇🍇', 'stars', 21, 0.15, '🍇', 'Виноград'),      # 0.15% - 21⭐
        ('💎💎💎', 'ton', 0.5, 0.08, '💎', 'Алмаз'),          # 0.08% - 0.5 TON
        ('⭐️⭐️⭐️', 'stars', 50, 0.03, '⭐️', 'Звезды'),       # 0.03% - 50⭐
        ('🔔🔔🔔', 'money', 100, 0.02, '🔔', 'Колокольчик'),   # 0.02% - 100₽
        ('💰💰💰', 'stars', 75, 0.008, '💰', 'Мешок денег'),  # 0.008% - 75⭐
        ('🎰🎰🎰', 'ton', 1.0, 0.001, '🎰', 'Джекпот'),       # 0.001% - 1 TON
        ('7️⃣7️⃣7️⃣', 'stars', 100, 0.001, '7️⃣', 'Три семерки'), # 0.001% - 100⭐
    ]'''
    
    try:
        # Читаем файл
        with open('app/database/models.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Находим и заменяем секцию с конфигурациями
        start_marker = "    # Инициализация дефолтных конфигураций слот-машины"
        end_marker = "    ]"
        
        start_pos = content.find(start_marker)
        if start_pos == -1:
            print("❌ Не найден маркер начала конфигураций")
            return False
        
        # Ищем конец массива после start_pos
        temp_pos = start_pos
        bracket_count = 0
        found_start = False
        end_pos = -1
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '[':
                found_start = True
                bracket_count += 1
            elif char == ']' and found_start:
                bracket_count -= 1
                if bracket_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos == -1:
            print("❌ Не найден конец массива конфигураций")
            return False
        
        # Заменяем секцию
        new_content = content[:start_pos] + new_code_configs + content[end_pos:]
        
        # Записываем обратно
        with open('app/database/models.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Дефолтные конфигурации в коде обновлены")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении кода: {e}")
        return False

def main():
    print("🎰 ОБНОВЛЕНИЕ СЛОТ-МАШИНЫ")
    print("=" * 60)
    
    # Создаем резервную копию
    backup_path = backup_database()
    if not backup_path:
        return
    
    # Обновляем конфигурации в БД
    if not update_slot_configurations():
        print("❌ Не удалось обновить конфигурации в БД")
        return
    
    # Обновляем код
    if not update_code_defaults():
        print("❌ Не удалось обновить код")
        return
    
    print("\n🎉 ВСЕ ЗАДАЧИ ВЫПОЛНЕНЫ УСПЕШНО!")
    print("✅ Слот-машина обновлена")
    print("✅ Добавлены джекпот и три семерки")
    print("✅ Обновлены все призы")
    print("✅ Общий процент ≤2%")
    print("✅ Код обновлен")

if __name__ == "__main__":
    main()
