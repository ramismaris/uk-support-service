from maxapi.context import State, StatesGroup


class RequestForm(StatesGroup):
    phone = State()
    category = State()
    address = State()
    building = State()
    apartment = State()
    description = State()
    photos = State()
    preferred_time = State()
    confirm = State()
