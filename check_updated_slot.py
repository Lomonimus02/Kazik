#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_slot_configurations():
    """Проверяет обновленные конфигурации слот-машины"""
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT combination, reward_type, reward_amount, chance_percent, name FROM slot_config ORDER BY chance_percent DESC')
    configs = cursor.fetchall()
    
    total_percent = 0
    print('🎰 ОБНОВЛЕННЫЕ КОНФИГУРАЦИИ СЛОТ-МАШИНЫ:')
    print('=' * 60)
    
    for combo, reward_type, reward_amount, chance, name in configs:
        total_percent += chance
        
        # Форматируем награду
        if reward_type == "money":
            reward_text = f"{int(reward_amount)}₽"
        elif reward_type == "stars":
            reward_text = f"{int(reward_amount)}⭐"
        elif reward_type == "ton":
            reward_text = f"{reward_amount} TON"
        else:
            reward_text = str(reward_amount)
        
        print(f'{combo} - {chance}% - {reward_text} ({name})')
    
    print('=' * 60)
    print(f'📊 ОБЩИЙ ПРОЦЕНТ ВЫИГРЫШЕЙ: {total_percent:.3f}%')
    
    if total_percent <= 2.0:
        print('✅ Проценты в норме (≤2%)')
    else:
        print('❌ Проценты превышают 2%!')
    
    # Проверяем наличие джекпота и семерок
    jackpot_found = any('🎰🎰🎰' in config[0] for config in configs)
    sevens_found = any('7️⃣7️⃣7️⃣' in config[0] for config in configs)
    
    print(f'\n🎰 Джекпот (🎰🎰🎰): {"✅ Найден" if jackpot_found else "❌ Не найден"}')
    print(f'7️⃣ Три семерки (7️⃣7️⃣7️⃣): {"✅ Найдены" if sevens_found else "❌ Не найдены"}')
    
    conn.close()

if __name__ == "__main__":
    check_slot_configurations()
