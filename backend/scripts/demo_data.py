"""Six months of realistic ticket history for the hackathon demo.

Run from backend/:

    uv run python scripts/demo_data.py            # create if missing
    uv run python scripts/demo_data.py --reset    # recreate relative to now
    uv run python scripts/demo_data.py --delete   # remove demo data only

In Docker: docker compose exec api python scripts/demo_data.py --reset

The script writes six months of realistic history for the dashboard and the
staff panel: residents and their addresses, tickets with status timelines and
chats. It never calls Max and never touches the services; it writes rows the
way the real services would have written them.

Marker: a demo user is a user whose `max_user_id` is in the reserved range
`DEMO_MAX_USER_ID_BASE = 9_000_000_000` and above. Real Max ids are around
1e8-1e9, and the base seed uses 1000001-1000003, so neither is treated as demo
data by this script. There is no «demo» flag: a demo ticket is simply a ticket
whose client is a demo user.

Determinism: a fixed `random.Random` seed and timestamps relative to
`datetime.now(UTC)` taken at the start of the run. Two runs a day apart give
the same history shifted by a day.
"""

import argparse
import asyncio
import random
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from scripts import demo_content as content
from scripts.seed import DEMO_MANAGER_MAX_USER_ID, seed
from src.core.config import settings
from src.core.constants import SenderType, TicketStatus, TicketType, UserRole
from src.core.texts import status_message_text
from src.db.session import AsyncSessionLocal
from src.models.auth_token import AuthToken
from src.models.building import Building
from src.models.category import Category
from src.models.content_block import ContentBlock
from src.models.file import File
from src.models.login_token import LoginToken
from src.models.message import Message
from src.models.residence import Residence
from src.models.status_change import StatusChange
from src.models.ticket import Ticket
from src.models.ticket_triage import TicketTriage
from src.models.user import User

DEMO_MAX_USER_ID_BASE = 9_000_000_000
DEMO_CLIENT_MAX_USER_ID_START = DEMO_MAX_USER_ID_BASE + 10_000
DEMO_CLIENT_COUNT = 60

DEMO_MANAGER_KEYS = ("olga", "dmitry", "petr")
SLOW_MANAGER_KEY = "petr"
SEED_MANAGER_KEY = "igor"

DEMO_RANDOM_SEED = 20260929

HISTORY_DAYS = 182
CLOSED_HISTORY_DAYS = 180

SEED_BUILDING_ADDRESSES = [
    "ул. Ленина, 12",
    "ул. Гагарина, 5",
    "пр-т Мира, 28",
    "ул. Садовая, 7",
]
# The building with the lift problem (pattern 2).
LIFT_PROBLEM_BUILDING = "ул. Садовая, 7"
LIFT_PROBLEM_MULTIPLIER = 3

# ~500 tickets for a full run: roughly 1.5/day six months ago growing to
# 4.5/day now, with fewer on weekends.
START_DAILY_RATE = 1.5
END_DAILY_RATE = 4.5
WEEKEND_RATE = 0.6

# The company connected the bot half a year ago and got faster over time.
# Reaction is exponential (hours): the last 30 days of the crew are about a
# quarter faster than the 30 days before. Пётр is the slow one (pattern 3).
REACTION_HOURS_RECENT = 0.45
REACTION_HOURS_PREVIOUS = 1.05
REACTION_HOURS_OLDER = 0.8
REACTION_HOURS_SLOW = 3.5
WORK_START_HOUR = 8
WORK_END_HOUR = 20

HEATING_CATEGORY = "🔥 Отопление"
LIFT_CATEGORY = "🛗 Лифт"
HEATING_SEASON_DAYS = 14
# Category mix of requests outside the heating season; in-season the heating
# weight is forced to ~30% and the other categories are rescaled (pattern 1).
BASE_CATEGORY_WEIGHTS = {
    "🚰 Сантехника": 30.0,
    "⚡️ Электрика": 15.0,
    "🛗 Лифт": 10.0,
    HEATING_CATEGORY: 2.0,
    "🧹 Уборка": 20.0,
    "🌳 Благоустройство": 12.0,
    "❓ Другое": 11.0,
}
HEATING_SEASON_WEIGHT = 38.0

# Creation hour weights (local time): mostly 7:00-23:00, rarely at night.
HOUR_WEIGHTS = [
    0.06,  # 00
    0.06,  # 01
    0.06,  # 02
    0.06,  # 03
    0.06,  # 04
    0.08,  # 05
    0.25,  # 06
    1.5,  # 07
    3.2,  # 08
    3.2,  # 09
    3.0,  # 10
    2.9,  # 11
    2.8,  # 12
    2.8,  # 13
    2.8,  # 14
    2.8,  # 15
    2.8,  # 16
    2.6,  # 17
    2.4,  # 18
    1.1,  # 19
    0.3,  # 20
    0.2,  # 21
    0.15,  # 22
    0.08,  # 23
]

# Mean hours from reaction to closing. Lift and landscaping take longer.
WORK_HOURS_MEAN = {
    "🛗 Лифт": 34.0,
    "🌳 Благоустройство": 28.0,
    HEATING_CATEGORY: 24.0,
}
DEFAULT_WORK_HOURS_MEAN = 20.0

REJECTED_SHARE = 0.05
REJECTED_AFTER_WORK_SHARE = 0.35
WAITING_CLIENT_SHARE = 0.20
REOPEN_SHARE = 0.03
RATING_SHARE = 0.70
QUESTION_SHARE = 0.10
PREFERRED_TIME_SHARE = 0.35
TAKE_INTO_WORK_SHARE = 0.45

RATING_WEIGHTS_SLOW = {5: 0.28, 4: 0.36, 3: 0.24, 2: 0.08, 1: 0.04}
RATING_WEIGHTS = {5: 0.82, 4: 0.12, 3: 0.04, 2: 0.015, 1: 0.005}

# Open tickets written by this script. The base seed adds two NEW, one
# IN_PROGRESS and one WAITING_CLIENT on top, so the dashboard shows about
# 5 NEW, 10 IN_PROGRESS and 5 WAITING_CLIENT with 2-4 overdue.
OPEN_TICKET_SPECS = [
    (TicketStatus.NEW, 8.0, True),
    (TicketStatus.NEW, 5.0, True),
    (TicketStatus.NEW, 1.5, False),
    (TicketStatus.IN_PROGRESS, 120.0, False),
    (TicketStatus.IN_PROGRESS, 96.0, False),
    (TicketStatus.IN_PROGRESS, 48.0, True),
    (TicketStatus.IN_PROGRESS, 42.0, False),
    (TicketStatus.IN_PROGRESS, 36.0, True),
    (TicketStatus.IN_PROGRESS, 30.0, False),
    (TicketStatus.IN_PROGRESS, 24.0, True),
    (TicketStatus.IN_PROGRESS, 18.0, False),
    (TicketStatus.IN_PROGRESS, 12.0, False),
    (TicketStatus.WAITING_CLIENT, 60.0, False),
    (TicketStatus.WAITING_CLIENT, 42.0, False),
    (TicketStatus.WAITING_CLIENT, 30.0, False),
    (TicketStatus.WAITING_CLIENT, 10.0, False),
]

PHONE_TEMPLATE = "+7 (900) 0{d1}{d2}-{d3}{d4}-{d5}{d6}"

OPEN_STATUSES = (
    TicketStatus.NEW,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_CLIENT,
)


@dataclass
class _Transition:
    from_status: TicketStatus | None
    to_status: TicketStatus
    changed_by_id: int | None
    at: datetime
    comment: str | None = None


@dataclass
class _Message:
    sender_type: SenderType
    author_id: int | None
    at: datetime
    text: str | None = None
    system_status: TicketStatus | None = None
    comment: str | None = None


@dataclass
class _Plan:
    ticket: Ticket
    transitions: list[_Transition] = field(default_factory=list)
    messages: list[_Message] = field(default_factory=list)


@dataclass
class _Resident:
    user: User
    building: Building
    apartment: str


@dataclass
class GenerateSummary:
    clients: int = 0
    managers: int = 0
    residences: int = 0
    tickets: int = 0
    open_tickets: int = 0
    messages: int = 0
    status_changes: int = 0


@dataclass
class DeleteSummary:
    tickets: int = 0
    messages: int = 0
    status_changes: int = 0
    users_deleted: int = 0
    users_kept: list[str] = field(default_factory=list)


class _Picker:
    """Picks from a pool without repeating the last few values."""

    def __init__(self, rng: random.Random, avoid: int = 8):
        self.rng = rng
        self.avoid = avoid
        self._recent: dict[tuple, list[str]] = {}

    def pick(self, key: tuple, pool: list[str]) -> str:
        recent = self._recent.setdefault(key, [])
        options = [value for value in pool if value not in recent] or list(pool)
        value = self.rng.choice(options)
        recent.append(value)
        if len(recent) > self.avoid:
            recent.pop(0)
        return value


def is_demo_user(max_user_id: int) -> bool:
    return max_user_id >= DEMO_MAX_USER_ID_BASE


async def has_demo_data(db: AsyncSession) -> bool:
    """Demo data exists if at least one demo client is left."""
    count = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.max_user_id >= DEMO_MAX_USER_ID_BASE, User.role == UserRole.CLIENT)
    )
    return bool(count)


def _phone(rng: random.Random) -> str:
    digits = [rng.randrange(10) for _ in range(6)]
    return PHONE_TEMPLATE.format(
        d1=digits[0], d2=digits[1], d3=digits[2], d4=digits[3], d5=digits[4], d6=digits[5]
    )


# Reference data and users


async def _get_or_create_buildings(db: AsyncSession) -> dict[str, Building]:
    existing = (await db.scalars(select(Building))).all()
    by_address = {building.address: building for building in existing}
    for address in content.NEW_BUILDINGS:
        if address not in by_address:
            building = Building(address=address)
            db.add(building)
            await db.flush()
            by_address[address] = building
    return by_address


async def _get_or_create_user(
    db: AsyncSession,
    *,
    max_user_id: int,
    first_name: str,
    last_name: str | None,
    role: UserRole,
    phone: str | None = None,
    created_at: datetime | None = None,
) -> User:
    existing = await db.scalar(select(User).where(User.max_user_id == max_user_id))
    if existing is not None:
        return existing
    user = User(
        max_user_id=max_user_id,
        first_name=first_name,
        last_name=last_name,
        role=role,
        phone=phone,
    )
    if created_at is not None:
        user.created_at = created_at
    db.add(user)
    await db.flush()
    return user


async def _create_managers(db: AsyncSession, *, now: datetime) -> list[dict]:
    seed_manager = await db.scalar(select(User).where(User.max_user_id == DEMO_MANAGER_MAX_USER_ID))
    if seed_manager is None:
        raise RuntimeError("base seed did not create the seed manager")
    managers: list[dict] = [
        {"key": SEED_MANAGER_KEY, "id": seed_manager.id, "is_slow": False, "is_demo": False}
    ]
    for key in DEMO_MANAGER_KEYS:
        user = await _get_or_create_user(
            db,
            max_user_id=DEMO_MAX_USER_ID_BASE + content.MANAGER_MAX_USER_ID_OFFSET[key],
            first_name=content.MANAGER_FIRST_NAME[key],
            last_name=content.MANAGER_LAST_NAME[key],
            role=UserRole.MANAGER,
            created_at=now - timedelta(days=HISTORY_DAYS),
        )
        managers.append(
            {"key": key, "id": user.id, "is_slow": key == SLOW_MANAGER_KEY, "is_demo": True}
        )
    return managers


async def _create_residents(
    db: AsyncSession,
    *,
    now: datetime,
    rng: random.Random,
    buildings: dict[str, Building],
) -> list[_Resident]:
    addresses = [address for address in content.APARTMENT_MAX if address in buildings]
    names = content.CLIENTS[:]
    rng.shuffle(names)
    used_apartments: dict[str, set[str]] = {address: set() for address in addresses}
    residents: list[_Resident] = []

    for index in range(DEMO_CLIENT_COUNT):
        first_name, last_name = names[index]
        created_at = now - timedelta(days=HISTORY_DAYS - index % 30, hours=index % 24)
        user = await _get_or_create_user(
            db,
            max_user_id=DEMO_CLIENT_MAX_USER_ID_START + index,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.CLIENT,
            phone=_phone(rng),
            created_at=created_at,
        )

        address = addresses[index % len(addresses)]
        building = buildings[address]

        existing = await db.scalar(
            select(Residence).where(Residence.user_id == user.id).order_by(Residence.id)
        )
        if existing is not None:
            building = next(item for item in buildings.values() if item.id == existing.building_id)
            residents.append(_Resident(user=user, building=building, apartment=existing.apartment))
            continue

        apartment_max = content.APARTMENT_MAX[address]
        apartment = str(rng.randint(1, apartment_max))
        while apartment in used_apartments[address]:
            apartment = str(rng.randint(1, apartment_max))
        used_apartments[address].add(apartment)
        db.add(
            Residence(
                user_id=user.id,
                building_id=building.id,
                apartment=apartment,
                is_primary=True,
                verified=True,
                created_at=created_at,
            )
        )
        residents.append(_Resident(user=user, building=building, apartment=apartment))
    await db.flush()
    return residents


# Planning


def _work_clamped(created_at: datetime, delay_hours: float, rng: random.Random) -> datetime:
    """Reaction leaves NEW in working hours (8:00-20:00 local), else next morning."""
    tz = ZoneInfo(settings.timezone)
    moment = created_at.astimezone(tz) + timedelta(hours=delay_hours)
    if moment.hour >= WORK_END_HOUR:
        moment = (moment + timedelta(days=1)).replace(
            hour=WORK_START_HOUR,
            minute=rng.randrange(0, 60),
            second=rng.randrange(0, 60),
            microsecond=0,
        )
    elif moment.hour < WORK_START_HOUR:
        moment = moment.replace(
            hour=WORK_START_HOUR,
            minute=rng.randrange(0, 60),
            second=rng.randrange(0, 60),
            microsecond=0,
        )
    return moment.astimezone(UTC)


def _reaction_hours(rng: random.Random, manager: dict, days_ago: int) -> float:
    if manager["is_slow"]:
        base = REACTION_HOURS_SLOW
    elif days_ago <= 30:
        base = REACTION_HOURS_RECENT
    elif days_ago <= 60:
        base = REACTION_HOURS_PREVIOUS
    else:
        base = REACTION_HOURS_OLDER
    return max(0.1, rng.expovariate(1 / base))


def _choose_category(rng: random.Random, *, building_address: str, days_ago: int) -> str:
    weights = dict(BASE_CATEGORY_WEIGHTS)
    if days_ago < HEATING_SEASON_DAYS:
        others = sum(weight for title, weight in weights.items() if title != HEATING_CATEGORY)
        scale = (100 - HEATING_SEASON_WEIGHT) / others
        weights = {
            title: (HEATING_SEASON_WEIGHT if title == HEATING_CATEGORY else weight * scale)
            for title, weight in weights.items()
        }
    if building_address == LIFT_PROBLEM_BUILDING:
        weights[LIFT_CATEGORY] *= LIFT_PROBLEM_MULTIPLIER
    titles = list(weights)
    return rng.choices(titles, weights=[weights[title] for title in titles])[0]


def _rating(rng: random.Random, manager: dict) -> int | None:
    if rng.random() >= RATING_SHARE:
        return None
    weights = RATING_WEIGHTS_SLOW if manager["is_slow"] else RATING_WEIGHTS
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _description(
    rng: random.Random,
    picker: _Picker,
    ticket_type: TicketType,
    category_title: str | None,
) -> str:
    if ticket_type == TicketType.QUESTION or category_title is None:
        return picker.pick(("questions",), content.QUESTIONS)
    return picker.pick(
        ("descriptions", category_title), content.REQUEST_DESCRIPTIONS[category_title]
    )


def _staff_reply(rng: random.Random, ticket_type: TicketType, category_title: str | None) -> str:
    if ticket_type == TicketType.QUESTION or category_title is None:
        return rng.choice(content.QUESTION_REPLIES)
    return rng.choice(content.STAFF_REPLIES[category_title])


def _new_ticket(
    *,
    ticket_type: TicketType,
    client: _Resident,
    category: Category | None,
    description: str,
    preferred_time: str | None,
    created_at: datetime,
) -> Ticket:
    has_address = category is not None
    ticket = Ticket(
        type=ticket_type,
        status=TicketStatus.NEW,
        client_id=client.user.id,
        category_id=category.id if category else None,
        building_id=client.building.id if has_address else None,
        apartment=client.apartment if has_address else None,
        description=description,
        contact_phone=client.user.phone,
        preferred_time=preferred_time,
    )
    ticket.created_at = created_at
    ticket.updated_at = created_at
    return ticket


def _plan_rejected(
    rng: random.Random,
    *,
    plan: _Plan,
    now: datetime,
    manager: dict,
    react_at: datetime,
) -> _Plan:
    """The manager rejects the ticket, straight from NEW or after taking it."""
    ticket = plan.ticket
    reason = rng.choice(content.REJECTION_REASONS)
    if rng.random() < REJECTED_AFTER_WORK_SHARE:
        plan.transitions.append(
            _Transition(TicketStatus.NEW, TicketStatus.IN_PROGRESS, manager["id"], react_at)
        )
        plan.messages.append(
            _Message(
                SenderType.SYSTEM,
                None,
                react_at + timedelta(seconds=1),
                system_status=TicketStatus.IN_PROGRESS,
            )
        )
        reject_at = react_at + timedelta(hours=rng.uniform(2, 30))
        reject_at = min(reject_at, now - timedelta(hours=1))
        if reject_at <= react_at:
            reject_at = react_at + timedelta(hours=1)
        plan.transitions.append(
            _Transition(
                TicketStatus.IN_PROGRESS, TicketStatus.REJECTED, manager["id"], reject_at, reason
            )
        )
        plan.messages.append(
            _Message(
                SenderType.SYSTEM,
                None,
                reject_at + timedelta(seconds=1),
                system_status=TicketStatus.REJECTED,
                comment=reason,
            )
        )
        ticket.assignee_id = manager["id"]
        ticket.closed_at = reject_at
    else:
        plan.transitions.append(
            _Transition(TicketStatus.NEW, TicketStatus.REJECTED, manager["id"], react_at, reason)
        )
        plan.messages.append(
            _Message(
                SenderType.SYSTEM,
                None,
                react_at + timedelta(seconds=1),
                system_status=TicketStatus.REJECTED,
                comment=reason,
            )
        )
        ticket.closed_at = react_at

    ticket.status = TicketStatus.REJECTED
    ticket.rating = None
    ticket.updated_at = max(
        [
            ticket.closed_at,
            *[message.at for message in plan.messages],
            *[t.at for t in plan.transitions],
        ]
    )
    return plan


def _plan_closed_ticket(
    rng: random.Random,
    *,
    now: datetime,
    client: _Resident,
    managers: list[dict],
    category: Category | None,
    category_title: str | None,
    ticket_type: TicketType,
    created_at: datetime,
    picker: _Picker,
) -> _Plan:
    manager = rng.choice(managers)
    ticket = _new_ticket(
        ticket_type=ticket_type,
        client=client,
        category=category,
        description=_description(rng, picker, ticket_type, category_title),
        preferred_time=rng.choice(content.PREFERRED_TIMES)
        if rng.random() < PREFERRED_TIME_SHARE
        else None,
        created_at=created_at,
    )
    plan = _Plan(ticket=ticket)
    plan.transitions.append(_Transition(None, TicketStatus.NEW, client.user.id, created_at))

    days_ago = (now - created_at).days
    react_at = _work_clamped(created_at, _reaction_hours(rng, manager, days_ago), rng)
    react_at = min(react_at, now - timedelta(hours=5))
    if react_at <= created_at:
        react_at = created_at + timedelta(minutes=15)

    if rng.random() < REJECTED_SHARE:
        return _plan_rejected(rng, plan=plan, now=now, manager=manager, react_at=react_at)

    will_reopen = rng.random() < REOPEN_SHARE
    ticket.assignee_id = manager["id"]

    if will_reopen or rng.random() >= TAKE_INTO_WORK_SHARE:
        # The manager's first reply takes the ticket into work: a system
        # transition with changed_by_id = None, like message_service does.
        plan.messages.append(
            _Message(
                SenderType.STAFF,
                manager["id"],
                react_at,
                _staff_reply(rng, ticket_type, category_title),
            )
        )
        plan.transitions.append(
            _Transition(
                TicketStatus.NEW, TicketStatus.IN_PROGRESS, None, react_at + timedelta(seconds=1)
            )
        )
    else:
        plan.transitions.append(
            _Transition(TicketStatus.NEW, TicketStatus.IN_PROGRESS, manager["id"], react_at)
        )
        plan.messages.append(
            _Message(
                SenderType.SYSTEM,
                None,
                react_at + timedelta(seconds=1),
                system_status=TicketStatus.IN_PROGRESS,
            )
        )
        if not will_reopen and rng.random() < 0.6:
            plan.messages.append(
                _Message(
                    SenderType.STAFF,
                    manager["id"],
                    react_at + timedelta(minutes=rng.randint(3, 90)),
                    rng.choice(content.STAFF_TAKE_MESSAGES),
                )
            )

    ts = max(transition.at for transition in plan.transitions)
    last_client_message_at: datetime | None = None

    if not will_reopen and len(plan.messages) <= 2 and rng.random() < WAITING_CLIENT_SHARE:
        question_at = ts + timedelta(hours=rng.uniform(1, 10))
        question_at = min(question_at, now - timedelta(hours=4))
        question_at = max(question_at, ts + timedelta(minutes=30))
        plan.messages.append(
            _Message(
                SenderType.STAFF, manager["id"], question_at, rng.choice(content.STAFF_QUESTIONS)
            )
        )
        plan.transitions.append(
            _Transition(
                TicketStatus.IN_PROGRESS,
                TicketStatus.WAITING_CLIENT,
                manager["id"],
                question_at + timedelta(seconds=1),
            )
        )
        plan.messages.append(
            _Message(
                SenderType.SYSTEM,
                None,
                question_at + timedelta(seconds=2),
                system_status=TicketStatus.WAITING_CLIENT,
            )
        )
        answer_at = question_at + timedelta(hours=rng.uniform(2, 40))
        answer_at = min(answer_at, now - timedelta(hours=3))
        answer_at = max(answer_at, question_at + timedelta(minutes=20))
        plan.messages.append(
            _Message(
                SenderType.CLIENT, client.user.id, answer_at, rng.choice(content.CLIENT_ANSWERS)
            )
        )
        plan.transitions.append(
            _Transition(
                TicketStatus.WAITING_CLIENT,
                TicketStatus.IN_PROGRESS,
                None,
                answer_at + timedelta(seconds=1),
            )
        )
        last_client_message_at = answer_at
        ts = answer_at + timedelta(seconds=1)

    work_mean = WORK_HOURS_MEAN.get(category_title or "", DEFAULT_WORK_HOURS_MEAN)
    resolution_at = react_at + timedelta(hours=max(0.5, rng.expovariate(1 / work_mean)))
    resolution_at = max(resolution_at, ts + timedelta(hours=rng.uniform(0.5, 5)))
    resolution_at = min(resolution_at, now - timedelta(hours=2))
    resolution_at = max(resolution_at, ts + timedelta(minutes=30))
    if len(plan.messages) < 5 and rng.random() < 0.35:
        closing_at = resolution_at - timedelta(minutes=rng.randint(5, 120))
        if closing_at > ts:
            plan.messages.append(
                _Message(
                    SenderType.STAFF,
                    manager["id"],
                    closing_at,
                    rng.choice(content.CLOSING_MESSAGES),
                )
            )
            ts = closing_at
    resolution_at = max(resolution_at, ts + timedelta(minutes=1))

    plan.transitions.append(
        _Transition(TicketStatus.IN_PROGRESS, TicketStatus.CLOSED, manager["id"], resolution_at)
    )
    plan.messages.append(
        _Message(
            SenderType.SYSTEM,
            None,
            resolution_at + timedelta(seconds=1),
            system_status=TicketStatus.CLOSED,
        )
    )
    closed_at = resolution_at

    if will_reopen:
        reopen_at = closed_at + timedelta(hours=rng.uniform(2, 100))
        second_close_at = reopen_at + timedelta(hours=rng.uniform(2, 48))
        if reopen_at < now - timedelta(hours=2) and second_close_at < now - timedelta(hours=1):
            plan.transitions.append(
                _Transition(
                    TicketStatus.CLOSED, TicketStatus.IN_PROGRESS, client.user.id, reopen_at
                )
            )
            plan.messages.append(
                _Message(
                    SenderType.CLIENT,
                    client.user.id,
                    reopen_at + timedelta(seconds=30),
                    rng.choice(content.REOPEN_CLIENT_MESSAGES),
                )
            )
            last_client_message_at = reopen_at + timedelta(seconds=30)
            plan.transitions.append(
                _Transition(
                    TicketStatus.IN_PROGRESS,
                    TicketStatus.CLOSED,
                    manager["id"],
                    second_close_at,
                )
            )
            plan.messages.append(
                _Message(
                    SenderType.SYSTEM,
                    None,
                    second_close_at + timedelta(seconds=1),
                    system_status=TicketStatus.CLOSED,
                )
            )
            closed_at = second_close_at

    ticket.status = TicketStatus.CLOSED
    ticket.assignee_id = manager["id"]
    ticket.closed_at = closed_at
    ticket.rating = _rating(rng, manager)
    ticket.last_client_message_at = last_client_message_at
    ticket.staff_seen_at = (
        min(last_client_message_at + timedelta(minutes=5), now) if last_client_message_at else None
    )
    ticket.updated_at = max(
        [closed_at, *[message.at for message in plan.messages], *[t.at for t in plan.transitions]]
    )
    return plan


def _plan_open_ticket(
    rng: random.Random,
    *,
    now: datetime,
    client: _Resident,
    category: Category | None,
    category_title: str | None,
    ticket_type: TicketType,
    created_at: datetime,
    status: TicketStatus,
    manager: dict | None,
    unread: bool,
    picker: _Picker,
) -> _Plan:
    ticket = _new_ticket(
        ticket_type=ticket_type,
        client=client,
        category=category,
        description=_description(rng, picker, ticket_type, category_title),
        preferred_time=rng.choice(content.PREFERRED_TIMES)
        if rng.random() < PREFERRED_TIME_SHARE
        else None,
        created_at=created_at,
    )
    plan = _Plan(ticket=ticket)
    plan.transitions.append(_Transition(None, TicketStatus.NEW, client.user.id, created_at))

    last_client_message_at: datetime | None = None
    last_activity = created_at

    if status == TicketStatus.NEW:
        client_at = min(
            created_at + timedelta(minutes=rng.randint(10, 120)),
            now - timedelta(minutes=2),
        )
        plan.messages.append(
            _Message(
                SenderType.CLIENT, client.user.id, client_at, rng.choice(content.CLIENT_UPDATES)
            )
        )
        last_client_message_at = client_at
        last_activity = client_at
    elif manager is not None:
        ticket.assignee_id = manager["id"]
        react_at = created_at + timedelta(hours=rng.uniform(0.5, 2.5))
        react_at = min(react_at, now - timedelta(minutes=rng.randint(10, 45)))
        react_at = max(react_at, created_at + timedelta(minutes=10))
        plan.messages.append(
            _Message(
                SenderType.STAFF,
                manager["id"],
                react_at,
                _staff_reply(rng, ticket_type, category_title),
            )
        )
        # The first reply takes the ticket into work: a system transition
        # with changed_by_id = None, like message_service does.
        plan.transitions.append(
            _Transition(TicketStatus.NEW, TicketStatus.IN_PROGRESS, None, react_at)
        )
        last_activity = react_at

        if status == TicketStatus.WAITING_CLIENT:
            question_at = react_at + timedelta(hours=rng.uniform(1, 8))
            question_at = min(question_at, now - timedelta(minutes=30))
            question_at = max(question_at, react_at + timedelta(minutes=10))
            plan.messages.append(
                _Message(
                    SenderType.STAFF,
                    manager["id"],
                    question_at,
                    rng.choice(content.STAFF_QUESTIONS),
                )
            )
            plan.transitions.append(
                _Transition(
                    TicketStatus.IN_PROGRESS,
                    TicketStatus.WAITING_CLIENT,
                    manager["id"],
                    question_at + timedelta(seconds=1),
                )
            )
            plan.messages.append(
                _Message(
                    SenderType.SYSTEM,
                    None,
                    question_at + timedelta(seconds=2),
                    system_status=TicketStatus.WAITING_CLIENT,
                )
            )
            last_activity = question_at + timedelta(seconds=2)
        elif rng.random() < 0.4:
            reply_at = react_at + timedelta(hours=rng.uniform(0.5, 6))
            reply_at = min(reply_at, now - timedelta(minutes=15))
            reply_at = max(reply_at, react_at + timedelta(minutes=5))
            plan.messages.append(
                _Message(
                    SenderType.CLIENT, client.user.id, reply_at, rng.choice(content.CLIENT_REPLIES)
                )
            )
            last_client_message_at = reply_at
            last_activity = reply_at

    if unread and status in (TicketStatus.NEW, TicketStatus.IN_PROGRESS):
        client_at = now - timedelta(minutes=rng.randint(5, 180))
        client_at = max(
            client_at, last_activity + timedelta(minutes=5), created_at + timedelta(minutes=5)
        )
        if client_at >= now:
            client_at = now - timedelta(minutes=1)
        plan.messages.append(
            _Message(
                SenderType.CLIENT, client.user.id, client_at, rng.choice(content.CLIENT_UPDATES)
            )
        )
        last_client_message_at = client_at
        last_activity = client_at
        ticket.staff_seen_at = None
    elif last_client_message_at is not None:
        ticket.staff_seen_at = min(last_client_message_at + timedelta(minutes=5), now)
    else:
        ticket.staff_seen_at = last_activity + timedelta(minutes=5)

    ticket.status = status
    ticket.last_client_message_at = last_client_message_at
    ticket.updated_at = max(
        [
            last_activity,
            *[message.at for message in plan.messages],
            *[t.at for t in plan.transitions],
        ]
    )
    return plan


def _build_plans(
    rng: random.Random,
    *,
    now: datetime,
    residents: list[_Resident],
    managers: list[dict],
    categories: dict[str, Category],
    volume: float = 1.0,
) -> list[_Plan]:
    plans: list[_Plan] = []
    picker = _Picker(rng)
    tz = ZoneInfo(settings.timezone)
    today_local = now.astimezone(tz).date()
    start_date = today_local - timedelta(days=HISTORY_DAYS - 1)

    for index in range(CLOSED_HISTORY_DAYS):
        day = start_date + timedelta(days=index)
        progress = index / max(1, CLOSED_HISTORY_DAYS - 1)
        rate = START_DAILY_RATE + (END_DAILY_RATE - START_DAILY_RATE) * progress
        if day.weekday() >= 5:
            rate *= WEEKEND_RATE
        expected = rate * volume
        count = int(expected)
        if rng.random() < expected - count:
            count += 1

        for _ in range(count):
            hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
            local_dt = datetime.combine(
                day, time(hour, rng.randrange(60), rng.randrange(60)), tzinfo=tz
            )
            created_at = local_dt.astimezone(UTC)
            if created_at >= now:
                continue
            resident = rng.choice(residents)
            ticket_type = (
                TicketType.QUESTION if rng.random() < QUESTION_SHARE else TicketType.REQUEST
            )
            category = None
            category_title = None
            if ticket_type == TicketType.REQUEST:
                category_title = _choose_category(
                    rng,
                    building_address=resident.building.address,
                    days_ago=(now - created_at).days,
                )
                category = categories[category_title]
            plans.append(
                _plan_closed_ticket(
                    rng,
                    now=now,
                    client=resident,
                    managers=managers,
                    category=category,
                    category_title=category_title,
                    ticket_type=ticket_type,
                    created_at=created_at,
                    picker=picker,
                )
            )

    slow_manager = next(manager for manager in managers if manager["is_slow"])
    for status, age_hours, unread in OPEN_TICKET_SPECS:
        created_at = now - timedelta(hours=age_hours)
        resident = rng.choice(residents)
        ticket_type = TicketType.QUESTION if rng.random() < QUESTION_SHARE else TicketType.REQUEST
        category = None
        category_title = None
        if ticket_type == TicketType.REQUEST:
            category_title = _choose_category(
                rng, building_address=resident.building.address, days_ago=0
            )
            category = categories[category_title]
        manager = None
        if status != TicketStatus.NEW:
            manager = slow_manager if age_hours >= 96 else rng.choice(managers)
        plans.append(
            _plan_open_ticket(
                rng,
                now=now,
                client=resident,
                category=category,
                category_title=category_title,
                ticket_type=ticket_type,
                created_at=created_at,
                status=status,
                manager=manager,
                unread=unread,
                picker=picker,
            )
        )
    return plans


def _sorted_plan(plan: _Plan) -> _Plan:
    plan.transitions.sort(key=lambda item: item.at)
    plan.messages.sort(key=lambda item: item.at)
    return plan


# Writing


async def generate(
    db: AsyncSession,
    *,
    now: datetime,
    volume: float = 1.0,
    rng_seed: int = DEMO_RANDOM_SEED,
) -> GenerateSummary:
    """Write the demo history. The caller owns the transaction."""
    await seed(db)
    rng = random.Random(rng_seed)
    buildings = await _get_or_create_buildings(db)
    categories = {
        category.title: category for category in (await db.scalars(select(Category))).all()
    }
    managers = await _create_managers(db, now=now)
    residents = await _create_residents(db, now=now, rng=rng, buildings=buildings)

    plans = [
        _sorted_plan(plan)
        for plan in _build_plans(
            rng,
            now=now,
            residents=residents,
            managers=managers,
            categories=categories,
            volume=volume,
        )
    ]

    db.add_all([plan.ticket for plan in plans])
    await db.flush()

    status_changes: list[StatusChange] = []
    messages: list[Message] = []
    for plan in plans:
        ticket = plan.ticket
        for transition in plan.transitions:
            status_changes.append(
                StatusChange(
                    ticket_id=ticket.id,
                    from_status=transition.from_status,
                    to_status=transition.to_status,
                    changed_by_id=transition.changed_by_id,
                    comment=transition.comment,
                    created_at=transition.at,
                )
            )
        for message in plan.messages:
            text = message.text
            if message.system_status is not None:
                text = status_message_text(
                    ticket.type, ticket.id, message.system_status, message.comment
                )
            messages.append(
                Message(
                    ticket_id=ticket.id,
                    sender_type=message.sender_type,
                    author_id=message.author_id,
                    text=text,
                    created_at=message.at,
                )
            )
    db.add_all(status_changes)
    db.add_all(messages)
    await db.flush()

    active_ticket: dict[int, int] = {}
    for plan in plans:
        active_ticket[plan.ticket.client_id] = plan.ticket.id
    for resident in residents:
        ticket_id = active_ticket.get(resident.user.id)
        if ticket_id is not None:
            resident.user.active_ticket_id = ticket_id
    await db.flush()

    open_tickets = sum(1 for plan in plans if plan.ticket.status in OPEN_STATUSES)
    return GenerateSummary(
        clients=sum(1 for resident in residents if is_demo_user(resident.user.max_user_id)),
        managers=sum(1 for manager in managers if manager["is_demo"]),
        residences=len(residents),
        tickets=len(plans),
        open_tickets=open_tickets,
        messages=len(messages),
        status_changes=len(status_changes),
    )


async def delete_demo(db: AsyncSession) -> DeleteSummary:
    """Remove demo data in FK order. Never touches non-demo rows."""
    summary = DeleteSummary()
    demo_user_ids = list(
        await db.scalars(select(User.id).where(User.max_user_id >= DEMO_MAX_USER_ID_BASE))
    )
    if not demo_user_ids:
        return summary

    demo_users = list(await db.scalars(select(User).where(User.id.in_(demo_user_ids))))
    demo_ticket_ids = list(
        await db.scalars(select(Ticket.id).where(Ticket.client_id.in_(demo_user_ids)))
    )

    if demo_ticket_ids:
        demo_message_ids = select(Message.id).where(Message.ticket_id.in_(demo_ticket_ids))
        await db.execute(
            delete(File).where(
                or_(File.ticket_id.in_(demo_ticket_ids), File.message_id.in_(demo_message_ids))
            )
        )
        await db.execute(delete(TicketTriage).where(TicketTriage.ticket_id.in_(demo_ticket_ids)))
        summary.tickets = len(demo_ticket_ids)
        summary.messages = (
            await db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.ticket_id.in_(demo_ticket_ids))
            )
            or 0
        )
        summary.status_changes = (
            await db.scalar(
                select(func.count())
                .select_from(StatusChange)
                .where(StatusChange.ticket_id.in_(demo_ticket_ids))
            )
            or 0
        )
        await db.execute(delete(Message).where(Message.ticket_id.in_(demo_ticket_ids)))
        await db.execute(delete(StatusChange).where(StatusChange.ticket_id.in_(demo_ticket_ids)))
        await db.execute(delete(Ticket).where(Ticket.id.in_(demo_ticket_ids)))

    await db.execute(delete(Residence).where(Residence.user_id.in_(demo_user_ids)))
    await db.execute(delete(AuthToken).where(AuthToken.user_id.in_(demo_user_ids)))
    await db.execute(delete(LoginToken).where(LoginToken.user_id.in_(demo_user_ids)))
    await db.flush()

    referenced: set[int] = set()
    for query in (
        select(Ticket.assignee_id).where(Ticket.assignee_id.in_(demo_user_ids)),
        select(StatusChange.changed_by_id).where(StatusChange.changed_by_id.in_(demo_user_ids)),
        select(Message.author_id).where(Message.author_id.in_(demo_user_ids)),
        select(ContentBlock.updated_by_id).where(ContentBlock.updated_by_id.in_(demo_user_ids)),
    ):
        referenced.update(value for value in (await db.scalars(query)).all() if value is not None)

    kept = [user for user in demo_users if user.id in referenced]
    removable = [user.id for user in demo_users if user.id not in referenced]
    if removable:
        await db.execute(delete(User).where(User.id.in_(removable)))
    await db.flush()

    summary.users_deleted = len(removable)
    summary.users_kept = [
        f"{user.first_name} {user.last_name or ''} (max_user_id {user.max_user_id})".strip()
        for user in kept
    ]
    return summary


async def ensure_demo(
    db: AsyncSession,
    *,
    now: datetime,
    volume: float = 1.0,
    rng_seed: int = DEMO_RANDOM_SEED,
) -> GenerateSummary | None:
    """Generate only if there is no demo data yet; otherwise change nothing."""
    if await has_demo_data(db):
        return None
    return await generate(db, now=now, volume=volume, rng_seed=rng_seed)


async def reset_demo(
    db: AsyncSession, *, now: datetime, volume: float = 1.0, rng_seed: int = DEMO_RANDOM_SEED
) -> GenerateSummary:
    await delete_demo(db)
    return await generate(db, now=now, volume=volume, rng_seed=rng_seed)


def _print_generate(summary: GenerateSummary) -> None:
    print(
        "Демо-данные готовы: "
        f"жильцов — {summary.clients}, "
        f"менеджеров — {summary.managers}, "
        f"адресов — {summary.residences}, "
        f"обращений — {summary.tickets} "
        f"(открытых — {summary.open_tickets}), "
        f"сообщений — {summary.messages}, "
        f"записей истории — {summary.status_changes}."
    )


def _print_delete(summary: DeleteSummary) -> None:
    print(
        "Демо-данные удалены: "
        f"обращений — {summary.tickets}, "
        f"сообщений — {summary.messages}, "
        f"записей истории — {summary.status_changes}, "
        f"пользователей — {summary.users_deleted}."
    )
    if summary.users_kept:
        print("Оставлены (на них ссылаются не-демо данные): " + "; ".join(summary.users_kept) + ".")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Демо-история обращений за полгода")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--reset", action="store_true", help="пересоздать демо-данные")
    group.add_argument("--delete", action="store_true", help="удалить только демо-данные")
    args = parser.parse_args()

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        if args.delete:
            summary = await delete_demo(db)
            await db.commit()
            _print_delete(summary)
            return
        if args.reset:
            summary = await reset_demo(db, now=now)
            await db.commit()
            _print_generate(summary)
            return
        summary = await ensure_demo(db, now=now)
        await db.commit()
        if summary is None:
            print(
                "Демо-данные уже есть. Запустите с --reset, чтобы пересоздать их "
                "относительно текущего времени."
            )
            return
    _print_generate(summary)


if __name__ == "__main__":
    asyncio.run(main())
