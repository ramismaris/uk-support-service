import pytest
from pydantic import TypeAdapter, ValidationError

from src.core.texts import DIRECTORY_NAME_MARKUP
from src.schemas.directory import DIRECTORY_NAME_LIMIT, DirectoryName

validate = TypeAdapter(DirectoryName).validate_python


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  ул.   Мира,\n 1 ", "ул. Мира, 1"),
        ("\tСантехника\t", "Сантехника"),
        ("Отопление\xa0", "Отопление"),
        ("а\xa0 б", "а б"),
    ],
)
def test_collapses_whitespace(raw: str, expected: str) -> None:
    assert validate(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "\t\n", "\xa0"])
def test_empty_or_whitespace_only_is_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        validate(raw)


def test_length_bounds() -> None:
    assert validate("a" * DIRECTORY_NAME_LIMIT) == "a" * DIRECTORY_NAME_LIMIT

    with pytest.raises(ValidationError):
        validate("a" * (DIRECTORY_NAME_LIMIT + 1))


@pytest.mark.parametrize("char", list("*_~^+`[]#>"))
def test_markup_characters_are_rejected(char: str) -> None:
    with pytest.raises(ValidationError) as exc:
        validate(f"Сантехника{char}")

    assert DIRECTORY_NAME_MARKUP in str(exc.value)


def test_nul_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate("Сантехника\x00")


@pytest.mark.parametrize(
    "value",
    [
        "🔥 Отопление",
        "пр-т Мира, 28/2 (корп. 1)",
    ],
)
def test_allowed_names_pass(value: str) -> None:
    assert validate(value) == value


def test_non_string_is_rejected() -> None:
    with pytest.raises(ValidationError):
        validate(123)
