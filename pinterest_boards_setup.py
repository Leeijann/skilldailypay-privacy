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

    # Use Pinterest's internal API to get boards reliably
    boards_data = await page.evaluate("""
        async () => {
            try {
                const resp = await fetch('/resource/BoardResource/get/?source_url=%2Fme%2Fboards%2F&data=%7B%22options%22%3A%7B%22field_set_key%22%3A%22detailed%22%7D%7D', {
                    credentials: 'include'
                });
                const json = await resp.json();
                return (json?.resource_response?.data || []).map(b => b.name);
            } catch(e) {
                return [];
            }
        }
    """)

    if boards_data:
        names = {n.lower() for n in boards_data}
        print(f"[+] Found {len(names)} existing board(s) via API.")
        return names

    # Fallback: scrape from DOM
    board_els = await page.query_selector_all(
        '[data-test-id="board-card-title"], [data-test-id="boardName"], h3'
    )
    names = set()
    for el in board_els:
        text = (await el.inner_text()).strip()
        if text:
            names.add(text.lower())
    print(f"[+] Found {len(names)} existing board(s) from DOM.")
    return names


async def create_board(page: Page, name: str) -> bool:
    """Create a board using Pinterest's internal fetch API from inside the browser."""
    try:
        result = await page.evaluate("""
            async (boardName) => {
                // Get CSRF token from cookies
                const csrfToken = document.cookie
                    .split(';')
                    .map(c => c.trim())
                    .find(c => c.startsWith('csrftoken='))
                    ?.split('=')[1] || '';

                const payload = new URLSearchParams({
                    source_url: '/me/boards/',
                    data: JSON.stringify({
                        options: {
                            name: boardName,
                            privacy: 'public',
                            category: 'other'
                        },
                        context: {}
                    }),
                    _: Date.now().toString()
                });

                const resp = await fetch('/resource/BoardResource/create/', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-APP-VERSION': window.__app_version__ || '',
                        'Referer': 'https://www.pinterest.com/me/boards/'
                    },
                    body: payload.toString()
                });

                const json = await resp.json();
                if (json?.resource_response?.data?.id) {
                    return { ok: true, id: json.resource_response.data.id };
                }
                return { ok: false, error: JSON.stringify(json?.resource_response?.error || json) };
            }
        """, name)

        if result and result.get('ok'):
            print(f"  [+] Created: {name} (id={result.get('id')})")
            await page.wait_for_timeout(500)
            return True
        else:
            print(f"  [!] Failed '{name}': {result.get('error', 'unknown')}")
            return False

    except Exception as e:
        print(f"  [!] Exception for '{name}': {e}")
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
