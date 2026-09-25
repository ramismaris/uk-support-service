import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus, TicketType
from src.models.building import Building
from src.models.category import Category
from src.models.residence import Residence
from src.models.ticket import Ticket
from src.models.user import User


async def _create_user(db: AsyncSession, max_user_id: int = 1) -> User:
    user = User(max_user_id=max_user_id, first_name="Test")
    db.add(user)
    await db.flush()
    return user


async def _create_building(db: AsyncSession, address: str = "ul. Lenina, 5") -> Building:
    building = Building(address=address)
    db.add(building)
    await db.flush()
    return building


async def _create_category(db: AsyncSession, title: str = "Plumbing") -> Category:
    category = Category(title=title, sort_order=0)
    db.add(category)
    await db.flush()
    return category


async def test_ticket_id_starts_at_1000(db: AsyncSession) -> None:
    user = await _create_user(db)
    building = await _create_building(db)
    category = await _create_category(db)

    ticket = Ticket(
        type=TicketType.REQUEST,
        status=TicketStatus.NEW,
        client_id=user.id,
        building_id=building.id,
        apartment="12",
        category_id=category.id,
        description="Leaking tap",
    )
    db.add(ticket)
    await db.flush()

    assert ticket.id >= 1000


async def test_request_without_address_violates_check(db: AsyncSession) -> None:
    user = await _create_user(db)

    db.add(
        Ticket(
            type=TicketType.REQUEST,
            status=TicketStatus.NEW,
            client_id=user.id,
            description="No address",
        )
    )

    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


async def test_rating_out_of_range_violates_check(db: AsyncSession) -> None:
    user = await _create_user(db)
    building = await _create_building(db)
    category = await _create_category(db)

    db.add(
        Ticket(
            type=TicketType.REQUEST,
            status=TicketStatus.CLOSED,
            client_id=user.id,
            building_id=building.id,
            apartment="12",
            category_id=category.id,
            description="Rated",
            rating=6,
        )
    )

    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


async def test_second_primary_residence_violates_partial_unique_index(db: AsyncSession) -> None:
    user = await _create_user(db)
    building = await _create_building(db)

    db.add(Residence(user_id=user.id, building_id=building.id, apartment="1", is_primary=True))
    await db.flush()

    db.add(Residence(user_id=user.id, building_id=building.id, apartment="2", is_primary=True))

    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


async def test_duplicate_residence_violates_unique_constraint(db: AsyncSession) -> None:
    user = await _create_user(db)
    building = await _create_building(db)

    db.add(Residence(user_id=user.id, building_id=building.id, apartment="1"))
    await db.flush()

    db.add(Residence(user_id=user.id, building_id=building.id, apartment="1"))

    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


async def test_question_without_address_is_accepted(db: AsyncSession) -> None:
    user = await _create_user(db)

    ticket = Ticket(
        type=TicketType.QUESTION,
        status=TicketStatus.NEW,
        client_id=user.id,
        description="When is the elevator repaired?",
    )
    db.add(ticket)
    await db.flush()

    assert ticket.id >= 1000


@pytest.mark.parametrize("rating", [1, 5])
async def test_rating_in_range_is_accepted(db: AsyncSession, rating: int) -> None:
    user = await _create_user(db)
    building = await _create_building(db)
    category = await _create_category(db)

    ticket = Ticket(
        type=TicketType.REQUEST,
        status=TicketStatus.CLOSED,
        client_id=user.id,
        building_id=building.id,
        apartment="12",
        category_id=category.id,
        description="Rated",
        rating=rating,
    )
    db.add(ticket)
    await db.flush()

    assert ticket.rating == rating


async def test_non_primary_residence_next_to_primary_is_accepted(db: AsyncSession) -> None:
    user = await _create_user(db)
    building = await _create_building(db)

    db.add(Residence(user_id=user.id, building_id=building.id, apartment="1", is_primary=True))
    db.add(Residence(user_id=user.id, building_id=building.id, apartment="2", is_primary=False))
    await db.flush()

    residences = (
        (await db.execute(select(Residence).where(Residence.user_id == user.id))).scalars().all()
    )
    assert len(residences) == 2
