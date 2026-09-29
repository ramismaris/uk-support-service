import json

import pytest

from src.services.insights import (
    SYSTEM_PROMPT,
    InsightsParseError,
    build_user_prompt,
    parse_answer,
)

NAMES = {"m1": "Пётр", "m2": "Анна"}


def _answer(items: list[dict]) -> str:
    return json.dumps({"items": items})


def test_parse_clean_answer() -> None:
    raw = _answer(
        [
            {"kind": "fact", "text": "Поступило 10 обращений."},
            {"kind": "warning", "text": "Просрочено 3 обращения."},
        ]
    )

    items = parse_answer(raw, NAMES)

    assert [item.kind for item in items] == ["fact", "warning"]
    assert [item.text for item in items] == [
        "Поступило 10 обращений.",
        "Просрочено 3 обращения.",
    ]


def test_parse_fenced_answer() -> None:
    raw = '```json\n{"items":[{"kind":"fact","text":"Всего 7 обращений."}]}\n```'

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Всего 7 обращений."]


def test_parse_plain_fence_without_language() -> None:
    raw = '```\n{"items":[{"kind":"fact","text":"Всего 7 обращений."}]}\n```'

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Всего 7 обращений."]


def test_parse_keeps_only_first_five() -> None:
    raw = _answer([{"kind": "fact", "text": f"Вывод {index}."} for index in range(7)])

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == [f"Вывод {index}." for index in range(5)]


def test_parse_skips_wrong_kind_and_keeps_others() -> None:
    raw = _answer(
        [
            {"kind": "bogus", "text": "Плохой тип."},
            {"kind": "observation", "text": "Хороший вывод."},
        ]
    )

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Хороший вывод."]


@pytest.mark.parametrize(
    "kind",
    [[], {}, 1],
)
def test_parse_skips_non_string_kind_and_keeps_others(kind: object) -> None:
    raw = _answer(
        [
            {"kind": kind, "text": "Плохой тип."},
            {"kind": "observation", "text": "Хороший вывод."},
        ]
    )

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Хороший вывод."]


@pytest.mark.parametrize(
    "text",
    ["", "   ", 42, None, ["не строка"], "a" * 301],
)
def test_parse_skips_invalid_text(text: object) -> None:
    raw = _answer(
        [
            {"kind": "fact", "text": text},
            {"kind": "fact", "text": "Валидный вывод."},
        ]
    )

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Валидный вывод."]


def test_parse_skips_non_dict_item() -> None:
    raw = json.dumps(
        {
            "items": [
                "не объект",
                {"kind": "fact", "text": "Валидный вывод."},
            ]
        }
    )

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Валидный вывод."]


def test_parse_replaces_tag_twice_in_one_text() -> None:
    raw = _answer([{"kind": "fact", "text": "[[m1]] и [[m2]] закрыли 12 заявок."}])

    items = parse_answer(raw, NAMES)

    assert items[0].text == "Пётр и Анна закрыли 12 заявок."


def test_parse_inserts_special_name_literally() -> None:
    names = {"m1": "Иван \\1 {0} [[m2]] $"}
    raw = _answer([{"kind": "fact", "text": "[[m1]] закрыл 10 заявок."}])

    items = parse_answer(raw, names)

    assert items[0].text == "Иван \\1 {0} [[m2]] $ закрыл 10 заявок."


def test_parse_skips_unknown_tag() -> None:
    raw = _answer(
        [
            {"kind": "fact", "text": "[[m9]] закрыл 10 заявок."},
            {"kind": "fact", "text": "Есть 10 заявок."},
        ]
    )

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Есть 10 заявок."]


def test_parse_skips_stray_open_brackets() -> None:
    raw = _answer(
        [
            {"kind": "fact", "text": "Рост [[ без закрытия 20%."},
            {"kind": "fact", "text": "Есть 20 заявок."},
        ]
    )

    items = parse_answer(raw, NAMES)

    assert [item.text for item in items] == ["Есть 20 заявок."]


@pytest.mark.parametrize(
    "raw",
    [
        "не JSON",
        '["список"]',
        "{}",
        '{"items": "x"}',
        '{"items": []}',
        '{"items": [{"kind": "bogus", "text": "x"}]}',
        '```json\n{"items": []}\n```',
    ],
)
def test_parse_raises_on_invalid_answers(raw: str) -> None:
    with pytest.raises(InsightsParseError):
        parse_answer(raw, NAMES)


def test_parse_deeply_nested_answer_raises_parse_error() -> None:
    raw = "[" * 100000 + "]" * 100000

    with pytest.raises(InsightsParseError):
        parse_answer(raw, NAMES)


def test_build_user_prompt_is_compact_and_keeps_cyrillic() -> None:
    data = {"title": "🚰 Сантехника", "created": 10, "nested": {"value": None}}

    prompt = build_user_prompt(data)

    assert prompt == '{"title":"🚰 Сантехника","created":10,"nested":{"value":null}}'
    assert "\\u04" not in prompt
    assert json.loads(prompt) == data


def test_system_prompt_mentions_tag_form_and_answer_shape() -> None:
    assert "[[m1]]" in SYSTEM_PROMPT
    assert '"items"' in SYSTEM_PROMPT
