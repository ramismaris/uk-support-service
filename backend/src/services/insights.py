import json
import re
from typing import Any

from src.schemas.insights import InsightItem

SYSTEM_PROMPT = """Ты аналитик управляющей компании (УК). Тебе дают цифры дашборда обращений жильцов за период в формате JSON. Напиши от 3 до 5 коротких выводов для руководителя.

Правила:
- Каждый вывод — одно предложение до 160 символов, обязательно с числом из данных.
- kind: "fact" — что произошло; "observation" — заметная закономерность или сравнение; "warning" — то, на что стоит обратить внимание: рост, просрочки, перекос по дому, категории или менеджеру.
- Используй только числа из данных. Ничего не выдумывай. Если в данных есть готовое значение (share, growth, previous, previous_created, reaction_vs_others, resolution_vs_others), бери его, а не пересчитывай.
- growth — во сколько раз изменилось число обращений: 7.7 значит «в 7.7 раза больше», 0.5 — «в 2 раза меньше». reaction_vs_others и resolution_vs_others — во сколько раз время менеджера больше (число больше 1) или меньше (меньше 1), чем у остальных менеджеров.
- top_building у категории — дом с наибольшим числом её обращений, share — его доля в категории. Большая доля одного дома — перекос, о нём стоит написать.
- Сравнивай период с прошлым (previous, previous_created). Ищи резкие изменения и перекосы по категориям, домам и менеджерам.
- Не делай выводов по выборке меньше 5 обращений.
- Менеджера называй только тегом вида [[m1]] — так, как он записан в поле ref, и всегда в именительном падеже со словом «менеджер»: «менеджер [[m1]] отвечает втрое медленнее остальных». Тег не склоняется. Других тегов не придумывай.
- Не повторяй один вывод разными словами. Без советов, без обращений к читателю, без markdown.
- Нормы SLA — в поле sla (часы). Время реакции — в минутах, время решения — в часах.

Ответь только JSON-объектом такого вида: {"items":[{"kind":"fact","text":"..."}]}"""

MAX_ITEMS = 5
MAX_TEXT_LENGTH = 300
KINDS = {"fact", "observation", "warning"}

_TAG_RE = re.compile(r"\[\[(m\d+)\]\]")


class InsightsParseError(ValueError):
    pass


def build_user_prompt(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def parse_answer(raw: str, names: dict[str, str]) -> list[InsightItem]:
    data = _load_object(raw)
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise InsightsParseError("answer has no items list")

    items: list[InsightItem] = []
    for raw_item in raw_items:
        item = _parse_item(raw_item, names)
        if item is None:
            continue
        items.append(item)
        if len(items) >= MAX_ITEMS:
            break

    if not items:
        raise InsightsParseError("answer has no valid items")
    return items


def _load_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise InsightsParseError("answer is not valid JSON") from exc
    if not isinstance(data, dict):
        raise InsightsParseError("answer is not a JSON object")
    return data


def _parse_item(raw_item: object, names: dict[str, str]) -> InsightItem | None:
    if not isinstance(raw_item, dict):
        return None
    kind = raw_item.get("kind")
    if not isinstance(kind, str) or kind not in KINDS:
        return None
    text = raw_item.get("text")
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text or len(text) > MAX_TEXT_LENGTH:
        return None

    labels = _TAG_RE.findall(text)
    if any(label not in names for label in labels):
        return None
    # Check unmatched brackets before substitution: a manager name may itself
    # contain "[[" or "]]", and it must still be inserted literally.
    residual = _TAG_RE.sub("", text)
    if "[[" in residual or "]]" in residual:
        return None

    replaced = _TAG_RE.sub(lambda match: names[match.group(1)], text)
    return InsightItem(kind=kind, text=replaced)
