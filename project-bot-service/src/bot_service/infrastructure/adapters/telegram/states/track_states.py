from aiogram.fsm.state import StatesGroup, State


class TrackStates(StatesGroup):
    waiting_for_link = State()
    waiting_for_tags = State()
    waiting_for_filters = State()
    waiting_for_untrack_link = State()
