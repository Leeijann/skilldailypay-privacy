# Pinterest Board Setup — SkillDailyPay

Automated Playwright script that sets up all Pinterest boards for the SkillDailyPay multi-agency content system.

## Boards Created (38 total)

| Category | Boards |
|---|---|
| Social Media Strategy | Social Media Marketing Tips, Content Strategy & Planning, Social Media Content Calendar, Content Repurposing Ideas, Viral Content Ideas |
| Platform-Specific | Pinterest Marketing, Facebook Marketing Tips, Instagram Growth & Tips, YouTube Content Creation, TikTok Strategy & Growth, LinkedIn Marketing, Twitter X Marketing |
| Blog & Website | Blogging Tips & Growth, Blog Post Ideas, SEO & Website Traffic, WordPress & Website Design, Email Marketing Tips |
| Content Creation | Content Creation Tips, Graphic Design & Canva Templates, Video Content & Reels Ideas, Short Form Video Strategy, Storytelling & Copywriting, Brand Aesthetic & Visual Identity |
| Monetization | Make Money Online, Passive Income Ideas, Side Hustle Ideas, Digital Products & Income, Freelancing & Agency Life, Online Business & Entrepreneurship |
| Agency Operations | Digital Marketing Agency Tips, Client Management & Onboarding, Social Media Management Tools, AI Tools for Content Creators, Marketing Analytics & Reporting |
| Inspiration | Entrepreneur Mindset & Motivation, Work From Home Tips, Productivity & Time Management, Business Growth & Scaling |

## Setup

```bash
pip install playwright
playwright install chromium
```

## Export Your Pinterest Cookies

1. Open **pinterest.com** in Chrome and log in to your account
2. Install the [Cookie-Editor](https://cookie-editor.com/) extension
3. Click the extension → **Export** → **Export as JSON**
4. Save the file as `cookies.json` in this directory

## Run

```bash
python pinterest_boards_setup.py
```

The script will:
1. Load your saved Pinterest session from `cookies.json`
2. Scan your profile for existing boards
3. Create only the boards that are missing
4. Save an updated session to `session_state.json` for future runs

## Re-running

The script is safe to re-run at any time — it checks existing boards first and skips any that already exist.

## Adding More Boards

Edit the `BOARDS` list in `pinterest_boards_setup.py`:

```python
BOARDS = [
    ("Your Board Name", False),   # False = public, True = secret/private
    ...
]
```
