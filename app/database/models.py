"""
Модели базы данных
"""
import datetime
import json
import sqlite3
import threading
from typing import Tuple, Optional, Dict, List
import aiosqlite
import logging

db_lock = threading.RLock()

def get_db_connection():
    return sqlite3.connect('data/users.db', timeout=30)

def migrate_users_table():
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Check if 'users' table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            table_exists = cursor.fetchone()

            if not table_exists:
                # If table doesn't exist, create it with the full schema
                cursor.execute('''
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tg_id INTEGER UNIQUE,
                        full_name TEXT,
                        username TEXT,
                        reg_date TEXT,
                        balance REAL DEFAULT 0,
                        frozen REAL DEFAULT 0,
                        referrer_id INTEGER,
                        referral_percent REAL DEFAULT 5.0,
                        slot_spins_used INTEGER DEFAULT 0,
                        slot_last_reset TEXT,
                        share_story_used INTEGER DEFAULT 0,
                        share_story_last_reset TEXT
                    )
                ''')
                conn.commit()
                conn.close()
                return # Exit after creating the table

            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'id' not in columns:
                # Формируем список реально существующих столбцов для копирования
                base_fields = ['tg_id', 'full_name', 'username', 'reg_date']
                existing_fields = [f for f in base_fields if f in columns]
                fields_str = ', '.join(existing_fields)
                # Создаём новую таблицу с нужной структурой
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tg_id INTEGER UNIQUE,
                        full_name TEXT,
                        username TEXT,
                        reg_date TEXT,
                        balance REAL DEFAULT 0,
                        frozen REAL DEFAULT 0,
                        referrer_id INTEGER
                    )
                ''')
                
                # Копируем данные из старой таблицы, исключая дубликаты по tg_id
                if existing_fields:
                    if 'tg_id' in existing_fields:
                        # Копируем только уникальные записи по tg_id
                        cursor.execute(f'''
                            INSERT INTO users_new ({fields_str})
                            SELECT {fields_str} FROM users
                            WHERE tg_id IN (
                                SELECT tg_id FROM users
                                GROUP BY tg_id
                                HAVING COUNT(*) = 1
                            )
                            UNION
                            SELECT {fields_str} FROM users
                            WHERE tg_id IN (
                                SELECT tg_id FROM users
                                GROUP BY tg_id
                                HAVING COUNT(*) > 1
                            )
                            GROUP BY tg_id
                        ''')
                    else:
                        cursor.execute(f'INSERT INTO users_new ({fields_str}) SELECT {fields_str} FROM users')
                
                # Удаляем старую таблицу и переименовываем новую
                cursor.execute('DROP TABLE users')
                cursor.execute('ALTER TABLE users_new RENAME TO users')
            else:
                # Миграция: добавление новых столбцов, если их нет
                if 'balance' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0')
                if 'frozen' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN frozen REAL DEFAULT 0')
                if 'referrer_id' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN referrer_id INTEGER')
                if 'referral_percent' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN referral_percent REAL DEFAULT 5.0')
                if 'slot_spins_used' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN slot_spins_used INTEGER DEFAULT 0')
                if 'slot_last_reset' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN slot_last_reset TEXT')
                if 'share_story_used' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN share_story_used INTEGER DEFAULT 0')
                if 'share_story_last_reset' not in columns:
                    cursor.execute('ALTER TABLE users ADD COLUMN share_story_last_reset TEXT')
                
                # Обновляем NULL значения в поле frozen на 0
                cursor.execute('UPDATE users SET frozen = 0 WHERE frozen IS NULL')
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

# --- основной init_db ---
def init_db():
    migrate_users_table()
    migrate_orders_table()  # Добавляю миграцию таблицы orders
    migrate_support_tickets_table()  # Добавляю миграцию таблицы поддержки
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- WITHDRAWALS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT,
        created_at TEXT,
        requisites TEXT,
        type TEXT DEFAULT 'withdraw',
        extra TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # --- USERS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        tg_id INTEGER UNIQUE,
        full_name TEXT,
        username TEXT,
        reg_date TEXT
    )''')
    
    # Миграция: добавление новых столбцов, если их нет
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(users)")]
    if 'balance' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0')
    if 'frozen' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN frozen REAL DEFAULT 0')
    if 'referrer_id' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN referrer_id INTEGER')
    if 'referral_percent' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN referral_percent REAL DEFAULT 5.0')
    if 'slot_spins_used' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN slot_spins_used INTEGER DEFAULT 0')
    if 'slot_last_reset' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN slot_last_reset TEXT')
    if 'share_story_used' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN share_story_used INTEGER DEFAULT 0')
    if 'share_story_last_reset' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN share_story_last_reset TEXT')

    
    # --- ORDERS (чеки) ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        status TEXT,
        created_at TEXT,
        data_json TEXT,
        file_id TEXT,
        admin_msg_id INTEGER,
        user_msg_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # --- REVIEWS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        status TEXT,
        created_at TEXT,
        admin_msg_id INTEGER,
        channel_msg_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # --- ADMIN SETTINGS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        description TEXT
    )''')
    
    # --- SLOT MACHINE ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS slot_machine (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        combination TEXT,
        reward_type TEXT,
        reward_amount REAL,
        is_win BOOLEAN,
        created_at TEXT,
        status TEXT DEFAULT 'pending',
        admin_msg_id INTEGER,
        extra_data TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Добавляем поле extra_data если его нет (для существующих БД)
    try:
        cursor.execute('ALTER TABLE slot_machine ADD COLUMN extra_data TEXT')
    except sqlite3.OperationalError:
        pass  # Поле уже существует
    
    # --- ACTIVITY CALENDAR ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_calendar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        activity_type TEXT,
        reward_type TEXT,
        reward_amount REAL,
        claimed BOOLEAN DEFAULT FALSE,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # --- SLOT CONFIG ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS slot_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        combination TEXT UNIQUE,
        reward_type TEXT,
        reward_amount REAL,
        chance_percent REAL,
        emoji TEXT,
        name TEXT
    )''')
    
    # --- ACTIVITY REWARDS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        days_required INTEGER,
        reward_type TEXT,
        reward_amount REAL,
        description TEXT
    )''')
    
    # --- SUPPORT TICKETS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        full_name TEXT,
        message TEXT,
        status TEXT,
        created_at TEXT,
        channel_msg_id INTEGER,
        reply TEXT,
        replied_at TEXT
    )''')
    
    # --- ROULETTE ATTEMPTS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS roulette_attempts (
        user_id INTEGER PRIMARY KEY,
        attempts_used INTEGER DEFAULT 0,
        last_reset TEXT
    )''')

    # --- BONUS ATTEMPTS ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS bonus_attempts (
        user_id INTEGER PRIMARY KEY,
        attempts INTEGER DEFAULT 0
    )''')
    
    # --- REFERRAL ATTEMPTS GIVEN ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_attempts_given (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_user_id INTEGER,
        attempts_given INTEGER DEFAULT 2,
        given_at TEXT,
        UNIQUE(referrer_id, referred_user_id)
    )''')
    
    # --- ROULETTE CONFIG ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS roulette_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        combination TEXT,
        reward_type TEXT,
        reward_amount REAL,
        chance_percent REAL,
        emoji TEXT,
        name TEXT
    )''')
    
    # Инициализация дефолтных настроек
    default_settings = [
        ('prem_3_price', '1154', 'Цена Premium 3 месяца'),
        ('prem_6_price', '1580', 'Цена Premium 6 месяцев'),
        ('prem_12_price', '2600', 'Цена Premium 12 месяцев'),
        ('main_photo', '', 'Главное фото бота'),
        ('btn_premium', 'TG Премиум 🔮', 'Кнопка Premium'),
        ('btn_stars', 'Звезды ⭐', 'Кнопка звезд'),
        ('btn_crypto', 'Купить криптовалюту 💸', 'Кнопка криптовалюты'),
        ('btn_support', 'Поддержка ✍️', 'Кнопка поддержки'),
        ('btn_profile', '👤 Профиль', 'Кнопка профиля'),
        ('btn_reviews', '🛍️ Отзывы', 'Кнопка отзывов'),
        ('btn_about', 'Описание 📝', 'Кнопка описания'),
        ('btn_activity', '📅 Календарь активности', 'Кнопка календаря'),
        ('btn_slot', '🎰 Слот-машина', 'Кнопка слот-машины'),
        ('profile_description', '🚀 <b>Ваш профиль</b>\n\nЗдесь вы можете посмотреть информацию о своем аккаунте, балансе и истории операций.', 'Описание профиля'),
        ('profile_photo', 'https://imgur.com/a/TkOPe7c.jpeg', 'Фото профиля'),
        ('slot_description', '🎰 <b>Слот-машина</b>\n\nСлот-машина — это бесплатная игра от Legal Stars.\n\n🎁Выигрывайте деньги, звёзды и TON!', 'Описание слот-машины'),
        ('slot_photo', 'https://imgur.com/a/TkOPe7c.jpeg', 'Фото слот-машины'),
        ('calendar_description', '📅 <b>Календарь активности</b>\n\nОтмечайте активность каждый день и получайте награды за постоянство!', 'Описание календаря'),
        ('calendar_photo', 'https://imgur.com/a/TkOPe7c.jpeg', 'Фото календаря'),
        ('stars_rate_low', '1.65', 'Курс звезд до порога'),
        ('stars_rate_high', '1.6', 'Курс звезд от порога'),
        ('stars_threshold', '1500', 'Порог смены курса звезд'),
        ('slot_daily_attempts', '5', 'Дневные попытки слот-машины'),
        ('slot_reset_hour', '0', 'Час сброса попыток слот-машины'),
        ('activity_enabled', 'true', 'Включен ли календарь активности'),
        ('withdrawal_commission', '3.0', 'Комиссия при выводе средств (%)'),
        ('share_story_bonus_spins', '2', 'Бонусные спины за историю'),
        ('share_story_cooldown_hours', '24', 'Кулдаун истории в часах'),
    ]
    
    # Вставляем настройки
    for key, value, description in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO admin_settings (key, value, description)
            VALUES (?, ?, ?)
        ''', (key, value, description))
    
    # Инициализация дефолтных конфигураций слот-машины (ШАНСЫ УМЕНЬШЕНЫ В 10 РАЗ КРОМЕ ВИШЕН)
    # Общий процент выигрышей: ~0.86% (вишни остались 0.8%, остальные уменьшены в 10 раз)
    default_slot_configs = [
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
    
    for combo, reward_type, reward_amount, chance, emoji, name in default_slot_configs:
        cursor.execute('''
            INSERT OR IGNORE INTO slot_config (combination, reward_type, reward_amount, chance_percent, emoji, name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (combo, reward_type, reward_amount, chance, emoji, name))
    
    conn.commit()
    conn.close()



def get_user_last_activity_date(user_id: int) -> Optional[str]:
    """Возвращает дату последней активности пользователя в формате YYYY-MM-DD"""
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM user_activity WHERE user_id = ? ORDER BY date DESC LIMIT 1', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def reset_user_activity(user_id: int):
    """Полностью сбрасывает активность пользователя"""
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_activity WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
# --- Пользователь ---
def get_or_create_user(tg_id, full_name, username, reg_date, referrer_id=None):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, tg_id, full_name, username, reg_date, balance, frozen, referrer_id FROM users WHERE tg_id=?', (tg_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute('''INSERT INTO users (tg_id, full_name, username, reg_date, referrer_id) VALUES (?, ?, ?, ?, ?)''',
                           (tg_id, full_name, username, reg_date, referrer_id))
            conn.commit()
            cursor.execute('SELECT id, tg_id, full_name, username, reg_date, balance, frozen, referrer_id FROM users WHERE tg_id=?', (tg_id,))
            user = cursor.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0],
                'tg_id': user[1],
                'full_name': user[2],
                'username': user[3],
                'reg_date': user[4],
                'balance': user[5],
                'frozen': user[6],
                'referrer_id': user[7]
            }
        return None

# --- Баланс ---
def update_balance(tg_id, amount):
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Используем COALESCE для обработки NULL значений
            cursor.execute('UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE tg_id=?', (amount, tg_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

def freeze_balance(tg_id, amount):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Сначала уменьшаем баланс, потом увеличиваем замороженные средства
        cursor.execute('UPDATE users SET balance = COALESCE(balance, 0) - ? WHERE tg_id=?', (amount, tg_id))
        cursor.execute('UPDATE users SET frozen = COALESCE(frozen, 0) + ? WHERE tg_id=?', (amount, tg_id))
        conn.commit()
        conn.close()

def unfreeze_balance(tg_id, amount):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Используем COALESCE для обработки NULL значений
        cursor.execute('UPDATE users SET frozen = MAX(COALESCE(frozen, 0) - ?, 0), balance = COALESCE(balance, 0) + ? WHERE tg_id=?', (amount, amount, tg_id))
        conn.commit()
        conn.close()

def write_off_frozen_balance(tg_id, amount):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET frozen = MAX(COALESCE(frozen, 0) - ?, 0) WHERE tg_id=?', (amount, tg_id))
        conn.commit()
        conn.close()

# --- Заявки на вывод и чеки ---
def create_withdrawal(tg_id, amount, requisites="", type="withdraw", extra=None):
    """Создает заявку на вывод средств с учетом комиссии"""
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            commission, final_amount = calculate_withdrawal_commission(amount)
            freeze_balance(tg_id, amount)
            user_profile = get_user_profile(tg_id)
            if not user_profile:
                raise Exception(f"Пользователь с tg_id={tg_id} не найден при создании заявки на вывод.")
            cursor.execute('''
                INSERT INTO withdrawals (user_id, amount, status, created_at, requisites, type, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_profile['id'],
                amount,
                "pending",
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                requisites,
                type,
                json.dumps({
                    "commission": commission,
                    "final_amount": final_amount,
                    "commission_percent": float(get_admin_setting('withdrawal_commission', '3.0'))
                }) if extra is None else extra
            ))
            withdrawal_id = cursor.lastrowid
            conn.commit()
            # Получаем только что созданную заявку и возвращаем как dict
            cursor.execute('''SELECT w.id, w.user_id, w.amount, w.status, w.created_at, w.requisites, w.type, w.extra, u.tg_id, u.full_name, u.username
                              FROM withdrawals w JOIN users u ON w.user_id = u.id WHERE w.id = ?''', (withdrawal_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'amount': row[2],
                    'status': row[3],
                    'created_at': row[4],
                    'requisites': row[5],
                    'type': row[6],
                    'extra': row[7],
                    'tg_id': row[8],
                    'full_name': row[9],
                    'username': row[10]
                }
            return None
        except Exception as e:
            conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

# --- Получение всех заявок (любого типа) ---
def get_all_pending_withdrawals():
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.id, w.user_id, w.amount, w.status, w.created_at, w.requisites, w.type, w.extra, u.tg_id, u.full_name, u.username
            FROM withdrawals w
            JOIN users u ON w.user_id = u.id
            WHERE w.status = 'pending'
            ORDER BY w.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return []
        result = []
        for row in rows:
            if not row:
                continue
            result.append({
                'id': row[0],
                'user_id': row[1],
                'amount': row[2],
                'status': row[3],
                'created_at': row[4],
                'requisites': row[5],
                'type': row[6],
                'extra': row[7],
                'tg_id': row[8],
                'full_name': row[9],
                'username': row[10]
            })
        return result

# --- Получение заявки по ID ---
def get_withdrawal_by_id(withdrawal_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.id, w.user_id, w.amount, w.status, w.created_at, w.requisites, w.type, w.extra, u.tg_id, u.full_name, u.username
            FROM withdrawals w
            JOIN users u ON w.user_id = u.id
            WHERE w.id = ?
        ''', (withdrawal_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            'id': row[0],
            'user_id': row[1],
            'amount': row[2],
            'status': row[3],
            'created_at': row[4],
            'requisites': row[5],
            'type': row[6],
            'extra': row[7],
            'tg_id': row[8],
            'full_name': row[9],
            'username': row[10]
        }

def update_withdrawal_status(withdrawal_id, status):
    """Обновляет статус заявки на вывод средств"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE withdrawals SET status = ? WHERE id = ?', (status, withdrawal_id))
        conn.commit()
        conn.close()

# --- Профиль ---
def get_user_profile(tg_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id, tg_id, full_name, username, reg_date, balance, frozen, referrer_id FROM users WHERE tg_id=?''', (tg_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0],
                'tg_id': user[1],
                'full_name': user[2],
                'username': user[3],
                'reg_date': user[4],
                'balance': user[5],
                'frozen': user[6],
                'referrer_id': user[7]
            }
        return None

def get_referrals_count(tg_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE tg_id=?', (tg_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return 0
        user_id = user[0]
        cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id=?', (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

def get_all_users():
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        conn.close()
        return users

def clear_all_withdrawals_and_frozen():
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM withdrawals')
        cursor.execute('UPDATE users SET frozen = 0')
        conn.commit()
        conn.close()

def remove_balance(tg_id, amount):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = MAX(balance - ?, 0) WHERE tg_id=?', (amount, tg_id))
        conn.commit()
        conn.close()

# --- Заказ (чек) ---
def migrate_orders_table():
    """Миграция таблицы orders для добавления недостающих колонок"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        if not cursor.fetchone():
            # Создаём таблицу если её нет
            cursor.execute('''CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_type TEXT,
                amount REAL,
                status TEXT,
                created_at TEXT,
                file_id TEXT,
                extra_data TEXT,
                admin_msg_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
        else:
            # Проверяем существование колонок
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'user_id' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN user_id INTEGER')
            
            if 'order_type' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN order_type TEXT')
            
            if 'amount' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN amount REAL')
            
            if 'status' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN status TEXT')
            
            if 'created_at' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN created_at TEXT')
            
            if 'file_id' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN file_id TEXT')
            
            if 'extra_data' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN extra_data TEXT')
            
            if 'admin_msg_id' not in columns:
                cursor.execute('ALTER TABLE orders ADD COLUMN admin_msg_id INTEGER')
        
        conn.commit()
        conn.close()

def create_order(user_id, order_type, amount, status, file_id=None, extra_data=None):
    import sqlite3, datetime, json
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        extra_data_json = json.dumps(extra_data) if extra_data else None
        if user_id is None:
            raise Exception("user_id не может быть None при создании заказа")
        cursor.execute('''INSERT INTO orders (user_id, order_type, amount, status, created_at, file_id, extra_data) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (user_id, order_type, amount, status, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), file_id, extra_data_json))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return order_id

def get_order_by_id(order_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id, user_id, order_type, amount, status, created_at, file_id, extra_data, admin_msg_id 
                          FROM orders WHERE id = ?''', (order_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'order_type': row[2],
                'amount': row[3],
                'status': row[4],
                'created_at': row[5],
                'file_id': row[6],
                'extra_data': row[7],
                'admin_msg_id': row[8]
            }
        return None

def get_all_orders():
    # Выполняем миграцию перед получением данных
    migrate_orders_table()
    
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id, user_id, order_type, amount, status, created_at, file_id, extra_data, admin_msg_id 
                          FROM orders ORDER BY created_at DESC''')
        rows = cursor.fetchall()
        conn.close()
        return rows



def delete_order(order_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()
        conn.close()

def clear_all_orders():
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM orders')
        conn.commit()
        conn.close()

# --- Отзывы ---
def migrate_reviews_table():
    """Миграция таблицы reviews для добавления недостающих колонок"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
        if not cursor.fetchone():
            # Создаём таблицу если её нет
            cursor.execute('''CREATE TABLE reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT,
                status TEXT,
                created_at TEXT,
                file_id TEXT,
                admin_msg_id INTEGER,
                channel_msg_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
        else:
            # Проверяем существование колонок
            cursor.execute("PRAGMA table_info(reviews)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'user_id' not in columns:
                cursor.execute('ALTER TABLE reviews ADD COLUMN user_id INTEGER')
            
            if 'content' not in columns:
                cursor.execute('ALTER TABLE reviews ADD COLUMN content TEXT')
            
            if 'status' not in columns:
                cursor.execute('ALTER TABLE reviews ADD COLUMN status TEXT')
            
            if 'created_at' not in columns:
                cursor.execute('ALTER TABLE reviews ADD COLUMN created_at TEXT')
            
            if 'file_id' not in columns:
                cursor.execute('ALTER TABLE reviews ADD COLUMN file_id TEXT')
            
            if 'admin_msg_id' not in columns:
                cursor.execute('ALTER TABLE reviews ADD COLUMN admin_msg_id INTEGER')
            
            if 'channel_msg_id' not in columns:
                cursor.execute('ALTER TABLE reviews ADD COLUMN channel_msg_id INTEGER')

        # Мигрируем данные из text в content, если content пустой
        cursor.execute("SELECT id, text, content FROM reviews WHERE text IS NOT NULL AND text != ''")
        text_data = cursor.fetchall()

        for review_id, text_content, current_content in text_data:
            if not current_content or current_content.strip() == '':
                cursor.execute("UPDATE reviews SET content = ? WHERE id = ?", (text_content, review_id))

        conn.commit()
        conn.close()

def create_review(user_id, content, file_id=None, status="pending"):
    import datetime

    # Выполняем миграцию перед созданием отзыва
    migrate_reviews_table()

    # Если контент пустой, но есть файл, устанавливаем специальное значение
    if not content or not content.strip():
        if file_id:
            content = "[Отзыв с фото]"
        else:
            content = "[Пустой отзыв]"

    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''INSERT INTO reviews (user_id, content, status, created_at, file_id)
                          VALUES (?, ?, ?, ?, ?)''',
                       (user_id, content, status, datetime.datetime.now().isoformat(), file_id))

        review_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return review_id

def get_review_by_id(review_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id 
                          FROM reviews WHERE id = ?''', (review_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'content': row[2],
                'status': row[3],
                'created_at': row[4],
                'file_id': row[5],
                'admin_msg_id': row[6],
                'channel_msg_id': row[7]
            }
        return None

def get_all_reviews():
    # Выполняем миграцию перед получением данных
    migrate_reviews_table()
    
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id, user_id, content, status, created_at, file_id, admin_msg_id, channel_msg_id 
                          FROM reviews ORDER BY created_at DESC''')
        rows = cursor.fetchall()
        conn.close()
        return rows

def update_review_status(review_id, status=None, admin_msg_id=None, channel_msg_id=None):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if status:
            updates.append('status = ?')
            values.append(status)
        if admin_msg_id:
            updates.append('admin_msg_id = ?')
            values.append(admin_msg_id)
        if channel_msg_id:
            updates.append('channel_msg_id = ?')
            values.append(channel_msg_id)
        
        if updates:
            values.append(review_id)
            cursor.execute(f'UPDATE reviews SET {", ".join(updates)} WHERE id = ?', values)
            conn.commit()
        
        conn.close()

def delete_review(review_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
        conn.commit()
        conn.close()

def clear_all_reviews():
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reviews')
        conn.commit()
        conn.close()

def get_withdrawals(tg_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE tg_id=?', (tg_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return []
        user_id = user[0]
        cursor.execute('''
            SELECT amount, status, created_at FROM withdrawals
            WHERE user_id=?
            ORDER BY created_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

def confirm_withdrawal(tg_id, amount):
    """Подтверждает вывод средств и списывает замороженный баланс"""
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Списываем замороженную сумму (не возвращаем на баланс)
            write_off_frozen_balance(tg_id, amount)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

def get_user_profile_by_id(user_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id, tg_id, full_name, username, reg_date, balance, frozen, referrer_id FROM users WHERE id=?''', (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0],
                'tg_id': user[1],
                'full_name': user[2],
                'username': user[3],
                'reg_date': user[4],
                'balance': user[5],
                'frozen': user[6],
                'referrer_id': user[7]
            }
        return None

# --- SUPPORT TICKETS ---
def migrate_support_tickets_table():
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            message TEXT,
            status TEXT,
            created_at TEXT,
            channel_msg_id INTEGER,
            reply TEXT,
            replied_at TEXT
        )''')
        conn.commit()
        conn.close()

def create_support_ticket(user_id, username, full_name, message, channel_msg_id=None):
    import datetime
    migrate_support_tickets_table()
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO support_tickets (user_id, username, full_name, message, status, created_at, channel_msg_id) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (user_id, username, full_name, message, 'open', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), channel_msg_id))
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return ticket_id

def update_support_ticket_status(ticket_id, status=None, reply=None, replied_at=None, channel_msg_id=None):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        if status:
            fields.append('status=?')
            values.append(status)
        if reply:
            fields.append('reply=?')
            values.append(reply)
        if replied_at:
            fields.append('replied_at=?')
            values.append(replied_at)
        if channel_msg_id:
            fields.append('channel_msg_id=?')
            values.append(channel_msg_id)
        if not fields:
            conn.close()
            return
        values.append(ticket_id)
        cursor.execute(f'UPDATE support_tickets SET {", ".join(fields)} WHERE id=?', values)
        conn.commit()
        conn.close()

def get_support_ticket_by_id(ticket_id):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, user_id, username, full_name, message, status, created_at, channel_msg_id, reply, replied_at FROM support_tickets WHERE id=?', (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            'id': row[0],
            'user_id': row[1],
            'username': row[2],
            'full_name': row[3],
            'message': row[4],
            'status': row[5],
            'created_at': row[6],
            'channel_msg_id': row[7],
            'reply': row[8],
            'replied_at': row[9]
        }

def get_all_support_tickets(status=None):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute('SELECT * FROM support_tickets WHERE status=? ORDER BY created_at DESC', (status,))
        else:
            cursor.execute('SELECT * FROM support_tickets ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return rows

def delete_support_ticket(ticket_id):
    """Удаляет тикет поддержки по ID"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM support_tickets WHERE id=?', (ticket_id,))
        conn.commit()
        conn.close()
        return True

def clear_all_support_tickets():
    """Удаляет все тикеты поддержки"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM support_tickets')
        conn.commit()
        conn.close()
        return True

# --- АДМИНСКИЕ НАСТРОЙКИ ---
def get_admin_setting(key, default=""):
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM admin_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default

def update_admin_setting(key, value):
    """Обновляет значение настройки админки"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT OR REPLACE INTO admin_settings (key, value) VALUES (?, ?)''', (key, value))
        conn.commit()
        conn.close()

def get_all_admin_settings():
    """Получает все настройки админки"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value, description FROM admin_settings ORDER BY key')
        result = cursor.fetchall()
        conn.close()
        return result

# --- СЛОТ-МАШИНА ---
def get_slot_configs():
    """Получает все конфигурации слот-машины"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, combination, reward_type, reward_amount, chance_percent, emoji, name FROM slot_config ORDER BY chance_percent DESC')
        result = cursor.fetchall()
        conn.close()
        return result

def add_slot_config(combination, reward_type, reward_amount, chance_percent, emoji, name):
    """Добавляет новую конфигурацию слот-машины"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO slot_config (combination, reward_type, reward_amount, chance_percent, emoji, name) 
                         VALUES (?, ?, ?, ?, ?, ?)''', (combination, reward_type, reward_amount, chance_percent, emoji, name))
        conn.commit()
        conn.close()

def delete_slot_config(config_id):
    """Удаляет конфигурацию слот-машины"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM slot_config WHERE id = ?', (config_id,))
        conn.commit()
        conn.close()

def get_user_slot_spins(tg_id):
    """Получает количество использованных спинов пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT slot_spins_used, slot_last_reset FROM users WHERE tg_id = ?', (tg_id,))
        result = cursor.fetchone()
        conn.close()
        return result if result else (0, None)

def use_slot_spin(tg_id):
    """Использует один спин пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET slot_spins_used = slot_spins_used + 1 WHERE tg_id = ?', (tg_id,))
        conn.commit()
        conn.close()

def reset_slot_spins(tg_id):
    """Сбрасывает спинны пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET slot_spins_used = 0, slot_last_reset = ? WHERE tg_id = ?', 
                      (datetime.datetime.now().strftime("%Y-%m-%d"), tg_id))
        conn.commit()
        conn.close()

def create_slot_win(tg_id, combination, reward_type, reward_amount, is_win):
    """Создает запись о выигрыше в слот-машине с правильным статусом"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Определяем статус в зависимости от типа награды
        if reward_type == "money":
            # Деньги зачисляются автоматически, поэтому статус "completed"
            status = "completed"
        else:
            # Звезды и TON требуют подтверждения админа, поэтому статус "pending"
            status = "pending"

        cursor.execute('''INSERT INTO slot_machine (user_id, combination, reward_type, reward_amount, is_win, status, created_at)
                         VALUES ((SELECT id FROM users WHERE tg_id = ?), ?, ?, ?, ?, ?, ?)''',
                      (tg_id, combination, reward_type, reward_amount, is_win, status, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        win_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return win_id

def get_slot_wins(status="pending"):
    """Получает все выигрыши слот-машины с определенным статусом"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT sm.id, sm.user_id, u.tg_id, u.full_name, sm.combination, sm.reward_type, 
                         sm.reward_amount, sm.is_win, sm.created_at, sm.status, sm.admin_msg_id
                         FROM slot_machine sm 
                         JOIN users u ON sm.user_id = u.id 
                         WHERE sm.status = ? ORDER BY sm.created_at DESC''', (status,))
        result = cursor.fetchall()
        conn.close()
        return result

def update_slot_win_status(win_id, status, admin_msg_id=None):
    """Обновляет статус выигрыша слот-машины"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        if admin_msg_id:
            cursor.execute('UPDATE slot_machine SET status = ?, admin_msg_id = ? WHERE id = ?', (status, admin_msg_id, win_id))
        else:
            cursor.execute('UPDATE slot_machine SET status = ? WHERE id = ?', (status, win_id))
        conn.commit()
        conn.close()

def update_slot_win_status_with_extra(win_id, status, extra_data=None, admin_msg_id=None):
    """Обновляет статус выигрыша слот-машины с дополнительными данными"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        if extra_data and admin_msg_id:
            cursor.execute('UPDATE slot_machine SET status = ?, extra_data = ?, admin_msg_id = ? WHERE id = ?',
                         (status, extra_data, admin_msg_id, win_id))
        elif extra_data:
            cursor.execute('UPDATE slot_machine SET status = ?, extra_data = ? WHERE id = ?',
                         (status, extra_data, win_id))
        elif admin_msg_id:
            cursor.execute('UPDATE slot_machine SET status = ?, admin_msg_id = ? WHERE id = ?',
                         (status, admin_msg_id, win_id))
        else:
            cursor.execute('UPDATE slot_machine SET status = ? WHERE id = ?', (status, win_id))

        conn.commit()
        conn.close()

def get_slot_win_by_id(win_id):
    """Получает выигрыш слот-машины по ID"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT sm.id, sm.user_id, u.tg_id, u.full_name, sm.combination, sm.reward_type,
                         sm.reward_amount, sm.is_win, sm.created_at, sm.status, sm.extra_data
                         FROM slot_machine sm
                         JOIN users u ON sm.user_id = u.id
                         WHERE sm.id = ?''', (win_id,))
        result = cursor.fetchone()
        conn.close()
        return result

# --- КАЛЕНДАРЬ АКТИВНОСТИ ---
def get_activity_rewards():
    """Получает все награды активности"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, days_required, reward_type, reward_amount, description FROM activity_rewards ORDER BY days_required')
        result = cursor.fetchall()
        conn.close()
        return result

def add_activity_reward(days_required, reward_type, reward_amount, description):
    """Добавляет новую награду активности"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO activity_rewards (days_required, reward_type, reward_amount, description) 
                         VALUES (?, ?, ?, ?)''', (days_required, reward_type, reward_amount, description))
        conn.commit()
        conn.close()

def delete_activity_reward(reward_id):
    """Удаляет награду активности"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM activity_rewards WHERE id = ?', (reward_id,))
        conn.commit()
        conn.close()

def get_user_activity(tg_id, date=None):
    """Получает активность пользователя за определенную дату"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        if date:
            cursor.execute('''SELECT * FROM activity_calendar 
                             WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND date = ?''', (tg_id, date))
        else:
            cursor.execute('''SELECT * FROM activity_calendar 
                             WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) 
                             ORDER BY date DESC LIMIT 30''', (tg_id,))
        result = cursor.fetchall()
        conn.close()
        return result

def mark_activity(tg_id, date, activity_type="daily"):
    """Отмечает активность пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, есть ли уже активность на эту дату
        cursor.execute('''SELECT COUNT(*) FROM activity_calendar
                         WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)
                         AND date = ? AND activity_type = ?''', (tg_id, date, activity_type))

        existing = cursor.fetchone()[0]

        if existing == 0:
            cursor.execute('''INSERT INTO activity_calendar (user_id, date, activity_type, created_at)
                             VALUES ((SELECT id FROM users WHERE tg_id = ?), ?, ?, ?)''',
                          (tg_id, date, activity_type, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

        conn.close()

def get_user_activity_streak(tg_id):
    """Получает текущую серию активности пользователя (непрерывную)"""
    import datetime

    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем пользователя
        cursor.execute('SELECT id FROM users WHERE tg_id = ?', (tg_id,))
        user_result = cursor.fetchone()
        if not user_result:
            conn.close()
            return 0

        user_id = user_result[0]
        today = datetime.datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        streak = 0

        # Сначала проверяем, есть ли активность сегодня
        cursor.execute('''SELECT COUNT(*) FROM activity_calendar
                         WHERE user_id = ? AND date = ?''', (user_id, today_str))
        today_result = cursor.fetchone()

        # Если есть активность сегодня, включаем её в streak
        if today_result and today_result[0] > 0:
            streak = 1
            start_day = 1  # Начинаем проверку с вчерашнего дня
        else:
            start_day = 1  # Начинаем проверку с вчерашнего дня

        # Проверяем активность за предыдущие дни подряд
        for i in range(start_day, 365):  # Максимум год назад
            check_date = today - datetime.timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")

            cursor.execute('''SELECT COUNT(*) FROM activity_calendar
                             WHERE user_id = ? AND date = ?''', (user_id, date_str))
            result = cursor.fetchone()

            if result and result[0] > 0:
                streak += 1
            else:
                break  # Прерываем серию при первом пропуске

        conn.close()
        return streak

def claim_activity_reward(tg_id, reward_id):
    """Получает награду за активность"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Получаем информацию о награде
        cursor.execute('SELECT days_required, reward_type, reward_amount FROM activity_rewards WHERE id = ?', (reward_id,))
        reward = cursor.fetchone()
        if not reward:
            conn.close()
            return False
        days_required, reward_type, reward_amount = reward
        # Проверяем, достиг ли пользователь нужного количества дней
        cursor.execute('''SELECT COUNT(*) FROM activity_calendar \
                         WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) \
                         AND date >= date('now', '-30 days')''', (tg_id,))
        user_days = cursor.fetchone()[0]
        # Проверяем, не была ли награда уже получена
        cursor.execute('''SELECT COUNT(*) FROM activity_calendar \
                         WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) \
                         AND activity_type = 'reward' \
                         AND reward_type = ? \
                         AND reward_amount = ?''', (tg_id, reward_type, reward_amount))
        already_claimed = cursor.fetchone()[0]
        if already_claimed:
            conn.close()
            return False
        if user_days >= days_required:
            # Начисляем награду в зависимости от типа
            if reward_type in ("balance", "money"):
                cursor.execute('UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE tg_id = ?', (reward_amount, tg_id))
            # Для stars и ton заказы создаются в обработчике, здесь только отмечаем награду как полученную
            # Отмечаем награду как полученную
            cursor.execute('''INSERT INTO activity_calendar (user_id, date, activity_type, reward_type, reward_amount, claimed, created_at) \
                             VALUES ((SELECT id FROM users WHERE tg_id = ?), ?, 'reward', ?, ?, 1, ?)''',
                          (tg_id, datetime.datetime.now().strftime("%Y-%m-%d"), reward_type, reward_amount, 
                           datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False

# --- РЕФЕРАЛЬНЫЕ ПРОЦЕНТЫ ---
def get_user_referral_percent(tg_id):
    """Получает процент рефералов пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT referral_percent FROM users WHERE tg_id = ?', (tg_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 5.0

def update_user_referral_percent(tg_id, percent):
    """Обновляет процент рефералов пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET referral_percent = ? WHERE tg_id = ?', (percent, tg_id))
        conn.commit()
        conn.close()

def get_user_by_username(username):
    """Получить пользователя по юзернейму (поиск без учета регистра)"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Убираем @ если есть и приводим к нижнему регистру
        clean_username = username.lstrip('@').lower()
        cursor.execute('SELECT id, tg_id, full_name, username, referral_percent FROM users WHERE LOWER(username) = ?', (clean_username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                'id': result[0],
                'tg_id': result[1],
                'full_name': result[2],
                'username': result[3],
                'referral_percent': result[4] if result[4] is not None else 5.0
            }
        return None

def update_user_referral_percent_by_username(username, percent):
    """Обновить реферальный процент пользователя по юзернейму"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Убираем @ если есть
        clean_username = username.lstrip('@')
        cursor.execute('UPDATE users SET referral_percent = ? WHERE username = ?', (percent, clean_username))
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        return affected_rows > 0

# --- УТИЛИТЫ ---
def calculate_withdrawal_commission(amount: float) -> Tuple[float, float]:
    """
    Рассчитывает комиссию при выводе средств
    Возвращает: (комиссия, сумма к выплате)
    """
    commission_percent = float(get_admin_setting('withdrawal_commission', '3.0'))
    commission = amount * (commission_percent / 100)
    final_amount = amount - commission
    return commission, final_amount

def calculate_stars_price(stars_count):
    """Рассчитать цену звезд на основе настроек"""
    rate_low = float(get_admin_setting('stars_rate_low', '1.65'))
    rate_high = float(get_admin_setting('stars_rate_high', '1.6'))
    threshold = int(get_admin_setting('stars_threshold', '1500'))
    
    if stars_count <= threshold:
        return int(stars_count * rate_low)
    else:
        return int(stars_count * rate_high)

def get_daily_attempts_reset_time():
    """Получить время до сброса дневных попыток"""
    import datetime
    reset_hour = int(get_admin_setting('slot_reset_hour', '0'))
    now = datetime.datetime.now()
    reset_time = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    
    if now.hour >= reset_hour:
        reset_time += datetime.timedelta(days=1)
    
    return reset_time

def should_reset_daily_attempts(tg_id):
    """Проверить, нужно ли сбросить дневные попытки"""
    import datetime
    last_reset = get_user_slot_spins(tg_id)[1]
    if not last_reset:
        return True
    
    last_reset_date = datetime.datetime.fromisoformat(last_reset)
    reset_time = get_daily_attempts_reset_time()
    
    return last_reset_date.date() < reset_time.date()

# --- ПОДЕЛИТЬСЯ ИСТОРИЕЙ ---
def get_user_share_story_status(tg_id):
    """Получает статус использования истории пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT share_story_used, share_story_last_reset FROM users WHERE tg_id = ?', (tg_id,))
        result = cursor.fetchone()
        conn.close()
        return result if result else (0, None)

def use_share_story(tg_id):
    """Использует возможность поделиться историей"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET share_story_used = share_story_used + 1 WHERE tg_id = ?', (tg_id,))
        conn.commit()
        conn.close()

def reset_share_story(tg_id):
    """Сбрасывает использование истории"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET share_story_used = 0, share_story_last_reset = ? WHERE tg_id = ?', 
                      (datetime.datetime.now().strftime("%Y-%m-%d"), tg_id))
        conn.commit()
        conn.close()

def delete_slot_win(win_id):
    """Удаляет выигрыш слот-машины"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM slot_machine WHERE id = ?', (win_id,))
        conn.commit()
        conn.close()

def init_activity_rewards_custom():
    """Инициализация наград календаря активности по новому списку"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM activity_rewards")
        rewards = [
            (3, 'money', 15, '3 дня — 15₽ на баланс'),
            (7, 'money', 50, '7 дней — 50₽ на баланс'),
            (15, 'stars', 13, '15 дней — 13⭐️'),
            (21, 'stars', 21, '21 день — 21⭐️'),
            (28, 'ton', 0.1, '28 дней — 0.1 TON'),
            (30, 'ton', 0.5, '30 дней — 0.5 TON'),
        ]
        for days, reward_type, reward_amount, description in rewards:
            cursor.execute(
                "INSERT INTO activity_rewards (days_required, reward_type, reward_amount, description) VALUES (?, ?, ?, ?)",
                (days, reward_type, reward_amount, description)
            )
        conn.commit()
        conn.close()

def create_roulette_tables():
    """Синхронная обёртка для асинхронной функции создания таблиц рулетки"""
    import asyncio
    asyncio.run(_create_roulette_tables_async())

async def _create_roulette_tables_async():
    import aiosqlite
    async with aiosqlite.connect('data/users.db') as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roulette_config (
                id INTEGER PRIMARY KEY,
                combination TEXT UNIQUE,
                reward_type TEXT,
                reward_amount INTEGER,
                chance_percent REAL,
                emoji TEXT,
                name TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roulette_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                combination TEXT,
                reward_type TEXT,
                reward_amount INTEGER,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roulette_attempts (
                user_id INTEGER PRIMARY KEY,
                attempts_used INTEGER DEFAULT 0,
                last_reset TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referral_attempts_given (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_user_id INTEGER,
                attempts_given INTEGER DEFAULT 2,
                given_at TEXT,
                UNIQUE(referrer_id, referred_user_id)
            )
        """)
        await db.commit()

async def get_weighted_slot_combination():
    """Генерирует взвешенную комбинацию для слот-машины"""
    slot_weights = {
        "🍒": 30,
        "🍋": 25,
        "🍊": 20,
        "🍇": 15,
        "⭐": 5,
        "💎": 3,
        "🔔": 1,
        "💰": 1,
        "🎰": 0.5,
        "7️⃣": 0.5
    }
    
    # Нормализуем веса
    total_weight = sum(slot_weights.values())
    normalized_weights = {k: v/total_weight for k, v in slot_weights.items()}
    
    # Выбираем 3 символа с учетом весов
    symbols = list(normalized_weights.keys())
    weights = list(normalized_weights.values())
    
    combination = ''.join(random.choices(symbols, weights=weights, k=3))
    return combination


def init_roulette_configs():
    """Синхронная обёртка для асинхронной функции инициализации конфигов рулетки"""
    import asyncio
    asyncio.run(_init_roulette_configs_async())

async def _init_roulette_configs_async():
    import aiosqlite
    async with aiosqlite.connect('data/users.db') as db:
        await db.execute("DELETE FROM roulette_config")
        configs = [
            ("🍒🍒🍒", "money", 5, 17.0, "🍒", "5₽"),
            ("🍋🍋🍋", "money", 10, 16.0, "🍋", "10₽"),
            ("🍊🍊🍊", "money", 30, 13.0, "🍊", "30₽"),
            ("🍇🍇🍇", "stars", 13, 4.0, "🍇", "13⭐️"),
            ("🍊🍊🍊", "stars", 21, 2.0, "🍊", "21⭐️"),
            ("💎💎💎", "ton", 0.5, 1.0, "💎", "0.5 TON"),
            ("⭐️⭐️⭐️", "stars", 50, 0.7, "⭐️", "50⭐️"),
            ("🔔🔔🔔", "money", 100, 0.4, "🔔", "100₽"),
            ("💰💰💰", "stars", 75, 0.3, "💰", "75⭐️"),
            ("🎰🎰🎰", "ton", 1.0, 0.1, "🎰", "1 TON"),
            ("7️⃣7️⃣7️⃣", "stars", 100, 0.05, "7️⃣", "100⭐️"),
        ]
        for combination, reward_type, reward_amount, chance_percent, emoji, name in configs:
            await db.execute(
                "INSERT INTO roulette_config (combination, reward_type, reward_amount, chance_percent, emoji, name) VALUES (?, ?, ?, ?, ?, ?)",
                (combination, reward_type, reward_amount, chance_percent, emoji, name)
            )
        await db.commit()

def get_flag(key: str, default: str = 'false') -> bool:
    val = get_admin_setting(key, default)
    if val is None:
        return False
    return str(val).lower() in ['true', '1', 'on', 'yes', 'вкл']

def set_flag(key: str, value: bool):
    update_admin_setting(key, 'true' if value else 'false')

def add_stars_to_user(tg_id, stars):
    """Начисляет пользователю звёзды (увеличивает баланс)"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE tg_id = ?', (stars, tg_id))
        conn.commit()
        conn.close()

def add_ton_to_user(tg_id, ton_amount):
    """Логирует выдачу TON пользователю (можно доработать под реальную интеграцию)"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Просто логируем в activity_calendar как отдельную запись
        cursor.execute('''INSERT INTO activity_calendar (user_id, date, activity_type, reward_type, reward_amount, claimed, created_at) \
                         VALUES ((SELECT id FROM users WHERE tg_id = ?), ?, 'reward', 'ton', ?, 1, ?)''',
                      (tg_id, datetime.datetime.now().strftime("%Y-%m-%d"), ton_amount, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

# Асинхронные функции рулетки
async def get_user_roulette_attempts(user_id: int):
    async with aiosqlite.connect('data/users.db') as db:
        cursor = await db.execute("SELECT attempts_used, last_reset FROM roulette_attempts WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row if row else (0, None)

async def use_roulette_attempt(user_id: int):
    async with aiosqlite.connect('data/users.db') as db:
        row = await db.execute("SELECT attempts_used, last_reset FROM roulette_attempts WHERE user_id = ?", (user_id,))
        data = await row.fetchone()
        today = datetime.date.today().isoformat()
        if not data or data[1] != today:
            await db.execute("REPLACE INTO roulette_attempts (user_id, attempts_used, last_reset) VALUES (?, ?, ?)", (user_id, 1, today))
        else:
            await db.execute("UPDATE roulette_attempts SET attempts_used = attempts_used + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def reset_roulette_attempts(user_id: int):
    async with aiosqlite.connect('data/users.db') as db:
        today = datetime.date.today().isoformat()
        await db.execute("REPLACE INTO roulette_attempts (user_id, attempts_used, last_reset) VALUES (?, ?, ?)", (user_id, 0, today))
        await db.commit()

async def add_referral_bonus_for_order_async(user_id: int, order_amount: float, order_type: str):
    """
    Асинхронно начисляет реферальный бонус пригласившему за подтвержденный заказ
    """
    try:
        async with aiosqlite.connect('data/users.db') as db:
            # Получаем профиль пользователя
            cursor = await db.execute('SELECT referrer_id FROM users WHERE id = ?', (user_id,))
            user_row = await cursor.fetchone()
            
            if not user_row or not user_row[0]:
                logging.info(f"[REFERRAL] Пользователь {user_id} не имеет пригласившего")
                return False, None  # Нет пригласившего
            
            referrer_id = user_row[0]
            
            # Получаем профиль пригласившего
            cursor = await db.execute('SELECT tg_id, full_name, username, referral_percent FROM users WHERE id = ?', (referrer_id,))
            referrer_row = await cursor.fetchone()
            
            if not referrer_row:
                logging.error(f"[REFERRAL] Не найден профиль пригласившего {referrer_id}")
                return False, None
            
            referrer_tg_id, referrer_name, referrer_username, referral_percent = referrer_row
            
            # Используем настраиваемый процент или дефолтный 5%
            if referral_percent is None:
                referral_percent = 5.0
            
            # Рассчитываем бонус
            bonus_amount = order_amount * (referral_percent / 100)
            
            # Начисляем бонус на баланс пригласившего
            await db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (bonus_amount, referrer_id))
            await db.commit()
            
            logging.info(f"[REFERRAL] Начислен бонус {bonus_amount:.2f}₽ пользователю {referrer_tg_id} за заказ {order_type}")
            
            return True, {
                'referrer_tg_id': referrer_tg_id,
                'referrer_name': referrer_name,
                'referrer_username': referrer_username,
                'bonus_amount': bonus_amount,
                'referral_percent': referral_percent,
                'order_amount': order_amount,
                'order_type': order_type
            }
            
    except Exception as e:
        logging.error(f"[REFERRAL] Ошибка начисления реферального бонуса: {e}")
        return False, None

async def check_referral_attempts_given_async(user_id: int, referrer_id: int) -> bool:
    """
    Асинхронно проверяет, были ли уже начислены попытки за этого реферала
    """
    try:
        async with aiosqlite.connect('data/users.db') as db:
            # Проверяем, было ли уже начисление
            cursor = await db.execute('SELECT id FROM referral_attempts_given WHERE referrer_id = ? AND referred_user_id = ?', 
                                     (referrer_id, user_id))
            
            result = await cursor.fetchone()
            return result is not None
            
    except Exception as e:
        logging.error(f"[REFERRAL] Ошибка проверки начислений: {e}")
        return False

async def mark_referral_attempts_given_async(user_id: int, referrer_id: int, attempts: int = 2):
    """
    Асинхронно отмечает, что попытки за этого реферала уже были начислены
    """
    try:
        async with aiosqlite.connect('data/users.db') as db:
            # Записываем начисление
            await db.execute('''
                INSERT OR REPLACE INTO referral_attempts_given 
                (referrer_id, referred_user_id, attempts_given, given_at) 
                VALUES (?, ?, ?, ?)
            ''', (referrer_id, user_id, attempts, datetime.datetime.now().isoformat()))
            
            await db.commit()
            logging.info(f"[REFERRAL] Отмечено начисление {attempts} попыток за реферала {user_id} пригласившему {referrer_id}")
            
    except Exception as e:
        logging.error(f"[REFERRAL] Ошибка записи начисления: {e}")

def add_ton_slot_win(tg_id, ton_amount, combination):
    """Создает заявку на выплату TON за выигрыш в слот-машине"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        user_profile = get_user_profile(tg_id)
        if not user_profile:
            conn.close()
            return None
        user_id = user_profile['id']
        cursor.execute('''INSERT INTO orders (user_id, order_type, amount, status, created_at, extra_data) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (user_id, 'slot_ton', ton_amount, 'pending', 
                       datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                       f'TON за выигрыш в слот-машине: {combination}'))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return order_id

def reset_user_activity(user_id):
    """Сбрасывает активность пользователя на новый день"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.date.today().isoformat()
        cursor.execute('''INSERT OR REPLACE INTO user_activity (user_id, last_activity_date, activity_count) 
                         VALUES (?, ?, ?)''', (user_id, today, 0))
        conn.commit()
        conn.close()

def check_and_reset_activity_streak(user_id):
    """Проверяет и сбрасывает серию активности пользователя"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT last_activity_date, activity_count FROM user_activity WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        today = datetime.date.today().isoformat()
        
        if not row:
            cursor.execute('''INSERT INTO user_activity (user_id, last_activity_date, activity_count) 
                             VALUES (?, ?, ?)''', (user_id, today, 1))
            conn.commit()
            conn.close()
            return 1
        
        last_date, count = row
        if last_date != today:
            cursor.execute('''UPDATE user_activity SET last_activity_date = ?, activity_count = ? 
                             WHERE user_id = ?''', (today, 1, user_id))
            conn.commit()
            conn.close()
            return 1
        else:
            conn.close()
            return count

def clear_all_calendar_data():
    """Очищает всю историю активности пользователей (таблица activity_calendar)"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM activity_calendar')
        conn.commit()
        conn.close()
        return True

def clear_all_activity_prizes():
    """Очищает все призы активности (таблица activity_rewards)"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM activity_rewards')
        conn.commit()
        conn.close()
        return True

def clear_all_slot_data():
    """Очищает всю историю выигрышей и спинов слот-машины (таблица slot_machine)"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM slot_machine')
        cursor.execute('UPDATE users SET slot_spins_used = 0, slot_last_reset = NULL')
        conn.commit()
        conn.close()
        return True

def clear_all_slot_prizes():
    """Очищает все призы слот-машины (таблица slot_config)"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM slot_config')
        conn.commit()
        conn.close()
        return True

def reset_all_prizes():
    """Восстанавливает все призы слот-машины и активности"""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Восстанавливаем призы слот-машины (УМЕНЬШЕННЫЕ В 5 РАЗ ШАНСЫ)
            cursor.execute("DELETE FROM slot_config")
            default_slot_configs = [
                ('🍒🍒🍒', 'money', 2, 1.2, '🍒', 'Вишни'),           # 1.2% - 2₽ (было 6%)
                ('🍊🍊🍊', 'stars', 4, 0.6, '🍊', 'Апельсин'),        # 0.6% - 4⭐ (было 3%)
                ('🍋🍋🍋', 'money', 5, 0.4, '🍋', 'Лимон'),           # 0.4% - 5₽ (было 2%)
                ('🍇🍇🍇', 'stars', 8, 0.16, '🍇', 'Виноград'),       # 0.16% - 8⭐ (было 0.8%)
                ('💎💎💎', 'ton', 0.3, 0.1, '💎', 'Алмаз'),          # 0.1% - 0.3 TON (было 0.5%)
                ('⭐️⭐️⭐️', 'stars', 25, 0.06, '⭐️', 'Звезды'),       # 0.06% - 25⭐ (было 0.3%)
                ('🔔🔔🔔', 'money', 50, 0.04, '🔔', 'Колокольчик'),   # 0.04% - 50₽ (было 0.2%)
                ('💰💰💰', 'stars', 40, 0.03, '💰', 'Мешок денег'),  # 0.03% - 40⭐ (было 0.15%)
                ('🎰🎰🎰', 'ton', 0.8, 0.01, '🎰', 'Джекпот'),       # 0.01% - 0.8 TON (было 0.05%)
                ('7️⃣7️⃣7️⃣', 'stars', 100, 0.004, '7️⃣', 'Счастливая семерка'), # 0.004% - 100⭐ (было 0.02%)
            ]
            
            for combo, reward_type, reward_amount, chance, emoji, name in default_slot_configs:
                cursor.execute('''
                    INSERT INTO slot_config (combination, reward_type, reward_amount, chance_percent, emoji, name)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (combo, reward_type, reward_amount, chance, emoji, name))
            
            # Восстанавливаем призы активности
            cursor.execute("DELETE FROM activity_rewards")
            default_activity_rewards = [
                (7, 'stars', 50, 'Недельная активность'),
                (14, 'stars', 150, 'Двухнедельная активность'),
                (30, 'stars', 500, 'Месячная активность'),
                (7, 'money', 100, 'Недельная активность (деньги)'),
                (14, 'money', 300, 'Двухнедельная активность (деньги)'),
                (30, 'money', 1000, 'Месячная активность (деньги)'),
            ]
            
            for days, reward_type, reward_amount, description in default_activity_rewards:
                cursor.execute('''
                    INSERT INTO activity_rewards (days_required, reward_type, reward_amount, description)
                    VALUES (?, ?, ?, ?)
                ''', (days, reward_type, reward_amount, description))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            logging.error(f"[ERROR] Ошибка при восстановлении призов: {e}")
            return False
        finally:
            conn.close()

def delete_user_everywhere_full(tg_id):
    """
    Полностью удаляет пользователя и все связанные с ним данные из всех таблиц
    """
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Получаем user_id
        cursor.execute('SELECT id FROM users WHERE tg_id=?', (tg_id,))
        user = cursor.fetchone()
        user_id = user[0] if user else None

        # Удаляем из связанных таблиц
        if user_id:
            # Основные таблицы пользователя
            cursor.execute('DELETE FROM roulette_attempts WHERE user_id=?', (user_id,))
            cursor.execute('DELETE FROM referral_attempts_given WHERE referrer_id=? OR referred_user_id=?', (user_id, user_id))
            cursor.execute('DELETE FROM activity_calendar WHERE user_id=?', (user_id,))
            cursor.execute('DELETE FROM orders WHERE user_id=?', (user_id,))
            cursor.execute('DELETE FROM withdrawals WHERE user_id=?', (user_id,))
            cursor.execute('DELETE FROM reviews WHERE user_id=?', (user_id,))

            # Дополнительные таблицы (проверяем существование)
            try:
                cursor.execute('DELETE FROM slot_machine WHERE user_id=?', (user_id,))
            except sqlite3.OperationalError:
                pass  # Таблица не существует

            try:
                cursor.execute('DELETE FROM roulette_history WHERE user_id=?', (user_id,))
            except sqlite3.OperationalError:
                pass  # Таблица не существует

            try:
                cursor.execute('DELETE FROM activity_rewards WHERE user_id=?', (user_id,))
            except sqlite3.OperationalError:
                pass  # Таблица не существует

            try:
                cursor.execute('DELETE FROM bonus_attempts WHERE user_id=?', (user_id,))
            except sqlite3.OperationalError:
                pass  # Таблица не существует

            try:
                cursor.execute('DELETE FROM user_activity WHERE user_id=?', (user_id,))
            except sqlite3.OperationalError:
                pass  # Таблица не существует

            try:
                cursor.execute('DELETE FROM support_tickets WHERE user_id=?', (user_id,))
            except sqlite3.OperationalError:
                pass  # Таблица не существует

            # Обновляем рефералов - убираем связь с удаляемым пользователем
            cursor.execute('UPDATE users SET referrer_id = NULL WHERE referrer_id = ?', (user_id,))

        # Удаляем самого пользователя
        cursor.execute('DELETE FROM users WHERE tg_id=?', (tg_id,))
        conn.commit()
        conn.close()
        logging.warning(f"[DELETE_USER] Полностью удалён пользователь tg_id={tg_id}, user_id={user_id} из всех таблиц")

async def get_referral_attempts(user_id: int) -> int:
    """Возвращает текущее количество использованных попыток (может быть отрицательным)"""
    async with aiosqlite.connect('data/users.db') as db:
        row = await db.execute("SELECT attempts_used, last_reset FROM roulette_attempts WHERE user_id = ?", (user_id,))
        data = await row.fetchone()
        return data[0] if data else 0

async def inc_referral_attempts(user_id: int, attempts: int = 2, db=None):
    """
    Инкрементирует попытки пригласившему пользователю (делает attempts_used более отрицательным)
    :param user_id: ID пользователя
    :param attempts: Сколько попыток добавить (по умолчанию 2)
    :param db: (опционально) открытое соединение aiosqlite.Connection
    """
    try:
        close_db = False
        if db is None:
            import aiosqlite
            db = await aiosqlite.connect('data/users.db')
            close_db = True
        
        cursor = await db.execute("SELECT attempts_used, last_reset FROM roulette_attempts WHERE user_id = ?", (user_id,))
        data = await cursor.fetchone()
        today = datetime.date.today().isoformat()
        
        if not data or data[1] != today:
            await db.execute("REPLACE INTO roulette_attempts (user_id, attempts_used, last_reset) VALUES (?, ?, ?)", (user_id, -attempts, today))
        else:
            await db.execute("UPDATE roulette_attempts SET attempts_used = attempts_used - ? WHERE user_id = ?", (attempts, user_id))
        
        # Коммитим изменения всегда, независимо от того, кто открыл соединение
        await db.commit()
        
        # Закрываем соединение только если мы его открывали
        if close_db:
            await db.close()
            
        logging.info(f"[REFERRAL] Инкрементировано {attempts} попыток пользователю {user_id}")
        return True
        
    except Exception as e:
        logging.error(f"[REFERRAL] Ошибка инкремента попыток: {e}")
        return False

async def get_unclaimed_referrals_count(referrer_id: int) -> int:
    """
    Возвращает количество неактивированных рефералов для пользователя
    """
    try:
        async with aiosqlite.connect('data/users.db') as db:
            # Получаем всех рефералов пользователя
            cursor = await db.execute('SELECT id FROM users WHERE referrer_id = ?', (referrer_id,))
            all_referrals = await cursor.fetchall()
            
            if not all_referrals:
                return 0
            
            # Преобразуем в список для корректной работы с len()
            all_referrals_list = list(all_referrals)
            
            # Проверяем, сколько из них уже активированы (есть в таблице referral_attempts_given)
            activated_count = 0
            for referral in all_referrals_list:
                referred_user_id = referral[0]
                cursor = await db.execute('SELECT id FROM referral_attempts_given WHERE referrer_id = ? AND referred_user_id = ?', 
                                         (referrer_id, referred_user_id))
                result = await cursor.fetchone()
                if result:
                    activated_count += 1
            
            unclaimed_count = len(all_referrals_list) - activated_count
            logging.info(f"[REFERRAL] Пользователь {referrer_id}: всего рефералов {len(all_referrals_list)}, активировано {activated_count}, неактивировано {unclaimed_count}")
            return unclaimed_count
            
    except Exception as e:
        logging.error(f"[REFERRAL] Ошибка подсчета неактивированных рефералов: {e}")
        return 0

async def claim_referral_bonus(referrer_id: int) -> tuple[bool, int, int]:
    """
    Активирует все неактивированные реферальные бонусы для пользователя
    Возвращает: (успех, количество активированных рефералов, общее количество попыток)
    """
    try:
        import aiosqlite
        async with aiosqlite.connect('data/users.db') as db:
            # Получаем всех рефералов пользователя
            cursor = await db.execute('SELECT id FROM users WHERE referrer_id = ?', (referrer_id,))
            all_referrals = await cursor.fetchall()
            if not all_referrals:
                return False, 0, 0
            activated_count = 0
            total_attempts = 0
            for referral in all_referrals:
                referred_user_id = referral[0]
                
                # Проверяем, был ли уже активирован этот реферал (есть ли в таблице referral_attempts_given)
                cursor = await db.execute('SELECT id FROM referral_attempts_given WHERE referrer_id = ? AND referred_user_id = ?', 
                                         (referrer_id, referred_user_id))
                result = await cursor.fetchone()
                
                if not result:
                    # Активируем реферала (добавляем в таблицу referral_attempts_given)
                    await db.execute('''
                        INSERT OR REPLACE INTO referral_attempts_given 
                        (referrer_id, referred_user_id, attempts_given, given_at) 
                        VALUES (?, ?, ?, ?)
                    ''', (referrer_id, referred_user_id, 2, datetime.datetime.now().isoformat()))
                    
                    activated_count += 1
                    total_attempts += 2
            
            if activated_count > 0:
                # Коммитим изменения в таблице referral_attempts_given
                await db.commit()
                
                # Начисляем попытки пользователю (вызываем без передачи db)
                await inc_referral_attempts(referrer_id, total_attempts)
                
                logging.info(f"[REFERRAL] Активировано {activated_count} рефералов, начислено {total_attempts} попыток пользователю {referrer_id}")
                return True, activated_count, total_attempts
            else:
                return False, 0, 0
                
    except Exception as e:
        logging.error(f"[REFERRAL] Ошибка активации реферальных бонусов: {e}")
        return False, 0, 0

async def get_roulette_configs():
    async with aiosqlite.connect('data/users.db') as db:
        cursor = await db.execute('SELECT id, combination, reward_type, reward_amount, chance_percent, emoji, name FROM roulette_config ORDER BY chance_percent DESC')
        result = await cursor.fetchall()
        return result

def update_order_status(order_id, status=None, admin_msg_id=None, extra_data=None):
    import json
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            updates = []
            params = []

            if status is not None:
                updates.append("status = ?")
                params.append(status)

            if admin_msg_id is not None:
                updates.append("admin_msg_id = ?")
                params.append(admin_msg_id)

            if extra_data is not None:
                updates.append("extra_data = ?")
                params.append(json.dumps(extra_data) if isinstance(extra_data, dict) else extra_data)

            if not updates:
                return False

            query = f"UPDATE orders SET {', '.join(updates)} WHERE id = ?"
            params.append(order_id)

            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating order status: {e}")
            return False
        finally:
            conn.close()
        


async def get_slot_wins_async(user_id=None, status=None):
    """Асинхронно получает выигрыши слот-машины из БД"""
    async with aiosqlite.connect('data/users.db') as db:
        if user_id is not None and status is not None:
            # Фильтр по user_id и статусу
            query = '''SELECT sm.id, sm.user_id, u.tg_id, u.full_name, sm.combination, sm.reward_type,
                       sm.reward_amount, sm.is_win, sm.created_at, sm.status, sm.admin_msg_id
                       FROM slot_machine sm
                       JOIN users u ON sm.user_id = u.id
                       WHERE u.tg_id = ? AND sm.status = ? ORDER BY sm.created_at DESC'''
            cursor = await db.execute(query, (user_id, status))
        elif user_id is not None:
            # Фильтр только по user_id
            query = '''SELECT sm.id, sm.user_id, u.tg_id, u.full_name, sm.combination, sm.reward_type,
                       sm.reward_amount, sm.is_win, sm.created_at, sm.status, sm.admin_msg_id
                       FROM slot_machine sm
                       JOIN users u ON sm.user_id = u.id
                       WHERE u.tg_id = ? ORDER BY sm.created_at DESC'''
            cursor = await db.execute(query, (user_id,))
        elif status is not None:
            # Фильтр только по статусу
            query = '''SELECT sm.id, sm.user_id, u.tg_id, u.full_name, sm.combination, sm.reward_type,
                       sm.reward_amount, sm.is_win, sm.created_at, sm.status, sm.admin_msg_id
                       FROM slot_machine sm
                       JOIN users u ON sm.user_id = u.id
                       WHERE sm.status = ? ORDER BY sm.created_at DESC'''
            cursor = await db.execute(query, (status,))
        else:
            # Без фильтров
            query = '''SELECT sm.id, sm.user_id, u.tg_id, u.full_name, sm.combination, sm.reward_type,
                       sm.reward_amount, sm.is_win, sm.created_at, sm.status, sm.admin_msg_id
                       FROM slot_machine sm
                       JOIN users u ON sm.user_id = u.id
                       ORDER BY sm.created_at DESC'''
            cursor = await db.execute(query)

        return await cursor.fetchall()

# Пример использования:
# await add_slot_attempts(123456789, 5)  # Добавить 5 попыток пользователю с ID 123456789

__all__ = [
    'init_db',
    'init_activity_rewards_custom',
    'create_roulette_tables',
    'init_roulette_configs',
    'get_flag',
    'set_flag',
    'get_admin_setting',
    'add_stars_to_user',
    'add_ton_to_user',
    'add_ton_slot_win',
    'reset_user_activity',
    'check_and_reset_activity_streak',
    'get_user_roulette_attempts',
    'use_roulette_attempt',
    'reset_roulette_attempts',
    'save_roulette_win',
    'get_roulette_configs',
    'clear_all_calendar_data',
    'clear_all_activity_prizes',
    'clear_all_slot_data',
    'clear_all_slot_prizes',
    'reset_all_prizes',
    'update_withdrawal_status',
    'delete_user_everywhere_full',
    'get_unclaimed_referrals_count',
    'claim_referral_bonus',
    'check_referral_attempts_given_async',
    'mark_referral_attempts_given_async',
    'inc_referral_attempts',
    # ... другие функции по необходимости ...
]
