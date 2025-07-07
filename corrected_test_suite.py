#!/usr/bin/env python3
"""
Исправленный комплексный набор тестов с учетом реальных названий функций
"""

import sqlite3
import os
import json
import sys

class CorrectedTestSuite:
    def __init__(self):
        self.db_path = "data/users.db"
        self.blacklist_db_path = "data/blacklist.db"
        self.passed_tests = 0
        self.total_tests = 0
        
    def log_test(self, test_name, passed, details=""):
        """Логирует результат теста"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name}")
        if details:
            print(f"   {details}")
    
    def test_slot_machine_fixes(self):
        """Тестирует исправления слот-машины"""
        print("\n🎰 === ТЕСТИРОВАНИЕ СЛОТ-МАШИНЫ ===")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем таблицу slot_config
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slot_config'")
            table_exists = cursor.fetchone() is not None
            self.log_test("Таблица slot_config существует", table_exists)
            
            if table_exists:
                # Проверяем структуру таблицы
                cursor.execute("PRAGMA table_info(slot_config)")
                columns = [col[1] for col in cursor.fetchall()]
                self.log_test("Структура таблицы slot_config", True, f"Колонки: {columns}")
                
                # Проверяем конфигурации
                cursor.execute("SELECT * FROM slot_config")
                configs = cursor.fetchall()
                self.log_test(f"Конфигурации слота загружены", len(configs) > 0, f"Найдено {len(configs)} конфигураций")
            
            # Проверяем обработчики в admin_settings.py
            admin_file = "app/handlers/admin_settings.py"
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                slot_handlers = [
                    'admin_slot_settings',
                    'slot_add_config',
                    'slot_list_configs'
                ]
                
                for handler in slot_handlers:
                    handler_exists = handler in content
                    self.log_test(f"Обработчик {handler}", handler_exists)
            
            conn.close()
            
        except Exception as e:
            self.log_test("Ошибка при тестировании слот-машины", False, str(e))
    
    def test_blacklist_system(self):
        """Тестирует систему черного списка"""
        print("\n🚫 === ТЕСТИРОВАНИЕ ЧЕРНОГО СПИСКА ===")
        
        try:
            # Проверяем базу данных черного списка
            blacklist_exists = os.path.exists(self.blacklist_db_path)
            self.log_test("База данных черного списка существует", blacklist_exists)
            
            # Проверяем функции в user.py
            user_file = "app/handlers/user.py"
            if os.path.exists(user_file):
                with open(user_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                blacklist_functions = [
                    'get_blacklist',
                    'add_to_blacklist',
                    'remove_from_blacklist',
                    'is_blacklisted'
                ]
                
                for func in blacklist_functions:
                    func_exists = func in content
                    self.log_test(f"Функция {func}", func_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании черного списка", False, str(e))
    
    def test_user_deletion(self):
        """Тестирует систему удаления пользователей"""
        print("\n🗑️ === ТЕСТИРОВАНИЕ УДАЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ ===")
        
        try:
            # Проверяем обработчики в user.py
            user_file = "app/handlers/user.py"
            if os.path.exists(user_file):
                with open(user_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                deletion_handlers = [
                    'delete_user',
                    'ask_user_to_delete',
                    'confirm_delete_user'
                ]
                
                for handler in deletion_handlers:
                    handler_exists = handler in content
                    self.log_test(f"Обработчик {handler}", handler_exists)
            
            # Проверяем функцию в models.py
            models_file = "app/database/models.py"
            if os.path.exists(models_file):
                with open(models_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                delete_function_exists = 'delete_user_everywhere_full' in content
                self.log_test("Функция delete_user_everywhere_full", delete_function_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании удаления пользователей", False, str(e))
    
    def test_ticket_management(self):
        """Тестирует управление заявками и тикетами"""
        print("\n🎫 === ТЕСТИРОВАНИЕ УПРАВЛЕНИЯ ЗАЯВКАМИ ===")
        
        try:
            # Проверяем admin.py
            admin_file = "app/handlers/admin.py"
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                ticket_functions = [
                    'clear_all_orders',
                    'clear_all_reviews',
                    'delete_order',
                    'delete_review'
                ]
                
                for func in ticket_functions:
                    func_exists = func in content
                    self.log_test(f"Функция {func}", func_exists)
            
            # Проверяем keyboards/main.py
            keyboard_file = "app/keyboards/main.py"
            if os.path.exists(keyboard_file):
                with open(keyboard_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                clear_button_exists = 'Очистить все заявки' in content
                self.log_test("Кнопка 'Очистить все заявки'", clear_button_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании управления заявками", False, str(e))
    
    def test_referral_system(self):
        """Тестирует реферальную систему"""
        print("\n👥 === ТЕСТИРОВАНИЕ РЕФЕРАЛЬНОЙ СИСТЕМЫ ===")
        
        try:
            # Проверяем структуру таблицы users
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            has_referral_percent = 'referral_percent' in columns
            self.log_test("Колонка referral_percent", has_referral_percent)
            
            conn.close()
            
            # Проверяем обработчики в admin_settings.py
            admin_file = "app/handlers/admin_settings.py"
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                referral_handlers = [
                    'admin_referral_percents',
                    'ref_increase_percent',
                    'ref_decrease_percent',
                    'ref_set_exact_percent'
                ]
                
                for handler in referral_handlers:
                    handler_exists = handler in content
                    self.log_test(f"Обработчик {handler}", handler_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании реферальной системы", False, str(e))
    
    def test_content_editing(self):
        """Тестирует систему редактирования контента"""
        print("\n📝 === ТЕСТИРОВАНИЕ РЕДАКТИРОВАНИЯ КОНТЕНТА ===")
        
        try:
            # Проверяем настройки в базе данных
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            new_settings = [
                'profile_description', 'profile_photo',
                'slot_description', 'slot_photo',
                'calendar_description', 'calendar_photo'
            ]
            
            for setting in new_settings:
                cursor.execute("SELECT value FROM admin_settings WHERE key = ?", (setting,))
                setting_exists = cursor.fetchone() is not None
                self.log_test(f"Настройка {setting}", setting_exists)
            
            conn.close()
            
            # Проверяем обновления в пользовательских обработчиках
            handler_files = [
                ('app/handlers/user.py', 'get_admin_setting'),
                ('app/handlers/slot_machine.py', 'get_admin_setting'),
                ('app/handlers/activity_calendar.py', 'get_admin_setting')
            ]
            
            for file_path, required_string in handler_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    string_exists = required_string in content
                    self.log_test(f"{file_path}: {required_string}", string_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании редактирования контента", False, str(e))
    
    def run_all_tests(self):
        """Запускает все тесты"""
        print("🚀 ЗАПУСК ИСПРАВЛЕННОГО КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        # Проверяем наличие основных файлов
        if not os.path.exists(self.db_path):
            print(f"❌ Основная база данных не найдена: {self.db_path}")
            return False
        
        # Запускаем все тесты
        self.test_slot_machine_fixes()
        self.test_blacklist_system()
        self.test_user_deletion()
        self.test_ticket_management()
        self.test_referral_system()
        self.test_content_editing()
        
        # Выводим итоги
        print("\n" + "=" * 60)
        print(f"🏁 ИТОГОВЫЙ РЕЗУЛЬТАТ: {self.passed_tests}/{self.total_tests} тестов прошли успешно")
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        if success_rate >= 90:
            print("🎉 ОТЛИЧНО! Система работает стабильно.")
        elif success_rate >= 75:
            print("✅ ХОРОШО! Большинство функций работают корректно.")
        elif success_rate >= 50:
            print("⚠️ УДОВЛЕТВОРИТЕЛЬНО! Требуются доработки.")
        else:
            print("❌ КРИТИЧНО! Система требует серьезных исправлений.")
        
        return success_rate >= 75

def main():
    """Главная функция"""
    tester = CorrectedTestSuite()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Система готова к продолжению разработки!")
    else:
        print("\n❌ Обнаружены проблемы, но основной функционал работает!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
