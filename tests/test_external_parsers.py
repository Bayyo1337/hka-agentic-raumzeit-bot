import pytest

from src.domain.errors import DomainError
from src.integrations.hka.people_parser import parse_people_html
from src.integrations.mensa.parser import parse_meals


def test_people_parser_normalizes_html():
    html = """
    <tr><span class="person__user-academic-title">Dr. Ada <b>Lovelace</b></span>
    ada<span class="spam">spam prevention</span>@h-ka.de</tr>
    """
    person = parse_people_html(html)[0]
    assert person.name == "Dr. Ada Lovelace"
    assert person.email == "ada@h-ka.de"


def test_meal_parser_normalizes_labels():
    meals = parse_meals(
        [{"id": "wahlessen1", "title": "Curry", "allergens": ["WE"], "vegan": "ja"}]
    )
    assert meals[0].meal_id == "wahlessen1"
    assert meals[0].allergens == ("WE",)
    assert meals[0].vegan is True


def test_meal_parser_rejects_missing_identity():
    with pytest.raises(DomainError):
        parse_meals([{"title": "No ID"}])
