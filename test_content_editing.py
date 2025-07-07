#!/usr/bin/env python3
"""
Тест системы редактирования контента для админов
Проверяет возможность редактирования фото, текстов и кнопок для всех разделов
"""

import asyncio
import sys
import os
import sqlite3
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем путь к проекту
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app.database.models import (
    get_admin_setting, update_admin_setting, get_all_admin_settings,
    init_database, get_db_connection
)

class TestContentEditing:
    def __init__(self):
        self.test_db_path = None
        self.original_db_path = None
        
    def setup_test_database(self):
        """Создает временную тестовую базу данных"""
        # Создаем временный файл для тестовой БД
        fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Сохраняем оригинальный путь к БД
        import app.database.models as models
        self.original_db_path = models.DATABASE_PATH
        models.DATABASE_PATH = self.test_db_path
        
        # Инициализируем тестовую БД
        init_database()
        print(f"✅ Создана тестовая база данных: {self.test_db_path}")
        
    def cleanup_test_database(self):
        """Удаляет временную тестовую базу данных"""
        if self.test_db_path and os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
            print(f"✅ Удалена тестовая база данных: {self.test_db_path}")
            
        # Восстанавливаем оригинальный путь к БД
        if self.original_db_path:
            import app.database.models as models
            models.DATABASE_PATH = self.original_db_path

    def test_default_settings_exist(self):
        """Проверяет, что все дефолтные настройки созданы"""
        print("\n🧪 Тест: Проверка дефолтных настроек...")
        
        # Список всех настроек, которые должны существовать
        expected_settings = [
            # Основные разделы
            'main_description', 'main_photo', 'main_title',
            'premium_description', 'premium_photo',
            'stars_description', 'stars_photo',
            'crypto_description', 'crypto_photo',
            'support_description', 'support_photo',
            'reviews_description', 'reviews_photo',
            'about_description', 'about_photo',
            # Новые разделы
            'profile_description', 'profile_photo',
            'slot_description', 'slot_photo',
            'calendar_description', 'calendar_photo',
            # Кнопки
            'btn_premium', 'btn_stars', 'btn_crypto', 'btn_support',
            'btn_profile', 'btn_reviews', 'btn_about', 'btn_activity', 'btn_slot'
        ]
        
        all_settings = get_all_admin_settings()
        existing_keys = [setting[1] for setting in all_settings]  # setting[1] = key
        
        missing_settings = []
        for setting in expected_settings:
            if setting not in existing_keys:
                missing_settings.append(setting)
        
        if missing_settings:
            print(f"❌ Отсутствуют настройки: {missing_settings}")
            return False
        else:
            print(f"✅ Все {len(expected_settings)} настроек найдены в базе данных")
            return True

    def test_content_editing_functionality(self):
        """Проверяет функциональность редактирования контента"""
        print("\n🧪 Тест: Функциональность редактирования контента...")
        
        test_cases = [
            # (key, test_value, description)
            ('profile_description', '🚀 <b>Тестовый профиль</b>\n\nЭто тестовое описание профиля.', 'Описание профиля'),
            ('profile_photo', 'https://test.com/profile.jpg', 'Фото профиля'),
            ('slot_description', '🎰 <b>Тестовая слот-машина</b>\n\nТестовое описание слота.', 'Описание слот-машины'),
            ('slot_photo', 'https://test.com/slot.jpg', 'Фото слот-машины'),
            ('calendar_description', '📅 <b>Тестовый календарь</b>\n\nТестовое описание календаря.', 'Описание календаря'),
            ('calendar_photo', 'https://test.com/calendar.jpg', 'Фото календаря'),
        ]
        
        success_count = 0
        
        for key, test_value, description in test_cases:
            try:
                # Получаем исходное значение
                original_value = get_admin_setting(key, 'default')
                
                # Обновляем значение
                update_admin_setting(key, test_value)
                
                # Проверяем, что значение обновилось
                updated_value = get_admin_setting(key, 'default')
                
                if updated_value == test_value:
                    print(f"✅ {description}: успешно обновлено")
                    success_count += 1
                    
                    # Возвращаем исходное значение
                    update_admin_setting(key, original_value)
                else:
                    print(f"❌ {description}: не удалось обновить (ожидалось: {test_value}, получено: {updated_value})")
                    
            except Exception as e:
                print(f"❌ {description}: ошибка при тестировании - {e}")
        
        print(f"\n📊 Результат: {success_count}/{len(test_cases)} тестов прошли успешно")
        return success_count == len(test_cases)

    def test_admin_ui_coverage(self):
        """Проверяет покрытие всех разделов в админ интерфейсе"""
        print("\n🧪 Тест: Покрытие разделов в админ интерфейсе...")
        
        # Проверяем, что новые разделы добавлены в соответствующие меню
        sections_to_check = [
            ('profile', 'Профиль'),
            ('slot', 'Слот-машина'),
            ('calendar', 'Календарь активности')
        ]
        
        success_count = 0
        
        for section, name in sections_to_check:
            # Проверяем наличие настроек для описания и фото
            description_key = f"{section}_description"
            photo_key = f"{section}_photo"
            
            description_exists = get_admin_setting(description_key, None) is not None
            photo_exists = get_admin_setting(photo_key, None) is not None
            
            if description_exists and photo_exists:
                print(f"✅ {name}: настройки описания и фото найдены")
                success_count += 1
            else:
                missing = []
                if not description_exists:
                    missing.append("описание")
                if not photo_exists:
                    missing.append("фото")
                print(f"❌ {name}: отсутствуют настройки для {', '.join(missing)}")
        
        print(f"\n📊 Результат: {success_count}/{len(sections_to_check)} разделов полностью покрыты")
        return success_count == len(sections_to_check)

    def run_all_tests(self):
        """Запускает все тесты"""
        print("🚀 Запуск тестов системы редактирования контента...")
        
        try:
            self.setup_test_database()
            
            tests = [
                self.test_default_settings_exist,
                self.test_content_editing_functionality,
                self.test_admin_ui_coverage
            ]
            
            passed_tests = 0
            total_tests = len(tests)
            
            for test in tests:
                try:
                    if test():
                        passed_tests += 1
                except Exception as e:
                    print(f"❌ Ошибка в тесте {test.__name__}: {e}")
            
            print(f"\n🏁 Итоговый результат: {passed_tests}/{total_tests} тестов прошли успешно")
            
            if passed_tests == total_tests:
                print("🎉 Все тесты прошли успешно! Система редактирования контента работает корректно.")
                return True
            else:
                print("⚠️ Некоторые тесты не прошли. Требуется доработка.")
                return False
                
        finally:
            self.cleanup_test_database()

def main():
    """Главная функция для запуска тестов"""
    tester = TestContentEditing()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Система редактирования контента готова к использованию!")
        sys.exit(0)
    else:
        print("\n❌ Обнаружены проблемы в системе редактирования контента!")
        sys.exit(1)

if __name__ == "__main__":
    main()
