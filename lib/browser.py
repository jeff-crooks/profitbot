import random
import time
from playwright.sync_api import sync_playwright, Page


def human_delay(min_s: float = 2.0, max_s: float = 6.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def post_delay(min_s: float = 30.0, max_s: float = 90.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def human_type(page: Page, selector: str, text: str) -> None:
    page.click(selector)
    human_delay(0.3, 0.8)
    for char in text:
        page.keyboard.type(char, delay=random.uniform(50, 150))


def is_captcha_present(page: Page) -> bool:
    return bool(
        page.query_selector("iframe[src*='recaptcha']")
        or page.query_selector(".h-captcha")
        or page.query_selector("[data-sitekey]")
        or page.query_selector("iframe[title*='challenge']")
    )


class BrowserSession:
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, headless: bool = True):
        self._pw = None
        self._browser = None
        self.page = None

    def __enter__(self) -> "BrowserSession":
        self._pw = sync_playwright().__enter__()
        self._browser = self._pw.chromium.launch(headless=True)
        context = self._browser.new_context(user_agent=self.USER_AGENT)
        self.page = context.new_page()
        return self

    def __exit__(self, *args) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.__exit__(*args)

    def navigate(self, url: str) -> None:
        self.page.goto(url, wait_until="networkidle", timeout=30000)
        human_delay()

    def check_and_handle_captcha(self, script_name: str) -> None:
        from lib.manual import log_item, ManualInterventionRequired
        if is_captcha_present(self.page):
            log_item(
                "CAPTCHA detected",
                f"Complete the CAPTCHA at {self.page.url} in a browser, then re-run the script.",
                script_name,
            )
            raise ManualInterventionRequired("CAPTCHA detected")
