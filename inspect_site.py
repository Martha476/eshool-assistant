"""Step 1 helper: list the real search form fields on eschool.ug.

Usage: python inspect_site.py
Also save a results page for your test fixtures:
    python inspect_site.py --save tests/fixtures/real_results.html
Export the form's real option values for the RAG knowledge base:
    python inspect_site.py --export-options knowledge/eschool_options.json
Use what it prints to update SUPPORTED_FILTERS, build_params() and SELECTORS
in app/eschool_client.py.
"""
import json
import sys

import httpx
from bs4 import BeautifulSoup

URL = "https://eschool.ug/find-schools/search"


def export_options(soup: BeautifulSoup, path: str) -> None:
    """Write public form option values for the knowledge base."""
    data = {"_comment": "Exported from the live eSchool search form by inspect_site.py"}
    for name in ("location", "county"):
        select = soup.find("select", attrs={"name": name})
        values = []
        if select:
            for opt in select.find_all("option"):
                value = (opt.get("value") or "").strip()
                if value:
                    values.append(value)
        data[name] = values
    for field, name in (
        ("gender", "gender"),
        ("level", "levels[]"),
        ("admission_status", "admission_status"),
        ("boarding", "accomadation"),
        ("curriculum", "curriculums[]"),
        ("facility", "facilities[]"),
        ("affiliation", "religions[]"),
    ):
        values = []
        for control in soup.find_all(["input", "select"], attrs={"name": name}):
            value = (control.get("value") or "").strip()
            if value and value not in values:
                values.append(value)
            if control.name == "select":
                for option in control.find_all("option"):
                    value = (option.get("value") or "").strip()
                    if value and value not in values:
                        values.append(value)
        data[field] = values
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported option values to {path}: " + ", ".join(f"{k}={len(v)}" for k, v in data.items() if k != "_comment"))
    print("(An empty list means that field is not a <select> on the page; fill it by hand if needed.)")


def main() -> None:
    save = sys.argv[sys.argv.index("--save") + 1] if "--save" in sys.argv else None
    export = sys.argv[sys.argv.index("--export-options") + 1] if "--export-options" in sys.argv else None
    r = httpx.get(URL, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "eschool-assistant/0.1 (inspection)"})
    print("Status:", r.status_code)
    if save:
        with open(save, "w", encoding="utf-8") as f:
            f.write(r.text)
        print("Saved to", save)
    soup = BeautifulSoup(r.text, "html.parser")
    if export:
        export_options(soup, export)
    for form in soup.find_all("form"):
        print(f"\nFORM method={form.get('method')} action={form.get('action')}")
        for field in form.find_all(["input", "select", "textarea"]):
            print(f"  <{field.name}> name={field.get('name')} type={field.get('type')}")
            if field.name == "select":
                for opt in field.find_all("option"):
                    print(f"      option value={opt.get('value')!r}: {opt.get_text(strip=True)}")


if __name__ == "__main__":
    main()