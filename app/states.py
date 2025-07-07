"""
Состояния FSM
"""
from aiogram.fsm.state import StatesGroup, State

class SupportStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_admin_reply = State()

class WithdrawStates(StatesGroup):
    waiting_amount = State()
    confirm = State()
    waiting_requisites = State()

class EngagementStates(StatesGroup):
    """Состояния для системы вовлечённости"""
    waiting_for_achievement_name = State()
    waiting_for_achievement_description = State()
    waiting_for_achievement_type = State()
    waiting_for_achievement_requirement = State()
    waiting_for_achievement_reward_type = State()
    waiting_for_achievement_reward_amount = State()
    waiting_for_user_id = State()
    waiting_for_achievement_id = State()
