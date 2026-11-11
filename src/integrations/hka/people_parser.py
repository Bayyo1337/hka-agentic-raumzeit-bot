import re
from html import unescape

from src.domain.errors import DomainError, ErrorCode
from src.domain.models import Person


def parse_people_html(html: str) -> tuple[Person, ...]:
    """Parse the stable person-card fields without exposing raw HTML downstream."""
    blocks = re.findall(r"<tr\b[^>]*>.*?</tr>", html, flags=re.IGNORECASE | re.DOTALL)
    people: list[Person] = []
    for block in blocks:
        name_match = re.search(
            r'class=["\'][^"\']*person__user-academic-title[^"\']*["\'][^>]*>(.*?)</',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        email_match = re.search(r"([\w.+-]+)<span[^>]*>.*?</span>@h-ka\.de", block, flags=re.I | re.S)
        if not name_match or not email_match:
            continue
        name = _clean(name_match.group(1))
        account = email_match.group(1)
        if not name:
            raise DomainError(ErrorCode.SOURCE_ERROR, "HKA person record has an empty name")
        people.append(Person(name=name, email=f"{account}@h-ka.de", account=account))
    return tuple(people)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()
