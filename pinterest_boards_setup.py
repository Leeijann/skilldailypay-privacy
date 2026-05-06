"""
SkillDailyPay — Pinterest Board Setup
Silix LLC / skilldailypay.com

Loads a saved Pinterest session from cookies.json, checks all existing boards,
and creates any missing boards for the full multi-agency content system.

Usage:
    1. Export your Pinterest session cookies to cookies.json (see README below).
    2. pip install playwright && playwright install chromium
    3. python pinterest_boards_setup.py

Cookie export:
    Use the "EditThisCookie" or "Cookie-Editor" browser extension on pinterest.com,
    export as JSON, and save the file as cookies.json in the same directory.
"""

import json
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

COOKIES_FILE = Path(__file__).parent / "cookies.json"

# ---------------------------------------------------------------------------
# Full board list for the SkillDailyPay multi-agency content system
# Format: (board_name, secret)  — secret=True keeps the board private
# ---------------------------------------------------------------------------
BOARDS = [
    # ── Social Media Strategy ──────────────────────────────────────────────
    ("Social Media Marketing Tips",         False),
    ("Content Strategy & Planning",         False),
    ("Social Media Content Calendar",       False),
    ("Content Repurposing Ideas",           False),
    ("Viral Content Ideas",                 False),

    # ── Platform-Specific ──────────────────────────────────────────────────
    ("Pinterest Marketing",                 False),
    ("Facebook Marketing Tips",             False),
    ("Instagram Growth & Tips",             False),
    ("YouTube Content Creation",            False),
    ("TikTok Strategy & Growth",            False),
    ("LinkedIn Marketing",                  False),
    ("Twitter X Marketing",                 False),

    # ── Blog & Website ─────────────────────────────────────────────────────
    ("Blogging Tips & Growth",              False),
    ("Blog Post Ideas",                     False),
    ("SEO & Website Traffic",               False),
    ("WordPress & Website Design",          False),
    ("Email Marketing Tips",                False),

    # ── Content Creation ───────────────────────────────────────────────────
    ("Content Creation Tips",               False),
    ("Graphic Design & Canva Templates",    False),
    ("Video Content & Reels Ideas",         False),
    ("Short Form Video Strategy",           False),
    ("Storytelling & Copywriting",          False),
    ("Brand Aesthetic & Visual Identity",   False),

    # ── Monetization & SkillDailyPay Niche ────────────────────────────────
    ("Make Money Online",                   False),
    ("Passive Income Ideas",                False),
    ("Side Hustle Ideas",                   False),
    ("Digital Products & Income",           False),
    ("Freelancing & Agency Life",           False),
    ("Online Business & Entrepreneurship",  False),

    # ── Agency Operations ─────────────────────────────────────────────────
    ("Digital Marketing Agency Tips",       False),
    ("Client Management & Onboarding",      False),
    ("Social Media Management Tools",       False),
    ("AI Tools for Content Creators",       False),
    ("Marketing Analytics & Reporting",     False),

    # ── Inspiration & Lifestyle ────────────────────────────────────────────
    ("Entrepreneur Mindset & Motivation",   False),
    ("Work From Home Tips",                 False),
    ("Productivity & Time Management",      False),
    ("Business Growth & Scaling",           False),
]

# ---------------------------------------------------------------------------

async def load_cookies(context: BrowserContext) -> bool:
    if not COOKIES_FILE.exists():
        print(f"[ERROR] cookies.json not found at {COOKIES_FILE}")
        print("  Export your Pinterest cookies using a browser extension and save as cookies.json.")
        return False

    with open(COOKIES_FILE) as f:
        raw = json.load(f)

    # Normalize cookie format (EditThisCookie vs Cookie-Editor vs Playwright)
    cookies = []
    for c in raw:
        cookie = {
            "name":     c.get("name", c.get("Name", "")),
            "value":    c.get("value", c.get("Value", "")),
            "domain":   c.get("domain", c.get("Domain", ".pinterest.com")),
            "path":     c.get("path", c.get("Path", "/")),
            "secure":   c.get("secure", c.get("Secure", True)),
            "httpOnly": c.get("httpOnly", c.get("HttpOnly", False)),
        }
        if "expirationDate" in c:
            cookie["expires"] = int(c["expirationDate"])
        elif "expiry" in c:
            cookie["expires"] = int(c["expiry"])
        if cookie["name"]:
            cookies.append(cookie)

    await context.add_cookies(cookies)
    print(f"[+] Loaded {len(cookies)} cookies from {COOKIES_FILE.name}")
    return True


async def get_existing_boards(page: Page) -> set[str]:
    """Navigate to the profile boards page and return normalized board names."""
    await page.goto("https://www.pinterest.com/me/", wait_until="networkidle", timeout=30_000)
    await page.wait_for_timeout(2000)

    # Check if we're actually logged in
    if "login" in page.url or "signup" in page.url:
        raise RuntimeError("Session expired or cookies invalid — please re-export cookies.json from Pinterest.")

    # Scroll to load all boards
    for _ in range(6):
        await page.keyboard.press("End")
        await page.wait_for_timeout(800)

    # Grab all board title text
    board_els = await page.query_selector_all('[data-test-id="board-card-title"], [data-test-id="boardName"], h3')
    names = set()
    for el in board_els:
        text = (await el.inner_text()).strip()
        if text:
            names.add(text.lower())

    print(f"[+] Found {len(names)} existing boards on your profile.")
    return names


async def create_board(page: Page, name: str, secret: bool) -> bool:
    """Open the Create Board dialog and submit."""
    try:
        # Click the + / Create button
        await page.goto("https://www.pinterest.com/me/", wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(1000)

        # Pinterest "Create board" can be triggered via the board create URL
        await page.goto("https://www.pinterest.com/board/create/", wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(1500)

        # Fill in board name
        name_input = await page.wait_for_selector(
            'input[name="boardName"], input[placeholder*="Name"], input[id*="name"]',
            timeout=8000
        )
        await name_input.click()
        await name_input.fill(name)
        await page.wait_for_timeout(400)

        # Toggle secret if needed
        if secret:
            secret_toggle = page.locator(
                'input[name="secret"], input[type="checkbox"][id*="secret"], '
                'div[data-test-id*="secret"] input'
            ).first
            if await secret_toggle.count() > 0:
                await secret_toggle.click()

        # Submit
        submit = page.locator(
            'button[type="submit"], button:has-text("Create"), button:has-text("Done")'
        ).first
        await submit.click()
        await page.wait_for_timeout(1800)

        print(f"  [+] Created: {name}")
        return True

    except Exception as e:
        print(f"  [!] Failed to create '{name}': {e}")
        return False


async def main():
    print("=" * 60)
    print("  SkillDailyPay — Pinterest Board Setup")
    print("=" * 60)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=80)
        session_file = Path(__file__).parent / "session_state.json"
        ctx_kwargs = dict(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        if session_file.exists():
            ctx_kwargs["storage_state"] = str(session_file)
        context = await browser.new_context(**ctx_kwargs)

        page = await context.new_page()

        # Try saved session first, otherwise let user log in manually
        session_file = Path(__file__).parent / "session_state.json"
        if session_file.exists():
            await context.storage_state()  # already loaded via new_context below
            print(f"[+] Loaded saved session from {session_file.name}")
        elif COOKIES_FILE.exists():
            ok = await load_cookies(context)
            if not ok:
                await browser.close()
                return
        else:
            print("[!] No saved session found — opening Pinterest for manual login.")
            print("    Log in to your Pinterest account in the browser window,")
            print("    then come back here and press ENTER to continue...")
            await page.goto("https://www.pinterest.com/login/", wait_until="domcontentloaded")
            input("\n>>> Press ENTER after you have logged in to Pinterest: ")
            print("[+] Continuing...")

        # Get existing boards
        try:
            existing = await get_existing_boards(page)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            await browser.close()
            return

        # Determine which boards are missing
        to_create = [
            (name, secret)
            for name, secret in BOARDS
            if name.lower() not in existing
        ]

        if not to_create:
            print("\n[✓] All boards already exist — nothing to create.")
            await browser.close()
            return

        print(f"\n[→] Creating {len(to_create)} missing boards...\n")

        created, failed = 0, 0
        for name, secret in to_create:
            success = await create_board(page, name, secret)
            if success:
                created += 1
            else:
                failed += 1
            # Small pause between board creations to avoid rate limiting
            await page.wait_for_timeout(1200)

        print("\n" + "=" * 60)
        print(f"  Done — {created} created, {failed} failed, {len(existing)} already existed.")
        print("=" * 60)

        await context.storage_state(path="session_state.json")
        print("\n[+] Session saved to session_state.json for future runs.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
