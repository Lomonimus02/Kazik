"""
Модуль слот-машины
"""
import asyncio
import datetime
import logging
import random
from typing import Tuple, Optional, List

from app.database.models import (
    get_slot_configs, get_user_slot_spins, use_slot_spin, 
    create_slot_win, should_reset_daily_attempts, reset_slot_spins,
    get_admin_setting, get_slot_wins, get_slot_win_by_id, add_ton_slot_win,
    get_or_create_user, create_order, get_user_profile, update_balance
)
from app.keyboards.main import slot_win_admin_kb
from app.utils.misc import notify_admins

# Настройка логирования
logger = logging.getLogger(__name__)

# Эмодзи для слот-машины (должны соответствовать эмодзи в БД)
SLOT_EMOJIS = ["🍒", "🍋", "🍊", "🍇", "⭐️", "💎", "🔔", "💰", "🎰", "7️⃣"]

# Центрированная рамка для слотов (точно по размеру 3 эмодзи)
CENTERED_FRAME = (
    "┌───────────────┐\n"
    "│   {s1}   |   {s2}   |   {s3}   │\n"
    "└───────────────┘"
)

async def generate_slot_result() -> Tuple[str, str, str]:
    """
    НОВАЯ ЛОГИКА ГЕНЕРАЦИИ РЕЗУЛЬТАТОВ СЛОТ-МАШИНЫ

    Использует правильную систему вероятностей:
    1. Сначала определяется, будет ли выигрыш (общий шанс ~13%)
    2. Если выигрыш - выбирается конкретная комбинация по индивидуальным шансам
    3. Если проигрыш - генерируется случайная невыигрышная комбинация

    Это предотвращает частые выигрыши и обеспечивает правильный баланс.
    """
    configs = get_slot_configs()

    if not configs:
        # Если нет конфигураций, возвращаем случайные символы
        logger.warning("[SLOT] Нет конфигураций слот-машины, возвращаем случайные символы")
        return random.choice(SLOT_EMOJIS), random.choice(SLOT_EMOJIS), random.choice(SLOT_EMOJIS)

    # Вычисляем общий процент выигрышей
    total_win_chance = sum(config[4] for config in configs)  # config[4] = chance_percent
    logger.debug(f"[SLOT] Общий шанс выигрыша: {total_win_chance:.2f}%")

    # Генерируем случайное число от 0 до 100
    random_num = random.uniform(0, 100)
    logger.debug(f"[SLOT] Сгенерировано случайное число: {random_num:.4f}")

    # ЭТАП 1: Определяем, будет ли выигрыш
    if random_num <= total_win_chance:
        # ВЫИГРЫШ! Теперь выбираем конкретную комбинацию
        logger.info(f"[SLOT] Выигрыш! ({random_num:.4f} <= {total_win_chance:.2f}%)")

        # Генерируем новое случайное число для выбора конкретной комбинации
        win_random = random.uniform(0, total_win_chance)
        current_chance = 0

        for config in configs:
            config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = config
            current_chance += chance_percent

            if win_random <= current_chance:
                logger.info(f"[SLOT] Выбрана выигрышная комбинация: {name} ({emoji}{emoji}{emoji})")
                logger.info(f"[SLOT] Приз: {reward_amount} {reward_type}")
                return emoji, emoji, emoji

        # Если по какой-то причине не выбрали комбинацию, берем первую
        first_config = configs[0]
        emoji = first_config[5]
        logger.warning(f"[SLOT] Fallback к первой комбинации: {emoji}{emoji}{emoji}")
        return emoji, emoji, emoji

    else:
        # ПРОИГРЫШ - генерируем невыигрышную комбинацию
        logger.debug(f"[SLOT] Проигрыш ({random_num:.4f} > {total_win_chance:.2f}%)")
        return await _generate_losing_combination(configs)


async def _generate_losing_combination(configs) -> Tuple[str, str, str]:
    """
    Генерирует гарантированно проигрышную комбинацию
    """
    max_attempts = 100  # Увеличиваем количество попыток
    attempts = 0

    # Создаем множество выигрышных эмодзи для быстрой проверки
    winning_emojis = {config[5] for config in configs}  # config[5] = emoji

    while attempts < max_attempts:
        slot1 = random.choice(SLOT_EMOJIS)
        slot2 = random.choice(SLOT_EMOJIS)
        slot3 = random.choice(SLOT_EMOJIS)

        # Проверяем, что это НЕ тройка одинаковых выигрышных эмодзи
        if not (slot1 == slot2 == slot3 and slot1 in winning_emojis):
            # Дополнительно проверяем точные комбинации из БД
            combination = slot1 + slot2 + slot3
            is_winning = any(config[1] == combination for config in configs)

            if not is_winning:
                logger.debug(f"[SLOT] Сгенерирована проигрышная комбинация: {slot1}{slot2}{slot3} (попытка {attempts + 1})")
                return slot1, slot2, slot3

        attempts += 1

    # Если не удалось сгенерировать проигрышную комбинацию, создаем принудительно
    logger.warning(f"[SLOT] Не удалось сгенерировать проигрышную комбинацию за {max_attempts} попыток")

    # Принудительно создаем проигрышную комбинацию
    # Берем 3 разных эмодзи, чтобы гарантированно не было тройки
    available_emojis = [e for e in SLOT_EMOJIS if e not in winning_emojis]

    if len(available_emojis) >= 3:
        # Если есть достаточно неwyигрышных эмодзи
        selected = random.sample(available_emojis, 3)
        logger.debug(f"[SLOT] Принудительная проигрышная комбинация (неwyигрышные эмодзи): {selected[0]}{selected[1]}{selected[2]}")
        return selected[0], selected[1], selected[2]
    else:
        # Если неwyигрышных эмодзи мало, создаем смешанную комбинацию
        slot1 = random.choice(SLOT_EMOJIS)
        slot2 = random.choice([s for s in SLOT_EMOJIS if s != slot1])
        slot3 = random.choice([s for s in SLOT_EMOJIS if s != slot1 and s != slot2])
        logger.debug(f"[SLOT] Принудительная проигрышная комбинация (смешанная): {slot1}{slot2}{slot3}")
        return slot1, slot2, slot3

async def check_win_combination(slot1: str, slot2: str, slot3: str) -> Optional[Tuple]:
    """
    УЛУЧШЕННАЯ ПРОВЕРКА ВЫИГРЫШНЫХ КОМБИНАЦИЙ

    Проверяет комбинацию на соответствие выигрышным конфигурациям из БД.
    Поддерживает как точные комбинации, так и тройки одинаковых эмодзи.
    """
    combination = slot1 + slot2 + slot3
    configs = get_slot_configs()

    logger.debug(f"[SLOT] Проверяем комбинацию: {combination} ({slot1} {slot2} {slot3})")

    if not configs:
        logger.warning("[SLOT] Нет конфигураций для проверки выигрышей")
        return None

    for config in configs:
        config_id, combo, reward_type, reward_amount, chance_percent, emoji, name = config

        # Проверяем точное совпадение комбинации (если задано)
        if combo and combo == combination:
            logger.info(f"[SLOT] ✅ Найдена выигрышная комбинация (точное совпадение): {name}")
            logger.info(f"[SLOT] 🎁 Приз: {reward_amount} {reward_type}")
            return config

        # Проверяем тройку одинаковых эмодзи
        if slot1 == slot2 == slot3 == emoji:
            logger.info(f"[SLOT] ✅ Найдена выигрышная комбинация (тройка эмодзи): {name}")
            logger.info(f"[SLOT] 🎁 Приз: {reward_amount} {reward_type}")
            return config

    logger.debug(f"[SLOT] ❌ Комбинация {combination} не является выигрышной")
    return None

async def animate_slot_machine(message, callback) -> Tuple[str, str, str]:
    """Анимирует вращение слот-машины"""
    animation_steps = 12
    
    for i in range(animation_steps):
        try:
            # Генерируем случайные символы для анимации
            slot1 = random.choice(SLOT_EMOJIS)
            slot2 = random.choice(SLOT_EMOJIS) 
            slot3 = random.choice(SLOT_EMOJIS)
            
            # Обновляем сообщение с красивой анимацией
            anim = (
                f"🎰 <b>СЛОТ-МАШИНА КРУТИТСЯ...</b> 🎰\n\n"
                + CENTERED_FRAME.format(s1=slot1, s2=slot2, s3=slot3)
                + f"\n\n🎯 Ожидайте результат... <b>({i+1}/12)</b>"
            )
            
            await message.edit_text(anim, parse_mode="HTML")
            await asyncio.sleep(0.18 + 0.04 * (i / animation_steps))
        except Exception as e:
            logger.error(f"Error in animation step {i+1}: {e}")
            await asyncio.sleep(0.2)
    
    # Финальный результат
    try:
        final_slot1, final_slot2, final_slot3 = await generate_slot_result()
        return final_slot1, final_slot2, final_slot3
    except Exception as e:
        logger.error(f"Error generating final result: {e}")
        return random.choice(SLOT_EMOJIS), random.choice(SLOT_EMOJIS), random.choice(SLOT_EMOJIS)

async def process_slot_win(user_id: int, config: Tuple) -> Tuple[str, Optional[int]]:
    """
    УЛУЧШЕННАЯ ОБРАБОТКА ВЫИГРЫШЕЙ В СЛОТ-МАШИНЕ

    Обрабатывает выигрыш согласно новой системе:
    - Деньги начисляются автоматически
    - Звезды и TON требуют подтверждения админа
    - Создаются соответствующие записи в БД
    """
    config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = config

    # Получаем профиль пользователя
    user_profile = get_user_profile(user_id)
    if user_profile:
        db_user_id = user_profile['id']
        tg_id = user_profile['tg_id']
    else:
        logger.error(f"[SLOT] Не найден профиль пользователя с tg_id={user_id}")
        db_user_id = user_id
        tg_id = user_id

    # Создаем запись о выигрыше
    win_id = create_slot_win(user_id, combination, reward_type, reward_amount, True)
    logger.info(f"[SLOT] 🎰 Создана запись о выигрыше: win_id={win_id}, user_tg_id={tg_id}")

    # Обрабатываем приз в зависимости от типа
    if reward_type == "stars":
        # Для звезд создаем заказ, требующий подтверждения админа
        create_order(db_user_id, "slot_win", reward_amount, "pending",
                    extra_data=f"Звезды за слот: {combination} ({name})")
        reward_text = f"{int(reward_amount)}⭐ звезд"
        logger.info(f"[SLOT] ⭐ Создан заказ на звезды: {reward_amount} звезд для tg_id={tg_id}")

    elif reward_type == "money":
        # Для денег начисляем автоматически
        update_balance(user_id, reward_amount)
        reward_text = f"{int(reward_amount)}₽"
        logger.info(f"[SLOT] 💰 Автоматически начислено: {reward_amount}₽ для tg_id={tg_id}")

    elif reward_type == "ton":
        # Для TON создаем заказ, требующий подтверждения админа
        create_order(db_user_id, "slot_ton", reward_amount, "pending",
                    extra_data=f"TON за слот: {combination} ({name})")
        reward_text = f"{reward_amount} TON"
        logger.info(f"[SLOT] 💎 Создан заказ на TON: {reward_amount} TON для tg_id={tg_id}")

    else:
        reward_text = "Специальный приз"
        logger.warning(f"[SLOT] ⚠️ Неизвестный тип награды: {reward_type}")

    logger.info(f"[SLOT] ✅ Выигрыш '{name}' обработан для tg_id={tg_id}, win_id={win_id}, приз: {reward_text}")
    return reward_text, win_id

def try_use_slot_spin(tg_id: int) -> bool:
    """
    УЛУЧШЕННАЯ ФУНКЦИЯ ИСПОЛЬЗОВАНИЯ ПОПЫТОК СЛОТ-МАШИНЫ

    Проверяет доступность попыток и списывает одну при наличии.
    Поддерживает как обычные, так и бонусные попытки.
    """
    user_profile = get_user_profile(tg_id)
    if not user_profile:
        get_or_create_user(tg_id, "Unknown", None, datetime.datetime.now().strftime("%Y-%m-%d"))
        user_profile = get_user_profile(tg_id)

    user_id = user_profile['id']
    spins_used, last_reset = get_user_slot_spins(tg_id)
    daily_attempts = int(get_admin_setting('slot_daily_attempts', '5'))

    # Проверяем доступность попыток (включая бонусные)
    available_spins = get_spins_available(spins_used, daily_attempts)

    if available_spins <= 0:
        logger.info(f"[SLOT] ❌ Нет доступных попыток для tg_id={tg_id} (использовано: {spins_used}, лимит: {daily_attempts})")
        return False

    # Списываем попытку
    use_slot_spin(tg_id)
    logger.info(f"[SLOT] ✅ Попытка списана для tg_id={tg_id} (осталось: {available_spins - 1})")
    return True

async def use_slot_spin_and_check_win(tg_id: int, bot=None) -> Tuple[bool, str, str, str, Optional[Tuple]]:
    """Проверяет выигрыш в слот-машине (попытка уже должна быть списана)"""
    slot1, slot2, slot3 = await generate_slot_result()
    win_config = await check_win_combination(slot1, slot2, slot3)
    if win_config:
        config_id, combination, reward_type, reward_amount, chance_percent, emoji, name = win_config
        try:
            reward_text, win_id = await process_slot_win(tg_id, win_config)
        except Exception as e:
            logger.error(f"[SLOT] Ошибка process_slot_win: {e}")
            reward_text = ""
        # Отправляем уведомление админам только для stars и ton (деньги начисляются автоматически)
        if reward_type in ["stars", "ton"] and bot:
            try:
                await notify_admins_slot_win(tg_id, slot1+slot2+slot3, reward_type, reward_amount, bot=bot)
            except Exception as e:
                logger.error(f"[SLOT] Ошибка notify_admins_slot_win: {e}")
        return True, slot1, slot2, slot3, (name, reward_text, reward_type, reward_amount)
    else:
        create_slot_win(tg_id, slot1 + slot2 + slot3, "none", 0, False)
        return False, slot1, slot2, slot3, None

async def check_slot_availability(tg_id: int) -> Tuple[bool, str, int]:
    """Проверяет доступность слот-машины для пользователя"""
    # Проверяем, нужно ли сбросить попытки
    if should_reset_daily_attempts(tg_id):
        reset_slot_spins(tg_id)
    
    spins_used, last_reset = get_user_slot_spins(tg_id)
    daily_attempts = int(get_admin_setting('slot_daily_attempts', '5'))
    remaining = daily_attempts - spins_used
    
    if remaining <= 0:
        return False, f"Вы использовали все {daily_attempts} попыток на сегодня. Попробуйте завтра!", 0
    
    return True, f"У вас осталось {remaining} попыток", remaining

def format_slot_result(slot1: str, slot2: str, slot3: str, is_win: bool,
                      reward_text: str = "", prize_name: str = "", reward_type: str = "") -> str:
    """Форматирует результат слот-машины"""

    result_text = (
        f"🎰 <b>РЕЗУЛЬТАТ СЛОТ-МАШИНЫ</b> 🎰\n\n"
        + CENTERED_FRAME.format(s1=slot1, s2=slot2, s3=slot3)
        + "\n\n"
    )

    if is_win:
        # Определяем статус и финальное сообщение в зависимости от типа награды
        if reward_type == "money":
            status = "✅ Зачислено"
            final_message = "💰 Награда зачислена на ваш профиль"
        else:
            status = "⏳ Не зачислено"
            final_message = "🕒 Награда будет начислена в ближайшее время"

        # Получаем текущее время
        import datetime
        current_time = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')

        result_text += (
            f"🏆 <b>Приз:</b> {prize_name}\n"
            f"🎯 <b>Комбинация:</b> {slot1}{slot2}{slot3}\n"
            f"💎 <b>Награда:</b> {reward_text}\n"
            f"📊 <b>Статус:</b> {status}\n"
            f"🕒 <b>Время:</b> {current_time}\n\n"
            f"{final_message}"
        )
    else:
        result_text += (
            f"😔 На этот раз не повезло...\n\n"
            f"🍀 Не расстраивайтесь! Попробуйте еще раз!\n"
            f"🎯 Удача обязательно улыбнется вам!"
        )

    return result_text

def get_spins_available(attempts_used: int, daily_attempts: int) -> int:
    """
    Возвращает количество доступных попыток (с учётом бонусных)
    """
    if attempts_used < 0:
        bonus = abs(attempts_used)
        return daily_attempts + bonus
    else:
        return max(0, daily_attempts - attempts_used)

def format_attempts_text(attempts_used: int, daily_attempts: int) -> str:
    """
    Форматирует строку с количеством попыток для отображения в меню слот-машины.
    Если attempts_used < 0, значит есть бонусные попытки (например, за рефералов).
    """
    if attempts_used < 0:
        total = daily_attempts - attempts_used  # например, 5 - (-2) = 7
        return f"{total}/{daily_attempts}"
    else:
        left = max(0, daily_attempts - attempts_used)
        return f"{left}/{daily_attempts}"

def get_user_slot_stats(tg_id: int):
    """Возвращает статистику пользователя по слот-машине с учётом бонусных попыток"""
    spins_used, last_reset = get_user_slot_spins(tg_id)
    daily_attempts = int(get_admin_setting('slot_daily_attempts', '5'))
    # Используем синхронную версию для совместимости
    wins = get_slot_wins("completed")
    user_wins = [w for w in wins if w[2] == tg_id]
    # Корректно считаем оставшиеся попытки
    if spins_used < 0:
        bonus = abs(spins_used)
        remaining = daily_attempts + bonus
    else:
        remaining = max(0, daily_attempts - spins_used)
    return {
        'spins_used': spins_used,
        'daily_attempts': daily_attempts,
        'remaining': remaining,
        'total_wins': len(user_wins),
        'last_reset': last_reset,
        'attempts_text': format_attempts_text(spins_used, daily_attempts)
    }

def get_last_slot_results(tg_id: int, limit: int = 10):
    """Возвращает последние результаты слот-машины пользователя"""
    # Используем синхронную версию для совместимости
    wins = get_slot_wins("completed")
    user_wins = [w for w in wins if w[2] == tg_id]
    return user_wins[-limit:] if user_wins else []

async def notify_admins_slot_win(user_id: int, combination: str, reward_type: str, reward_amount: float, bot=None):
    """Уведомляет админов о выигрыше в слот-машине"""
    user = get_user_profile(user_id)
    if user:
        tg_id = user['tg_id']  # Используем ключи словаря
        full_name = user['full_name']
        username = user['username']
        reg_date = user['reg_date']
        user_info = f"@{username}" if username else f"ID {tg_id}"

        # Определяем эмодзи и текст для разных типов наград
        if reward_type == "stars":
            type_emoji = "⭐"
            type_text = "ЗВЁЗДЫ"
            reward_text = f"{reward_amount}⭐"
            hashtag = "#звёзды"
        elif reward_type == "ton":
            type_emoji = "💎"
            type_text = "TON"
            reward_text = f"{reward_amount} TON"
            hashtag = "#ton"
        elif reward_type == "money":
            type_emoji = "💰"
            type_text = "ДЕНЬГИ"
            reward_text = f"{reward_amount}₽"
            hashtag = "#деньги"
        else:
            type_emoji = "🎁"
            type_text = reward_type.upper()
            reward_text = f"{reward_amount}"
            hashtag = f"#{reward_type}"

        # Формируем текст в том же стиле, что и заказы
        text = (
            f"{type_emoji} <b>ВЫИГРЫШ В СЛОТ-МАШИНЕ - {type_text}</b> {type_emoji}\n\n"
            f"👤 <b>Клиент:</b> {user_info}\n"
            f"🆔 <b>ID:</b> <code>{tg_id}</code>\n"
            f"📝 <b>Имя:</b> {full_name}\n"
            f"🎯 <b>Комбинация:</b> {combination}\n"
            f"🏆 <b>Награда:</b> <b>{reward_text}</b>\n"
            f"🕒 <b>Дата/время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"📅 <b>Дата регистрации:</b> {reg_date}\n\n"
            f"#слот {hashtag}"
        )

        # Получаем win_id для создания клавиатуры для всех типов наград
        wins = get_slot_wins("pending")
        win_id = None
        for w in wins:
            # w[2] = tg_id, w[5] = reward_type, w[6] = reward_amount
            if w[2] == user_id and w[5] == reward_type and float(w[6]) == float(reward_amount):
                win_id = w[0]
                break

        # Создаем клавиатуру для всех типов наград
        if win_id:
            admin_kb = slot_win_admin_kb(win_id, user_id, reward_type, reward_amount)
        else:
            admin_kb = None

        try:
            if bot:
                await notify_admins(bot, text, admin_kb, parse_mode="HTML")
            else:
                logger.error("[SLOT] Не передан bot для notify_admins_slot_win")
        except Exception as e:
            logger.error(f"[SLOT] Ошибка отправки уведомления админам: {e}")