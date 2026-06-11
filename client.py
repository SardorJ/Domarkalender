from dataclasses import dataclass
import importlib
from typing import Optional
import os
from playwright.sync_api import sync_playwright
import time
import csv
from pathlib import Path

LOGIN_URL = "https://fogis.svenskfotboll.se/FogisDomarklient/Start/Frameset"
DEFAULT_OUTPUT_PATH = "uppdrag.csv"


@dataclass
class LoginResult:
    ok: bool
    final_url: str
    error: Optional[str] = None


@dataclass
class Assignment:
    datetime: str
    competition: str
    round: str
    match_no: str
    match: str
    venue: str
    referees: str
    notes: str


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def _cell_text(cell, strip_links: bool = False) -> str:
    script = """
        (el, stripLinks) => {
            const clone = el.cloneNode(true);
            clone.querySelectorAll('style,script').forEach(n => n.remove());
            if (stripLinks) {
                clone.querySelectorAll('a').forEach(n => n.remove());
            }
            return (clone.innerText || '').trim();
        }
    """
    text = cell.evaluate(script, strip_links)
    return _normalize_ws(text)


def _has_dotenv() -> bool:
    try:
        importlib.import_module("dotenv")
        return True
    except ModuleNotFoundError:
        return False


def _resolve_screenshot_path(path: str) -> str:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    return os.path.abspath(path)


def _find_locator(page, selector: str):
    """Helper to find a locator in the main page or any frame."""
    loc = page.locator(selector)
    if loc.count() > 0:
        return loc.first
    for frame in page.frames:
        floc = frame.locator(selector)
        if floc.count() > 0:
            return floc.first
    return None


def login(
    username: str,
    password: str,
    url: str = LOGIN_URL,
    headless: bool = True,
    debug: bool = False,
    screenshot_path: Optional[str] = None,
    output_path: str = DEFAULT_OUTPUT_PATH,
) -> LoginResult:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60_000)

        try:
            _user_input(page, username=username, debug=debug)
            _password_input(page, password=password, debug=debug)
            _login_button(page, debug=debug)

            if debug:
                print("[debug] clicked submit")
            page.wait_for_load_state("networkidle", timeout=60_000)
            page.wait_for_timeout(3000)

            _click_after_login(page, debug=debug)
            table_scope = _wait_for_uppdrag_table(page, timeout_ms=20_000)
            assignments = _parse_assignments(table_scope)
            if debug:
                print(f"[debug] assignments found: {len(assignments)}")

            _write_assignments_csv(assignments, output_path)

        except Exception as exc:
            browser.close()
            return LoginResult(ok=False, final_url=url, error=str(exc))

        final_url = page.url
        if debug:
            print(f"[debug] final url: {final_url}")
        browser.close()
        return LoginResult(ok=True, final_url=final_url)


def _user_input(page, username: str, debug: bool = False) -> None:
    selector = "#Username"
    locator = page.locator(selector)
    if locator.is_visible():
        locator.fill(username)
        if debug:
            print(f"[debug] filled {selector} with {username}")
    else:
        raise ValueError(f"Selector {selector} is not visible")


def _password_input(page, password: str, debug: bool = False) -> None:
    selector = "#Password"
    locator = page.locator(selector)
    if locator.is_visible():
        locator.fill(password)
        if debug:
            print(f"[debug] filled {selector}")
    else:
        raise ValueError(f"Selector {selector} is not visible")


def _login_button(page, debug: bool = False) -> None:
    locator = page.get_by_role("button", name="Logga in")
    if locator.is_visible():
        locator.click()
        if debug:
            print(f"[debug] clicked login button")
    else:
        raise ValueError(f"Login button is not visible")


def _click_after_login(page, debug: bool = False) -> None:
    # First menu item
    locator = _find_locator(page, "#FogisDomarMeny1_divDomareUppdrag")
    if locator is None or locator.count() == 0:
        raise ValueError("Uppdrag-tabben hittades inte")

    locator.first.click()
    if debug:
        print("[debug] clicked Uppdrag tab")

    page.wait_for_timeout(4000)

    # Submenu item
    locator = _find_locator(page, "#divHeaderUnderMenyUppdragUppdrag")
    if locator is None or locator.count() == 0:
        raise ValueError("Uppdrag-tabben hittades inte")

    locator.first.click()
    if debug:
        print("[debug] clicked Uppdrag submenu")


def _wait_for_uppdrag_table(page, timeout_ms: int = 20_000):
    deadline = time.monotonic() + (timeout_ms / 1000)
    selector = "#divUppdrag"
    while time.monotonic() < deadline:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            return page

        for frame in page.frames:
            frame_locator = frame.locator(selector)
            if frame_locator.count() > 0 and frame_locator.first.is_visible():
                return frame

        page.wait_for_timeout(250)

    raise ValueError("Uppdrag-tabellen hittades inte (timeout)")


def _parse_assignments(table_scope) -> list[Assignment]:
    rows = table_scope.locator("#divUppdrag table.fogisInfoTable tbody tr")
    assignments: list[Assignment] = []
    for index in range(rows.count()):
        row = rows.nth(index)
        row_classes = (row.get_attribute("class") or "").split()
        if "inaktivMatch" in row_classes:
            continue
        cells = row.locator("td")
        if cells.count() < 8:
            continue
        values = [
            _cell_text(cells.nth(0)),
            _cell_text(cells.nth(1)),
            _cell_text(cells.nth(2)),
            _cell_text(cells.nth(3)),
            _cell_text(cells.nth(4)),
            _cell_text(cells.nth(5), strip_links=True),
            _cell_text(cells.nth(6)),
            _cell_text(cells.nth(7)),
        ]
        if not any(values):
            continue
        assignments.append(
            Assignment(
                datetime=values[0],
                competition=values[1],
                round=values[2],
                match_no=values[3],
                match=values[4],
                venue=values[5],
                referees=values[6],
                notes=values[7],
            )
        )
    return assignments


def _write_assignments_csv(assignments: list[Assignment], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "datetime",
                "competition",
                "round",
                "match_no",
                "match",
                "venue",
                "referees",
                "notes",
            ],
        )
        writer.writeheader()
        for assignment in assignments:
            writer.writerow(
                {
                    "datetime": assignment.datetime,
                    "competition": assignment.competition,
                    "round": assignment.round,
                    "match_no": assignment.match_no,
                    "match": assignment.match,
                    "venue": assignment.venue,
                    "referees": assignment.referees,
                    "notes": assignment.notes,
                }
            )


def get_schedule(
    url: str = LOGIN_URL,
    headless: bool = True,
    debug: bool = False,
    screenshot_path: Optional[str] = None,
    output_path: str = DEFAULT_OUTPUT_PATH,
) -> LoginResult:

    # Load username and password from environment variables
    dotenv = importlib.import_module("dotenv") if _has_dotenv() else None
    if dotenv is not None:
        dotenv.load_dotenv(override=True)
    username = os.environ.get("FOGIS_USERNAME")
    password = os.environ.get("FOGIS_PASSWORD")
    if username is None or password is None:
        return LoginResult(
            ok=False,
            final_url=url,
            error="Username or password is not set"
        )

    return login(
        username=username,
        password=password,
        url=url,
        headless=headless,
        debug=debug,
        screenshot_path=screenshot_path,
        output_path=output_path,
    )


if __name__ == "__main__":
    result = get_schedule(debug=True, screenshot_path="login_debug.png")
    print(result)