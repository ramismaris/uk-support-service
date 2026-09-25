from zoneinfo import ZoneInfo

from src.core.constants import TicketStatus, TicketType
from src.core.texts import STATUS_LABELS, format_address
from src.models.status_change import StatusChange
from src.models.ticket import Ticket

_STATUS_ICONS: dict[TicketStatus, str] = {
    TicketStatus.WAITING_CLIENT: "🟡",
    TicketStatus.REJECTED: "🔴",
}
_DEFAULT_ICON = "🟢"

_PENDING_STEPS: dict[TicketStatus, tuple[TicketStatus, ...]] = {
    TicketStatus.NEW: (TicketStatus.IN_PROGRESS, TicketStatus.CLOSED),
    TicketStatus.IN_PROGRESS: (TicketStatus.CLOSED,),
    TicketStatus.WAITING_CLIENT: (TicketStatus.CLOSED,),
    TicketStatus.CLOSED: (),
    TicketStatus.REJECTED: (),
}


def build_status_card(ticket: Ticket, history: list[StatusChange], tz: ZoneInfo) -> str:
    if ticket.type == TicketType.QUESTION:
        title = f"**Вопрос №{ticket.id}**"
    else:
        title = f"**Заявка №{ticket.id}**"
        if ticket.category is not None:
            title += f" · {ticket.category.title}"

    lines = [title]
    if ticket.type == TicketType.REQUEST and ticket.building is not None and ticket.apartment:
        lines.append(format_address(ticket.building.address, ticket.apartment))
    lines.append("")

    for change in history:
        local_time = change.created_at.astimezone(tz)
        icon = _STATUS_ICONS.get(change.to_status, _DEFAULT_ICON)
        label = STATUS_LABELS[change.to_status]
        lines.append(f"{icon} {label} — {local_time:%d.%m %H:%M}")

    for status in _PENDING_STEPS[ticket.status]:
        lines.append(f"⚪ {STATUS_LABELS[status]}")

    return "\n".join(lines)
