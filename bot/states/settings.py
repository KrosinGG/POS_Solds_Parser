from aiogram.fsm.state import State, StatesGroup


class FilterStates(StatesGroup):
    waiting_for_from_date = State()
    waiting_for_to_date = State()
    waiting_for_min_solds = State()


class AccessStates(StatesGroup):
    waiting_for_add_user_id = State()
    waiting_for_remove_user_id = State()
