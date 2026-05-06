"""
SkillDailyPay — Pinterest Board Setup
Silix LLC / skilldailypay.com

Opens a browser for you to log in to Pinterest, then automatically
creates all missing boards for the SkillDailyPay multi-agency content system.

Usage:
    pip install playwright
    python -m playwright install chromium
    python pinterest_boards_setup.py
"""

import asyncio
import shutil
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

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


def is_login_page(url: str) -> bool:
    return "/login" in url or "/signup" in url or "accounts/login" in url


async def ensure_logged_in(page: Page):
    """Go to Pinterest and wait until the user is confirmed logged in on /me/."""
    print("[*] Checking login status...")

    await page.goto("https://www.pinterest.com/me/boards/", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    if not is_login_page(page.url):
        print("[+] Already logged in.\n")
        return

    # Need to log in
    print("[!] Not logged in — opening Pinterest login page.")
    print("    Please log in to your Pinterest account in the browser.")
    print("    The script will continue automatically once you are logged in...\n")

    await page.goto("https://www.pinterest.com/login/", wait_until="domcontentloaded", timeout=20000)

    # Poll until we land on a non-login page (up to 3 minutes)
    for _ in range(180):
        await page.wait_for_timeout(1000)
        if not is_login_page(page.url) and "pinterest.com" in page.url:
            await page.wait_for_timeout(2000)
            print("[+] Login detected — continuing.\n")
            return

    raise RuntimeError("Timed out waiting for Pinterest login (3 min). Please try again.")


async def get_existing_boards(page: Page) -> set:
    await page.goto("https://www.pinterest.com/me/boards/", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(4000)

    # Scroll to load all boards
    for _ in range(8):
        await page.keyboard.press("End")
        await page.wait_for_timeout(600)

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


async def debug_page_elements(page: Page):
    """Print all buttons/interactive elements on the current page for debugging."""
    elements = await page.evaluate("""
        () => {
            const els = document.querySelectorAll(
                'button, [role="button"], a, input, [data-test-id]'
            );
            return [...els].slice(0, 40).map(el => ({
                tag:    el.tagName,
                text:   el.textContent.trim().slice(0, 60),
                aria:   el.getAttribute('aria-label'),
                testId: el.getAttribute('data-test-id'),
                href:   el.getAttribute('href'),
                type:   el.getAttribute('type'),
            }));
        }
    """)
    print("\n  [DEBUG] Elements found on page:")
    for el in elements:
        print(f"    tag={el['tag']} testId={el['testId']!r} aria={el['aria']!r} text={el['text']!r}")
    await page.screenshot(path="debug_screenshot.png")
    print("  [DEBUG] Screenshot saved to debug_screenshot.png\n")


async def create_board(page: Page, name: str) -> bool:
    try:
        await page.goto("https://www.pinterest.com/me/boards/", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        # Try to click the create board button via JavaScript (handles dynamic selectors)
        clicked = await page.evaluate("""
            () => {
                const candidates = [
                    ...document.querySelectorAll('button, [role="button"], a, div, svg')
                ];
                for (const el of candidates) {
                    const aria  = (el.getAttribute('aria-label') || '').toLowerCase();
                    const testId = (el.getAttribute('data-test-id') || '').toLowerCase();
                    const text  = (el.textContent || '').trim().toLowerCase();
                    if (
                        aria.includes('create board') || aria.includes('add board') ||
                        testId.includes('create-board') || testId.includes('board-create') ||
                        text === 'create board' || text === '+'
                    ) {
                        el.click();
                        return aria || testId || text;
                    }
                }
                return null;
            }
        """)

        if not clicked:
            print(f"  [!] Could not find Create Board button for '{name}'")
            await debug_page_elements(page)
            return False

        print(f"  [*] Clicked create button ({clicked})")
        await page.wait_for_timeout(2000)

        # Fill in board name
        name_input = await page.wait_for_selector(
            'input[name="boardName"], input[id="boardEditName"], '
            'input[placeholder*="oard"], input[placeholder*="Name"], '
            'input[type="text"]',
            timeout=8000
        )
        await name_input.click()
        await name_input.fill(name)
        await page.wait_for_timeout(500)

        # Submit
        submit = page.locator(
            'button[type="submit"], button:has-text("Create"), button:has-text("Done")'
        ).first
        await submit.click(timeout=6000)
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

    # Clear stale session if it exists so we always get a clean login check
    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
    SESSION_DIR.mkdir()

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            slow_mo=60,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = await context.new_page()

        try:
            await ensure_logged_in(page)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            await context.close()
            return

        existing = await get_existing_boards(page)
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
            await page.wait_for_timeout(800)

        print("\n" + "=" * 60)
        print(f"  Done — {created} created, {failed} failed, {len(existing)} already existed.")
        print("=" * 60)

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
