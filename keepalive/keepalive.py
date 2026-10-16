"""Keep a Streamlit Community Cloud app awake.

Streamlit suspends apps after ~12h without traffic. A suspended app serves a
"sleeping" interstitial with a wake-up button instead of the app itself.

This script visits the app in headless Chrome on a schedule: if the app is
asleep it clicks the wake-up button, then keeps polling until the app actually
renders (clicking alone proves nothing — the container still has to boot).
Exit 0 means the app is up and serving; anything else exits 1 and leaves a
screenshot for diagnosis.
"""

import logging
import os
import sys
import time
from enum import Enum

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

APP_URL = os.environ.get("STREAMLIT_APP_URL", "").strip() or (
    "https://moneyprinterturbo-cloud-cznebru7byeehbqwfx7ugr.streamlit.app/"
)
LOAD_TIMEOUT = int(os.environ.get("LOAD_TIMEOUT", "60"))
WAKE_TIMEOUT = int(os.environ.get("WAKE_TIMEOUT", "600"))
POLL_INTERVAL = 5
SCREENSHOT_PATH = os.environ.get("SCREENSHOT_PATH", "screenshot.png")

# Streamlit Cloud's own interstitial markup (top-level document).
WAKE_BUTTON = (By.CSS_SELECTOR, '[data-testid="wakeup-button-viewer"]')
# The running app renders inside a nested iframe — checking only the top-level
# document sees an empty page while the container boots.
APP_FRAME = (By.CSS_SELECTOR, 'iframe[title="streamlitApp"]')
APP_ROOT = (By.CSS_SELECTOR, '[data-testid="stApp"]')

log = logging.getLogger("keepalive")


class State(Enum):
    RUNNING = "running"
    ASLEEP = "asleep"
    WAKING = "waking"
    ERROR = "error"
    UNKNOWN = "unknown"


def app_is_rendered(driver) -> bool:
    frames = driver.find_elements(*APP_FRAME)
    if not frames:
        return False
    try:
        driver.switch_to.frame(frames[0])
        return bool(driver.find_elements(*APP_ROOT))
    except WebDriverException:
        return False
    finally:
        driver.switch_to.default_content()


def detect_state(driver) -> State:
    """Classify the page. Biased to positive identification: RUNNING requires
    finding the mounted app, so an unrecognised page is UNKNOWN, never
    optimistically 'healthy'."""
    driver.switch_to.default_content()
    if driver.find_elements(*WAKE_BUTTON):
        return State.ASLEEP
    try:
        text = " ".join(driver.find_element(By.TAG_NAME, "body").text.lower().split())
    except WebDriverException:
        return State.UNKNOWN
    if "error running app" in text or text.startswith("oh no."):
        return State.ERROR
    if "you do not have access to this app" in text:
        return State.ERROR
    if "waking up" in text or "taking longer than normal" in text:
        return State.WAKING
    if "gone to sleep" in text:
        return State.ASLEEP
    if app_is_rendered(driver):
        return State.RUNNING
    if not text:
        # Top-level body empties out while the container boots.
        return State.WAKING
    return State.UNKNOWN


def build_driver():
    options = Options()
    for arg in (
        "--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
    ):
        options.add_argument(arg)
    return webdriver.Chrome(options=options)


def settle(driver, timeout: int) -> State:
    """Poll until the page reports something recognisable."""
    deadline = time.monotonic() + timeout
    state = State.UNKNOWN
    while time.monotonic() < deadline:
        state = detect_state(driver)
        if state is not State.UNKNOWN:
            return state
        time.sleep(POLL_INTERVAL)
    return state


def await_boot(driver, timeout: int) -> State:
    """Watch a booting app until it serves. Only RUNNING ends the wait early:
    an ERROR mid-boot is not final (Streamlit restarts crashed startups)."""
    deadline = time.monotonic() + timeout
    start = time.monotonic()
    last = None
    while time.monotonic() < deadline:
        state = detect_state(driver)
        if state is not last:
            log.info("[%3.0fs] %s", time.monotonic() - start, state.value)
            last = state
        if state is State.RUNNING:
            return state
        time.sleep(POLL_INTERVAL)
    log.warning("gave up after %ds", timeout)
    return last or State.UNKNOWN


def save_screenshot(driver) -> None:
    try:
        driver.save_screenshot(SCREENSHOT_PATH)
        log.info("screenshot saved to %s", SCREENSHOT_PATH)
    except WebDriverException as exc:
        log.warning("could not save screenshot: %s", exc)


def run() -> int:
    if not APP_URL.startswith(("http://", "https://")):
        log.error("STREAMLIT_APP_URL is not a valid http(s) URL: %r", APP_URL)
        return 1
    log.info("target: %s", APP_URL)
    driver = build_driver()
    try:
        driver.get(APP_URL)
        state = settle(driver, LOAD_TIMEOUT)
        log.info("initial state: %s", state.value)

        if state is State.RUNNING:
            log.info("app is already awake, nothing to do")
            return 0
        if state is State.WAKING:
            log.info("app is already booting, waiting for it to finish")
            state = await_boot(driver, WAKE_TIMEOUT)
        elif state is State.ASLEEP:
            buttons = driver.find_elements(*WAKE_BUTTON)
            if not buttons:
                log.error("app reports asleep but the wake button is missing")
                save_screenshot(driver)
                return 1
            buttons[0].click()
            log.info("clicked the wake button, waiting for the container to boot")
            state = await_boot(driver, WAKE_TIMEOUT)
        else:
            log.error("unexpected state on load: %s", state.value)
            save_screenshot(driver)
            return 1

        if state is State.RUNNING:
            log.info("app is up and serving")
            return 0
        log.error("app did not come up (final state: %s)", state.value)
        save_screenshot(driver)
        return 1
    except WebDriverException as exc:
        log.error("browser error: %s", exc)
        return 1
    finally:
        driver.quit()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )
    sys.exit(run())


if __name__ == "__main__":
    main()
