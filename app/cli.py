"""Command-line interface: python -m app.cli "your request" """
import sys
from pathlib import Path

from dotenv import load_dotenv

from .schemas import AssistantResponse
from .service import handle

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def render(r: AssistantResponse) -> str:
    lines = [f"[{r.status}] {r.message}"]
    if r.criteria:
        lines.append("Criteria: " + (str(r.criteria.specified()) or "(none specified)"))
    if r.search_url:
        lines.append(f"Search URL: {r.search_url}")
    for i, m in enumerate(r.results, 1):
        s = m.school
        lines.append(f"\n{i}. {s.name}" + (f"  ({s.url})" if s.url else ""))
        if s.location:
            lines.append(f"   Location: {s.location}")
        if s.level:
            lines.append(f"   Level: {s.level}")
        if s.gender:
            lines.append(f"   Gender: {s.gender}")
        if s.boarding:
            lines.append(f"   Accommodation: {s.boarding}")
        lines.append(
            f"   Fees: {'UGX {:,}'.format(s.fees) if s.fees is not None else 'not listed'}"
        )
        if s.admission_status:
            lines.append(f"   Admission status: {s.admission_status}")
        if s.rating:
            lines.append(f"   Rating: {s.rating}")
        for reason in m.matched:
            lines.append(f"   + {reason}")
        for gap in m.unverified:
            lines.append(f"   ? {gap}")
    return "\n".join(lines)


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    text = " ".join(sys.argv[1:]) or input("Describe the school you are looking for: ")
    print(render(handle(text)))


if __name__ == "__main__":
    main()