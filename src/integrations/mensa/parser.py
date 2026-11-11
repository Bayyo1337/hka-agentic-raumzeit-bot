from collections.abc import Mapping

from src.domain.errors import DomainError, ErrorCode
from src.domain.models import Meal


def parse_meals(payload: object) -> tuple[Meal, ...]:
    if not isinstance(payload, list):
        raise DomainError(ErrorCode.SOURCE_ERROR, "Mensa response is not a list")
    meals: list[Meal] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise DomainError(ErrorCode.SOURCE_ERROR, "Mensa meal is not an object")
        meal_id = _text(item.get("id") or item.get("meal_id"))
        name = _text(item.get("name") or item.get("title"))
        if not meal_id or not name:
            raise DomainError(ErrorCode.SOURCE_ERROR, "Mensa meal is missing id or name")
        meals.append(
            Meal(
                meal_id=meal_id,
                name=name,
                price=_optional(item.get("price")),
                allergens=_texts(item.get("allergens")),
                additives=_texts(item.get("additives")),
                vegan=_bool_or_none(item.get("vegan")),
                vegetarian=_bool_or_none(item.get("vegetarian")),
            )
        )
    return tuple(meals)


def _texts(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list):
        return tuple(text for item in value if (text := _text(item)))
    raise DomainError(ErrorCode.SOURCE_ERROR, "Mensa labels have an invalid shape")


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _optional(value: object) -> str | None:
    text = _text(value)
    return text or None


def _bool_or_none(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.casefold()
        if lowered in {"true", "yes", "ja", "vegan", "vegetarian"}:
            return True
        if lowered in {"false", "no", "nein"}:
            return False
    raise DomainError(ErrorCode.SOURCE_ERROR, "Mensa dietary flag has an invalid shape")
