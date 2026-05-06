"""
SkillDailyPay — Pinterest Board Setup
Silix LLC / skilldailypay.com

Opens a browser window for you to log in to Pinterest, then automatically
creates all missing boards for the SkillDailyPay multi-agency content system.

Usage:
    pip install playwright
    python -m playwright install chromium
    python pinterest_boards_setup.py
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page

SESSION_DIR = Path(__file__).parent / "pinterest_session"

BOARDS = [
    # Social Media Strategy
    "Social Media Marketing Tips",
    "Content Strategy & Planning",
    "Social Media Content Calendar",
    "Content Repurposing Ideas",
    "Viral Content Ideas",

    # Platform-Specific
    "Pinterest Marketing",
    "Facebook Marketing Tips",
    "Instagram Growth & Tips",
    "YouTube Content Creation",
    "TikTok Strategy & Growth",
    "LinkedIn Marketing",
    "Twitter X Marketing",

    # Blog & Website
    "Blogging Tips & Growth",
    "Blog Post Ideas",
    "SEO & Website Traffic",
    "WordPress & Website Design",
    "Email Marketing Tips",

    # Content Creation
    "Content Creation Tips",
    "Graphic Design & Canva Templates",
    "Video Content & Reels Ideas",
    "Short Form Video Strategy",
    "Storytelling & Copywriting",
    "Brand Aesthetic & Visual Identity",

    # Monetization
    "Make Money Online",
    "Passive Income Ideas",
    "Side Hustle Ideas",
    "Digital Products & Income",
    "Freelancing & Agency Life",
    "Online Business & Entrepreneurship",

    # Agency Operations
    "Digital Marketing Agency Tips",
    "Client Management & Onboarding",
    "Social Media Management Tools",
    "AI Tools for Content Creators",
    "Marketing Analytics & Reporting",

    # Inspiration & Lifestyle
    "Entrepreneur Mindset & Motivation",
    "Work From Home Tips",
    "Productivity & Time Management",
    "Business Growth & Scaling",
]


async def wait_for_login(page: Page):
    """Navigate to Pinterest and wait until the user is logged in."""
    await page.goto("https://www.pinterest.com/login/", wait_until="domcontentloaded")
    print("[!] Browser opened — please log in to Pinterest.")
    print("    Waiting automatically, no ENTER needed...\n")

    # Wait until we land on a page that is NOT the login/signup page
    for _ in range(120):  # wait up to 2 minutes
        await page.wait_for_timeout(1000)
        url = page.url
        if "pinterest.com" in url and "/login" not in url and "/signup" not in url:
            print("[+] Login detected — continuing.\n")
            return
    raise RuntimeError("Timed out waiting for Pinterest login (2 min limit).")


async def get_existing_boards(page: Page) -> set:
    await page.goto("https://www.pinterest.com/me/", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)

    if "/login" in page.url or "/signup" in page.url:
        raise RuntimeError("Not logged in — session may have expired.")

    # Scroll to load all boards
    for _ in range(8):
        await page.keyboard.press("End")
        await page.wait_for_timeout(700)

    board_els = await page.query_selector_all(
        '[data-test-id="board-card-title"], [data-test-id="boardName"], '
        'div[class*="boardName"], h3'
    )
    names = set()
    for el in board_els:
        text = (await el.inner_text()).strip()
        if text:
            names.add(text.lower())

    print(f"[+] Found {len(names)} existing board(s) on your profile.")
    return names


async def create_board(page: Page, name: str) -> bool:
    try:
        await page.goto("https://www.pinterest.com/board/create/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1500)

        name_input = await page.wait_for_selector(
            'input[name="boardName"], input[placeholder*="Name"], input[id*="name"], input[type="text"]',
            timeout=8000
        )
        await name_input.click()
        await name_input.fill(name)
        await page.wait_for_timeout(500)

        submit = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Done")').first
        await submit.click()
        await page.wait_for_timeout(2000)

        print(f"  [+] Created: {name}")
        return True
    except Exception as e:
        print(f"  [!] Failed '{name}': {e}")
        return False


async def main():
    print("=" * 60)
    print("  SkillDailyPay — Pinterest Board Setup")
    print("=" * 60 + "\n")

    SESSION_DIR.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        # Persistent context saves the login session automatically
        context = await pw.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            slow_mo=80,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        # Check if already logged in from a previous run
        await page.goto("https://www.pinterest.com/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1500)

        if "/login" in page.url or "/signup" in page.url:
            await wait_for_login(page)
        else:
            print("[+] Already logged in from saved session.\n")

        # Scan existing boards
        try:
            existing = await get_existing_boards(page)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            await context.close()
            return

        to_create = [n for n in BOARDS if n.lower() not in existing]

        if not to_create:
            print("\n[✓] All boards already exist — nothing to do.")
            await context.close()
            return

        print(f"[→] Creating {len(to_create)} missing board(s)...\n")

        created, failed = 0, 0
        for name in to_create:
            ok = await create_board(page, name)
            if ok:
                created += 1
            else:
                failed += 1
            await page.wait_for_timeout(1000)

        print("\n" + "=" * 60)
        print(f"  Done — {created} created, {failed} failed, {len(existing)} already existed.")
        print("=" * 60)

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
