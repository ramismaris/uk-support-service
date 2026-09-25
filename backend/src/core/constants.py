from enum import StrEnum

# The largest value of a Postgres bigint.
BIGINT_MAX = 2**63 - 1


class UserRole(StrEnum):
    CLIENT = "CLIENT"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class TicketType(StrEnum):
    REQUEST = "REQUEST"
    QUESTION = "QUESTION"


class TicketStatus(StrEnum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_CLIENT = "WAITING_CLIENT"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class TicketPriority(StrEnum):
    NORMAL = "NORMAL"
    URGENT = "URGENT"


class SenderType(StrEnum):
    CLIENT = "CLIENT"
    STAFF = "STAFF"
    SYSTEM = "SYSTEM"


class ButtonType(StrEnum):
    CALLBACK = "CALLBACK"
    LINK = "LINK"
    OPEN_APP = "OPEN_APP"


class ContentKey(StrEnum):
    WELCOME = "WELCOME"
    EMERGENCY = "EMERGENCY"
    SERVICES = "SERVICES"
    PAYMENT = "PAYMENT"
    CONTACTS = "CONTACTS"
    THEME = "THEME"
