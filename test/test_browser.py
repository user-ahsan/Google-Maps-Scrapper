import sys

# Ensure UTF-8 output encoding for emojis on Windows consoles
try:
    if sys.stdout:
        reconfig_stdout = getattr(sys.stdout, 'reconfigure', None)
        if callable(reconfig_stdout):
            reconfig_stdout(encoding='utf-8', errors='replace')
    if sys.stderr:
        reconfig_stderr = getattr(sys.stderr, 'reconfigure', None)
        if callable(reconfig_stderr):
            reconfig_stderr(encoding='utf-8', errors='replace')
except Exception:
    pass

from playwright.sync_api import sync_playwright


def test_browser():
    print("="*60)
    print("   BROWSER TEST (HEADED)   ")
    print("="*60)

    with sync_playwright() as p:
        print("1. Launching Browser (Headed)...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("2. Navigate to Google...")
        page.goto("https://www.google.com")
        page.wait_for_timeout(2000)
        print(f"   Page Title: {page.title()}")

        print("3. Navigate to Example.com...")
        page.goto("https://example.com")
        page.wait_for_timeout(1000)
        print(f"   Page Title: {page.title()}")

        print("4. Closing Browser...")
        browser.close()
        print("✅ Browser Test Passed!")

if __name__ == "__main__":
    test_browser()
