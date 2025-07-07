"""
Модуль календаря активности
"""
import calendar
import datetime
from typing import List, Tuple, Dict
from app.database.models import (
    get_user_activity, mark_activity, get_user_activity_streak, 
    get_activity_rewards, claim_activity_reward
)

def get_current_date() -> str:
    """Получить текущую дату в формате YYYY-MM-DD"""
    return datetime.datetime.now().strftime("%Y-%m-%d")

def generate_calendar_grid(year: int, month: int, user_activities: List[Tuple], style: str = "plain") -> str:
    """Генерирует календарную сетку для месяца в разных стилях: plain, unicode, markdown, emoji"""
    first_day = datetime.date(year, month, 1)
    if month == 12:
        last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    days_in_month = last_day.day
    start_weekday = (first_day.weekday() + 1) % 7
    active_days = set()
    for activity in user_activities:
        if len(activity) > 2 and activity[2]:
            active_days.add(activity[2])
    # Убираем строку с днями недели
    calendar = ""
    week = ['   '] * 7
    day_ptr = start_weekday
    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        if date_str in active_days:
            if style == "emoji":
                cell = f"✅"
            elif style == "unicode":
                cell = f"{day:2d}✔"
            elif style == "markdown":
                cell = f"*{day:2d}*"
            else:
                cell = f"[{day:2d}]"
        else:
            cell = f"{day:2d} "
        week[day_ptr] = cell
        day_ptr += 1
        if day_ptr == 7:
            if style == "unicode":
                calendar += '┃' + '┃'.join(week) + '┃\n'
            else:
                calendar += ' '.join(week) + '\n'
            week = ['   '] * 7
            day_ptr = 0
    if any(cell.strip() for cell in week):
        if style == "unicode":
            calendar += '┃' + '┃'.join(week) + '┃\n'
        else:
            calendar += ' '.join(week) + '\n'
    if style == "unicode":
        calendar += '┗' + '┻'.join(['━━━']*7) + '┛'
    return calendar.strip()

def get_current_month_activities(tg_id: int) -> List[Tuple]:
    """Получает активность пользователя за текущий месяц"""
    current_date = datetime.datetime.now()
    activities = get_user_activity(tg_id)
    
    # Фильтруем только текущий месяц
    current_month_activities = []
    for activity in activities:
        try:
            if len(activity) > 2 and activity[2]:  # activity[2] = date
                activity_date = datetime.datetime.strptime(activity[2], "%Y-%m-%d")
                if activity_date.year == current_date.year and activity_date.month == current_date.month:
                    current_month_activities.append(activity)
        except:
            continue
    
    return current_month_activities

def format_activity_calendar(tg_id: int, year: int, month: int) -> str:
    """Форматирует календарь активности для пользователя"""
    activities = get_user_activity(tg_id)
    
    # Фильтруем активности за указанный месяц
    month_activities = []
    for activity in activities:
        try:
            if len(activity) > 2 and activity[2]:  # activity[2] = date
                activity_date = datetime.datetime.strptime(activity[2], "%Y-%m-%d")
                if activity_date.year == year and activity_date.month == month:
                    month_activities.append(activity)
        except:
            continue
    
    calendar_text = generate_calendar_grid(year, month, month_activities)
    
    # Добавляем статистику
    streak = get_user_activity_streak(tg_id)
    calendar_text += f"\n\n📊 **Статистика:**\n"
    calendar_text += f"🔥 Текущая серия: {streak} дней\n"
    calendar_text += f"✅ Активных дней в этом месяце: {len(month_activities)}\n"
    
    return calendar_text

def format_rewards_list(tg_id: int) -> str:
    """Форматирует список наград активности"""
    rewards = get_activity_rewards()
    streak = get_user_activity_streak(tg_id)
    
    rewards_text = "🏆 **Награды за активность** 🏆\n\n"
    
    for reward in rewards:
        reward_id, days_required, reward_type, reward_amount, description = reward
        reward_icon = "⭐" if reward_type == "stars" else "💰"
        
        if streak >= days_required:
            status = "✅ Доступно"
            action = f"[Получить](claim_reward_{reward_id})"
        else:
            days_left = days_required - streak
            status = f"⏳ Осталось {days_left} дней"
            action = ""
        
        rewards_text += f"{reward_icon} **{description}**\n"
        rewards_text += f"📅 Требуется дней: {days_required}\n"
        rewards_text += f"🎁 Награда: {reward_amount}{'⭐' if reward_type == 'stars' else '₽'}\n"
        rewards_text += f"📊 Статус: {status}\n"
        if action:
            rewards_text += f"🎯 {action}\n"
        rewards_text += "\n"
    
    return rewards_text

def format_activity_stats(stats: Dict) -> str:
    """Форматирует статистику активности для отображения"""
    text = "📊 <b>Статистика активности</b>\n\n"
    text += f"🔥 Текущая серия: {stats['current_streak']} дней\n"
    text += f"🏆 Максимальная серия: {stats['max_streak']} дней\n"
    text += f"📅 Активность за 7 дней: {stats['activities_7_days']}/7 дней\n"
    text += f"📅 Активность за 30 дней: {stats['activities_30_days']}/30 дней\n"
    text += f"📈 Процент активности (30 дней): {stats['percentage_30_days']:.1f}%\n\n"
    
    # Оценка активности
    if stats['percentage_30_days'] >= 80:
        text += "🏆 Отличная активность! Продолжайте в том же духе!\n"
    elif stats['percentage_30_days'] >= 60:
        text += "👍 Хорошая активность! Старайтесь быть активнее!\n"
    elif stats['percentage_30_days'] >= 40:
        text += "💪 Средняя активность. Есть куда расти!\n"
    else:
        text += "💪 Постарайтесь быть более активными!\n"
    
    return text

def mark_today_activity(tg_id: int) -> bool:
    """Отмечает активность пользователя на сегодня"""
    today = get_current_date()
    
    # Проверяем, не отмечена ли уже активность сегодня
    activities = get_user_activity(tg_id, today)
    if activities:
        return False  # Уже отмечена
    
    # Отмечаем активность
    mark_activity(tg_id, today, "daily")
    return True

def get_available_rewards(user_id: int) -> List[Dict]:
    """Получает доступные награды для пользователя"""
    streak = get_user_activity_streak(user_id)  # Используем исправленную функцию
    rewards = get_activity_rewards()

    available = []
    for reward in rewards:
        reward_id = reward[0]
        days_required = reward[1]
        reward_type = reward[2]
        reward_amount = reward[3]
        description = reward[4]

        if streak >= days_required:
            available.append({
                'id': reward_id,
                'days_required': days_required,
                'reward_type': reward_type,
                'reward_amount': reward_amount,
                'description': description
            })

    return available

def can_claim_reward(tg_id: int, reward_id: int) -> Tuple[bool, str]:
    """Проверяет, может ли пользователь получить награду"""
    streak = get_user_activity_streak(tg_id)
    rewards = get_activity_rewards()
    
    # Находим нужную награду
    target_reward = None
    for reward in rewards:
        if reward[0] == reward_id:
            target_reward = reward
            break
    
    if not target_reward:
        return False, "Награда не найдена"
    
    reward_id, days_required, reward_type, reward_amount, description = target_reward
    
    if streak < days_required:
        days_left = days_required - streak
        return False, f"Для получения награды нужно еще {days_left} дней активности"
    
    # Проверяем, не получал ли уже пользователь эту награду
    activities = get_user_activity(tg_id)
    for activity in activities:
        if len(activity) > 4 and activity[3] == 'reward' and activity[4] == reward_type and activity[5] == reward_amount:
            return False, "Вы уже получали эту награду"
    
    return True, "Награда доступна"

async def process_reward_claim(tg_id: int, reward_id: int) -> Tuple[bool, str]:
    """Обрабатывает получение награды"""
    can_claim, message = can_claim_reward(tg_id, reward_id)
    
    if not can_claim:
        return False, message
    
    # Получаем награду
    success = claim_activity_reward(tg_id, reward_id)
    
    if success:
        rewards = get_activity_rewards()
        for reward in rewards:
            if reward[0] == reward_id:
                reward_type, reward_amount, description = reward[2], reward[3], reward[4]
                reward_text = f"{reward_amount}{'⭐' if reward_type == 'stars' else '₽'}"
                return True, f"🎉 Поздравляем! Вы получили награду: {description} - {reward_text}"
    
    return False, "Ошибка при получении награды"

def get_activity_rewards_list() -> str:
    """Получает список всех наград активности"""
    rewards = get_activity_rewards()
    
    rewards_text = "🏆 **Награды за активность** 🏆\n\n"
    
    for reward in rewards:
        reward_id, days_required, reward_type, reward_amount, description = reward
        reward_icon = "⭐" if reward_type == "stars" else "💰"
        rewards_text += f"{reward_icon} **{description}**\n"
        rewards_text += f"📅 Требуется дней: {days_required}\n"
        rewards_text += f"🎁 Награда: {reward_amount}{'⭐' if reward_type == 'stars' else '₽'}\n\n"
    
    return rewards_text

def render_best_calendar_format(tg_id: int, year: int, month: int) -> str:
    """Красивый календарь активности с эмодзи, рамкой и выделением сегодняшнего дня"""
    import calendar
    now = datetime.datetime.now()
    cal = calendar.monthcalendar(year, month)
    activities = get_user_activity_for_month(tg_id, year, month)  # day:int -> bool
    text = f"📅 <b>Календарь активности — {calendar.month_name[month]} {year}</b>\n\n"
    text += "Пн  Вт  Ср  Чт  Пт  Сб  Вс\n"
    for week in cal:
        week_text = ""
        for day in week:
            if day == 0:
                week_text += "▫️ "  # пустая ячейка
            else:
                is_active = activities.get(day, False)
                is_today = (day == now.day and month == now.month and year == now.year)
                if is_active:
                    week_text += "✅ "
                elif is_today:
                    week_text += "🔵 "
                else:
                    week_text += "◻️ "
        text += week_text.rstrip() + "\n"
    return text.strip()

def get_current_month_calendar(year: int, month: int) -> List[List[int]]:
    """Возвращает календарь текущего месяца"""
    return calendar.monthcalendar(year, month)

def get_user_activity_for_month(tg_id: int, year: int, month: int) -> Dict[int, bool]:
    """Получает активность пользователя за месяц по tg_id"""
    month_start = datetime.datetime(year, month, 1)
    if month == 12:
        month_end = datetime.datetime(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        month_end = datetime.datetime(year, month + 1, 1) - datetime.timedelta(days=1)
    activities = {}
    current_date = month_start
    while current_date <= month_end:
        date_str = current_date.strftime("%Y-%m-%d")
        activity = get_user_activity(tg_id, date_str)
        activities[current_date.day] = bool(activity)
        current_date += datetime.timedelta(days=1)
    return activities

def format_calendar_display(year: int, month: int, user_activities: Dict[int, bool]) -> str:
    """Форматирует календарь для отображения"""
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    text = f"📅 <b>Календарь активности - {month_name} {year}</b>\n\n"
    
    # Заголовки дней недели
    text += "Пн  Вт  Ср  Чт  Пт  Сб  Вс\n"
    
    for week in cal:
        week_text = ""
        for day in week:
            if day == 0:
                week_text += "    "
            else:
                # Проверяем активность для этого дня
                is_active = user_activities.get(day, False)
                if is_active:
                    week_text += "✅ "
                else:
                    week_text += f"{day:2d} "
        text += week_text + "\n"
    
    text += "\n✅ - день активности отмечен"
    return text

def calculate_activity_streak(user_id: int) -> int:
    """Рассчитывает текущую серию активности пользователя (использует исправленную функцию БД)"""
    # Используем исправленную функцию из базы данных
    return get_user_activity_streak(user_id)

def get_next_reward_info(user_id: int) -> Dict:
    """Получает информацию о следующей доступной награде"""
    streak = get_user_activity_streak(user_id)  # Используем исправленную функцию
    rewards = get_activity_rewards()

    # Сортируем награды по количеству дней
    sorted_rewards = sorted(rewards, key=lambda x: x[1])

    for reward in sorted_rewards:
        days_required = reward[1]
        if streak < days_required:
            return {
                'days_required': days_required,
                'days_left': days_required - streak,
                'reward_type': reward[2],
                'reward_amount': reward[3],
                'description': reward[4]
            }

    return {}

def check_daily_activity_reset(user_id: int) -> bool:
    """Проверяет, нужно ли сбросить ежедневную активность"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    activity = get_user_activity(user_id, today)
    return activity is None 