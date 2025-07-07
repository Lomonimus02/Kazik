#!/usr/bin/env python3
"""
Комплексный набор тестов для всех выполненных задач
Проверяет слот-машину, черный список, удаление пользователей, 
управление заявками, реферальную систему и редактирование контента
"""

import sqlite3
import os
import json
import sys

class ComprehensiveTestSuite:
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
        
        # Проверяем наличие таблицы slot_config
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slot_config'")
            table_exists = cursor.fetchone() is not None
            self.log_test("Таблица slot_config существует", table_exists)
            
            if table_exists:
                # Проверяем конфигурацию слота
                cursor.execute("SELECT combination, probability FROM slot_config")
                configs = cursor.fetchall()
                
                # Проверяем, что нет комбинаций из 6 символов
                six_symbol_combos = [c for c in configs if len(c[0].split(',')) > 3]
                self.log_test("Нет комбинаций из 6+ символов", len(six_symbol_combos) == 0, 
                            f"Найдено {len(six_symbol_combos)} некорректных комбинаций")
                
                # Проверяем уменьшенные вероятности
                total_probability = sum(float(c[1]) for c in configs)
                self.log_test("Общая вероятность выигрыша снижена", total_probability < 50.0,
                            f"Общая вероятность: {total_probability:.2f}%")
                
                # Проверяем отсутствие дубликатов
                combinations = [c[0] for c in configs]
                unique_combinations = set(combinations)
                self.log_test("Нет дублирующихся комбинаций", len(combinations) == len(unique_combinations),
                            f"Найдено {len(combinations) - len(unique_combinations)} дубликатов")
            
            conn.close()
            
        except Exception as e:
            self.log_test("Ошибка при тестировании слот-машины", False, str(e))
    
    def test_blacklist_system(self):
        """Тестирует систему черного списка"""
        print("\n🚫 === ТЕСТИРОВАНИЕ ЧЕРНОГО СПИСКА ===")
        
        try:
            # Проверяем существование базы данных черного списка
            blacklist_exists = os.path.exists(self.blacklist_db_path)
            self.log_test("База данных черного списка существует", blacklist_exists)
            
            if blacklist_exists:
                conn = sqlite3.connect(self.blacklist_db_path)
                cursor = conn.cursor()
                
                # Проверяем структуру таблицы
                cursor.execute("PRAGMA table_info(blacklist)")
                columns = [col[1] for col in cursor.fetchall()]
                required_columns = ['id', 'username', 'reason', 'date_added']
                
                has_all_columns = all(col in columns for col in required_columns)
                self.log_test("Таблица blacklist имеет правильную структуру", has_all_columns,
                            f"Колонки: {columns}")
                
                conn.close()
            
            # Проверяем обработчики в admin_settings.py
            admin_file = "app/handlers/admin_settings.py"
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                blacklist_handlers = [
                    'admin_blacklist_add_user',
                    'admin_blacklist_remove_user',
                    'blacklist_username_input'
                ]
                
                for handler in blacklist_handlers:
                    handler_exists = handler in content
                    self.log_test(f"Обработчик {handler} существует", handler_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании черного списка", False, str(e))
    
    def test_user_deletion(self):
        """Тестирует систему удаления пользователей"""
        print("\n🗑️ === ТЕСТИРОВАНИЕ УДАЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ ===")
        
        try:
            # Проверяем функцию delete_user_completely
            admin_file = "app/handlers/admin_settings.py"
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Проверяем наличие функции удаления
                has_delete_function = 'delete_user_completely' in content
                self.log_test("Функция delete_user_completely существует", has_delete_function)
                
                # Проверяем удаление из всех таблиц
                tables_to_check = [
                    'users', 'activity_calendar', 'orders', 'withdrawals',
                    'reviews', 'roulette_attempts', 'roulette_history', 'support_tickets'
                ]
                
                for table in tables_to_check:
                    table_deletion = f"DELETE FROM {table}" in content
                    self.log_test(f"Удаление из таблицы {table}", table_deletion)
                
                # Проверяем обработчики
                deletion_handlers = [
                    'admin_delete_user',
                    'delete_username_input'
                ]
                
                for handler in deletion_handlers:
                    handler_exists = handler in content
                    self.log_test(f"Обработчик {handler} существует", handler_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании удаления пользователей", False, str(e))
    
    def test_ticket_management(self):
        """Тестирует управление заявками и тикетами"""
        print("\n🎫 === ТЕСТИРОВАНИЕ УПРАВЛЕНИЯ ЗАЯВКАМИ ===")
        
        try:
            admin_file = "app/handlers/admin_settings.py"
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Проверяем кнопки управления заявками
                ticket_features = [
                    ('Удалить все заявки', 'admin_delete_all_applications'),
                    ('Удалить тикет', 'admin_delete_ticket'),
                    ('delete_all_applications', 'функция удаления всех заявок'),
                    ('delete_ticket_by_id', 'функция удаления тикета по ID')
                ]
                
                for feature_name, feature_code in ticket_features:
                    feature_exists = feature_code in content
                    self.log_test(f"{feature_name}", feature_exists)
            
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
            self.log_test("Колонка referral_percent существует", has_referral_percent)
            
            conn.close()
            
            # Проверяем обработчики в admin_settings.py
            admin_file = "app/handlers/admin_settings.py"
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                referral_features = [
                    ('admin_referral_management', 'Управление рефералами'),
                    ('referral_username_input', 'Ввод юзернейма реферала'),
                    ('increase_referral_percent', 'Повышение процента'),
                    ('decrease_referral_percent', 'Понижение процента')
                ]
                
                for feature_code, feature_name in referral_features:
                    feature_exists = feature_code in content
                    self.log_test(f"{feature_name}", feature_exists)
            
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
                ('app/handlers/user.py', ['get_admin_setting', 'profile_description']),
                ('app/handlers/slot_machine.py', ['get_admin_setting', 'slot_description']),
                ('app/handlers/activity_calendar.py', ['get_admin_setting', 'calendar_description'])
            ]
            
            for file_path, required_strings in handler_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for required_string in required_strings:
                        string_exists = required_string in content
                        self.log_test(f"{file_path}: {required_string}", string_exists)
            
        except Exception as e:
            self.log_test("Ошибка при тестировании редактирования контента", False, str(e))
    
    def analyze_code_logic(self):
        """Анализирует код на наличие логических ошибок"""
        print("\n🔍 === АНАЛИЗ ЛОГИКИ КОДА ===")
        
        issues_found = []
        
        try:
            # Проверяем импорты и зависимости
            files_to_check = [
                'app/handlers/admin_settings.py',
                'app/handlers/user.py',
                'app/handlers/slot_machine.py',
                'app/handlers/activity_calendar.py'
            ]
            
            for file_path in files_to_check:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Проверяем потенциальные проблемы
                    if 'get_admin_setting' in content and 'from app.database.models import' not in content:
                        issues_found.append(f"{file_path}: Возможно отсутствует импорт get_admin_setting")
                    
                    # Проверяем обработку исключений
                    if 'sqlite3.connect' in content and 'except' not in content:
                        issues_found.append(f"{file_path}: Отсутствует обработка исключений для БД")
                    
                    # Проверяем закрытие соединений с БД
                    if 'sqlite3.connect' in content and 'conn.close()' not in content:
                        issues_found.append(f"{file_path}: Возможна утечка соединений с БД")
            
            if issues_found:
                for issue in issues_found:
                    self.log_test(f"Потенциальная проблема: {issue}", False)
            else:
                self.log_test("Анализ логики кода", True, "Критических проблем не обнаружено")
                
        except Exception as e:
            self.log_test("Ошибка при анализе кода", False, str(e))
    
    def run_all_tests(self):
        """Запускает все тесты"""
        print("🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ")
        print("=" * 50)
        
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
        self.analyze_code_logic()
        
        # Выводим итоги
        print("\n" + "=" * 50)
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
    tester = ComprehensiveTestSuite()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Система готова к продолжению разработки!")
    else:
        print("\n❌ Обнаружены критические проблемы!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
