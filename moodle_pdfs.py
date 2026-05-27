#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from playwright.sync_api import sync_playwright

DEFAULT_BASE_URL = "https://moodle.uam.es"
STATE_PATH = Path("storage_state.json")
def default_download_root() -> Path:
    if os.name == "nt":
        return Path.home() / "Downloads" / "moodle"
    if sys.platform == "darwin":
        return Path.home() / "Downloads" / "moodle"
    return Path.home() / "Descargas" / "moodle"


DEFAULT_DOWNLOAD_ROOT = default_download_root()

COURSE_LINK_SELECTOR = 'a[href*="/course/view.php?id="]'
ALL_LINKS_SELECTOR = "a[href]"
DATA_FILEURL_SELECTOR = "[data-fileurl]"


def sanitize_name(name: str) -> str:
    name = name.strip() or "curso"
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"[^A-Za-z0-9._() \-]", "_", name)
    return name[:120].strip() or "curso"


def ensure_login_state(base_url: str) -> None:
    if STATE_PATH.exists():
        return

    print("No se encontro storage_state.json. Se abrira el navegador para iniciar sesion.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(base_url, wait_until="domcontentloaded")
        print("Inicia sesion manualmente en el navegador.")
        input("Cuando hayas terminado, pulsa Enter aqui para guardar la sesion...")
        context.storage_state(path=str(STATE_PATH))
        browser.close()


def load_session_from_state(base_url: str) -> requests.Session:
    session = requests.Session()
    with STATE_PATH.open("r", encoding="utf-8") as f:
        state = json.load(f)

    host = (urlparse(base_url).hostname or "").lower()
    for cookie in state.get("cookies", []):
        domain = (cookie.get("domain", "") or "").lower()
        if host and host not in domain:
            continue
        session.cookies.set(
            cookie.get("name"),
            cookie.get("value"),
            domain=domain,
            path=cookie.get("path", "/"),
        )

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
            "Accept": "text/html,application/pdf,*/*;q=0.8",
        }
    )
    return session


def collect_courses(base_url: str) -> list[dict]:
    courses = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_PATH))
        page = context.new_page()
        page.goto(f"{base_url}/my/", wait_until="networkidle")

        raw = page.eval_on_selector_all(
            COURSE_LINK_SELECTOR,
            "els => els.map(e => ({href: e.href, text: e.textContent || ''}))",
        )
        seen = set()
        for item in raw:
            href = item.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            text = (item.get("text") or "").strip()
            courses.append({"href": href, "name": text})

        browser.close()
    return courses


def extract_links_for_course(course_url: str) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_PATH))
        page = context.new_page()
        page.goto(course_url, wait_until="networkidle")

        raw = page.eval_on_selector_all(
            ALL_LINKS_SELECTOR,
            "els => els.map(e => ({href: e.href, text: e.textContent || ''}))",
        )
        raw_fileurls = page.eval_on_selector_all(
            DATA_FILEURL_SELECTOR,
            "els => els.map(e => ({href: e.getAttribute('data-fileurl') || '', text: e.textContent || ''}))",
        )
        browser.close()

    links = []
    for item in raw + raw_fileurls:
        href = item.get("href", "")
        text = (item.get("text") or "").strip()
        if not href:
            continue
        lowered = href.lower()
        if (
            ".pdf" in lowered
            or "pluginfile.php" in lowered
            or "forcedownload=1" in lowered
            or "/mod/resource/view.php" in lowered
        ):
            links.append({"href": href, "text": text})
    return links


def filename_from_headers(resp: requests.Response, fallback_url: str) -> str:
    cd = resp.headers.get("Content-Disposition", "")
    match = re.search(r"filename\*?=([^;]+)", cd, re.IGNORECASE)
    if match:
        name = match.group(1).strip().strip('"')
        name = name.split("''")[-1]
        return unquote(name)

    path = urlparse(fallback_url).path
    name = os.path.basename(path)
    return unquote(name) or "archivo.pdf"


def is_pdf_response(resp: requests.Response) -> bool:
    ctype = resp.headers.get("Content-Type", "").lower()
    if "application/pdf" in ctype:
        return True
    cd = resp.headers.get("Content-Disposition", "").lower()
    return ".pdf" in cd


def download_pdf(session: requests.Session, url: str, dest_dir: Path, referer: str) -> bool:
    headers = {"Referer": referer}
    try:
        with session.get(url, headers=headers, stream=True, allow_redirects=True, timeout=60) as resp:
            resp.raise_for_status()
            if not is_pdf_response(resp):
                return False

            filename = sanitize_name(filename_from_headers(resp, url))
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            dest_path = dest_dir / filename
            if dest_path.exists():
                return True

            dest_dir.mkdir(parents=True, exist_ok=True)
            with dest_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        f.write(chunk)
            return True
    except requests.RequestException:
        return False


def prompt_settings() -> tuple[str, Path]:
    base_url = input(f"BASE_URL [{DEFAULT_BASE_URL}]: ").strip()
    if not base_url:
        base_url = DEFAULT_BASE_URL
    download_root_input = input(f"DOWNLOAD_ROOT [{DEFAULT_DOWNLOAD_ROOT}]: ").strip()
    if not download_root_input:
        download_root = DEFAULT_DOWNLOAD_ROOT
    else:
        download_root = Path(os.path.expanduser(download_root_input))
    return base_url.rstrip("/"), download_root


def prompt_course_selection(courses: list[dict]) -> list[dict]:
    print("Asignaturas disponibles:")
    for idx, course in enumerate(courses, start=1):
        name = sanitize_name(course.get("name", ""))
        print(f"  {idx}. {name}")

    raw = input(
        "Selecciona asignaturas (ej: 1,3,5) o Enter para todas: "
    ).strip()
    if not raw:
        return courses

    selected = []
    seen = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part)
        except ValueError:
            continue
        if idx < 1 or idx > len(courses):
            continue
        if idx in seen:
            continue
        seen.add(idx)
        selected.append(courses[idx - 1])

    return selected


def main() -> int:
    base_url, download_root = prompt_settings()
    ensure_login_state(base_url)
    download_root.mkdir(parents=True, exist_ok=True)

    courses = collect_courses(base_url)
    if not courses:
        print("No se encontraron cursos en /my/. Revisa que la sesion sea valida.")
        return 1

    courses = prompt_course_selection(courses)
    if not courses:
        print("No se seleccionaron asignaturas. Saliendo.")
        return 0

    session = load_session_from_state(base_url)
    total = 0

    for course in courses:
        course_name = sanitize_name(course.get("name", ""))
        course_url = course["href"]
        dest_dir = download_root / course_name

        links = extract_links_for_course(course_url)
        seen = set()
        print(f"Curso: {course_name} ({len(links)} enlaces candidatos)")
        for link in links:
            href = link.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            if download_pdf(session, href, dest_dir, course_url):
                total += 1

    print(f"Descargas completadas. PDFs guardados: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
