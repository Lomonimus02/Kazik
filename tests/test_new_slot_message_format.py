"""
Тест нового формата сообщений слот-машины
"""
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.slot_machine import format_slot_result


class TestNewSlotMessageFormat(unittest.TestCase):
    """Тесты нового формата сообщений слот-машины"""
    
    def test_money_win_message_format(self):
        """Тест формата сообщения при выигрыше денег"""
        result = format_slot_result(
            slot1="💰", slot2="💰", slot3="💰", 
            is_win=True, 
            reward_text="100₽", 
            prize_name="Джекпот", 
            reward_type="money"
        )
        
        # Проверяем обязательные элементы
        self.assertIn("🏆 <b>Приз:</b> Джекпот", result)
        self.assertIn("🎯 <b>Комбинация:</b> 💰💰💰", result)
        self.assertIn("💎 <b>Награда:</b> 100₽", result)
        self.assertIn("📊 <b>Статус:</b> ✅ Зачислено", result)
        self.assertIn("🕒 <b>Время:</b>", result)
        self.assertIn("💰 Награда зачислена на ваш профиль", result)
        
        print("✅ Формат сообщения для денег корректен")
    
    def test_stars_win_message_format(self):
        """Тест формата сообщения при выигрыше звезд"""
        result = format_slot_result(
            slot1="⭐", slot2="⭐", slot3="⭐", 
            is_win=True, 
            reward_text="10⭐ звезд", 
            prize_name="Звездный приз", 
            reward_type="stars"
        )
        
        # Проверяем обязательные элементы
        self.assertIn("🏆 <b>Приз:</b> Звездный приз", result)
        self.assertIn("🎯 <b>Комбинация:</b> ⭐⭐⭐", result)
        self.assertIn("💎 <b>Награда:</b> 10⭐ звезд", result)
        self.assertIn("📊 <b>Статус:</b> ⏳ Не зачислено", result)
        self.assertIn("🕒 <b>Время:</b>", result)
        self.assertIn("🕒 Награда будет начислена в ближайшее время", result)
        
        print("✅ Формат сообщения для звезд корректен")
    
    def test_ton_win_message_format(self):
        """Тест формата сообщения при выигрыше TON"""
        result = format_slot_result(
            slot1="💎", slot2="💎", slot3="💎", 
            is_win=True, 
            reward_text="0.5 TON", 
            prize_name="TON приз", 
            reward_type="ton"
        )
        
        # Проверяем обязательные элементы
        self.assertIn("🏆 <b>Приз:</b> TON приз", result)
        self.assertIn("🎯 <b>Комбинация:</b> 💎💎💎", result)
        self.assertIn("💎 <b>Награда:</b> 0.5 TON", result)
        self.assertIn("📊 <b>Статус:</b> ⏳ Не зачислено", result)
        self.assertIn("🕒 <b>Время:</b>", result)
        self.assertIn("🕒 Награда будет начислена в ближайшее время", result)
        
        print("✅ Формат сообщения для TON корректен")
    
    def test_lose_message_format(self):
        """Тест формата сообщения при проигрыше"""
        result = format_slot_result(
            slot1="🍒", slot2="🍋", slot3="🍊", 
            is_win=False
        )
        
        # Проверяем элементы проигрыша
        self.assertIn("😔 На этот раз не повезло...", result)
        self.assertIn("🍀 Не расстраивайтесь! Попробуйте еще раз!", result)
        self.assertIn("🎯 Удача обязательно улыбнется вам!", result)
        
        print("✅ Формат сообщения для проигрыша корректен")
    
    def test_message_structure_consistency(self):
        """Тест консистентности структуры сообщений"""
        # Тестируем разные типы наград
        test_cases = [
            ("money", "100₽", "✅ Зачислено", "💰 Награда зачислена на ваш профиль"),
            ("stars", "10⭐", "⏳ Не зачислено", "🕒 Награда будет начислена в ближайшее время"),
            ("ton", "0.5 TON", "⏳ Не зачислено", "🕒 Награда будет начислена в ближайшее время")
        ]
        
        for reward_type, reward_text, expected_status, expected_message in test_cases:
            with self.subTest(reward_type=reward_type):
                result = format_slot_result(
                    slot1="🎰", slot2="🎰", slot3="🎰", 
                    is_win=True, 
                    reward_text=reward_text, 
                    prize_name="Тестовый приз", 
                    reward_type=reward_type
                )
                
                # Проверяем структуру
                self.assertIn("🏆 <b>Приз:</b>", result)
                self.assertIn("🎯 <b>Комбинация:</b>", result)
                self.assertIn("💎 <b>Награда:</b>", result)
                self.assertIn("📊 <b>Статус:</b>", result)
                self.assertIn("🕒 <b>Время:</b>", result)
                
                # Проверяем специфичные элементы
                self.assertIn(expected_status, result)
                self.assertIn(expected_message, result)
        
        print("✅ Структура сообщений консистентна для всех типов наград")
    
    def test_time_format_in_message(self):
        """Тест формата времени в сообщении"""
        result = format_slot_result(
            slot1="💰", slot2="💰", slot3="💰", 
            is_win=True, 
            reward_text="100₽", 
            prize_name="Джекпот", 
            reward_type="money"
        )
        
        # Проверяем что время присутствует в правильном формате
        import re
        time_pattern = r"🕒 <b>Время:</b> \d{2}:\d{2} \d{2}\.\d{2}\.\d{4}"
        self.assertTrue(re.search(time_pattern, result), "Время должно быть в формате ЧЧ:ММ ДД.ММ.ГГГГ")
        
        print("✅ Формат времени корректен")
    
    def test_emoji_consistency(self):
        """Тест консистентности эмодзи"""
        result = format_slot_result(
            slot1="⭐", slot2="⭐", slot3="⭐", 
            is_win=True, 
            reward_text="10⭐", 
            prize_name="Звезды", 
            reward_type="stars"
        )
        
        # Проверяем наличие всех необходимых эмодзи
        required_emojis = ["🏆", "🎯", "💎", "📊", "🕒"]
        for emoji in required_emojis:
            self.assertIn(emoji, result, f"Эмодзи {emoji} должно присутствовать в сообщении")
        
        print("✅ Эмодзи в сообщениях консистентны")


if __name__ == '__main__':
    unittest.main()
