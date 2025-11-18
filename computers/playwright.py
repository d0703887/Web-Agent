# https://github.com/google-gemini/computer-use-preview/blob/main/computers/playwright/playwright.py

import time
from typing import Literal
from playwright.sync_api import sync_playwright, Page


PLAYWRIGHT_KEY_MAP = {
    "backspace": "Backspace",
    "tab": "Tab",
    "return": "Enter",  # Playwright uses 'Enter'
    "enter": "Enter",
    "shift": "Shift",
    "control": "ControlOrMeta",
    "alt": "Alt",
    "escape": "Escape",
    "space": "Space",  # Can also just be " "
    "pageup": "PageUp",
    "pagedown": "PageDown",
    "end": "End",
    "home": "Home",
    "left": "ArrowLeft",
    "up": "ArrowUp",
    "right": "ArrowRight",
    "down": "ArrowDown",
    "insert": "Insert",
    "delete": "Delete",
    "semicolon": ";",  # For actual character ';'
    "equals": "=",  # For actual character '='
    "multiply": "Multiply",  # NumpadMultiply
    "add": "Add",  # NumpadAdd
    "separator": "Separator",  # Numpad specific
    "subtract": "Subtract",  # NumpadSubtract, or just '-' for character
    "decimal": "Decimal",  # NumpadDecimal, or just '.' for character
    "divide": "Divide",  # NumpadDivide, or just '/' for character
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f10": "F10",
    "f11": "F11",
    "f12": "F12",
    "command": "Meta",  # 'Meta' is Command on macOS, Windows key on Windows
}



class EnvState:
    def __init__(self, screenshot: bytes, url: str):
        self.screenshot = screenshot
        self.url = url

class PlaywrightComputer:
    def __init__(
            self,
            screen_size: tuple[int, int],
            initial_url: str = "https://www.google.com",
            search_engine_url: str = "https://www.google.com",
            context_state_path: str = None
    ):
        self._screen_size = screen_size
        self._initial_url = initial_url
        self._search_engine_url = search_engine_url
        self._context_state_path = context_state_path
        self._initialize()


    def _initialize(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            args=[
                "--disable-extensions",
                "--disable-file-system",
                "--disable-plugins",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
            ],
            headless=False
        )

        self._context = self._browser.new_context(
            storage_state=self._context_state_path,
            viewport={
                "width": self._screen_size[0],
                "height": self._screen_size[1]
            }
        )

        self._page = self._context.new_page()
        self._page.goto(self._initial_url)
        self._context.on("page", self._handle_new_page)


    def _handle_new_page(self, new_page: Page):
        """The Computer Use model only supports a single tab at the moment.

        Some websites, however, try to open links in a new tab.
        For those situations, we intercept the page-opening behavior, and instead overwrite the current page.
        """
        new_url = new_page.url
        new_page.close()
        self._page.goto(new_url)

    def current_state(self):
        self._page.wait_for_load_state()
        # Even if Playwright reports the page as loaded, it may not be so.
        # Add a manual sleep to make sure the page has finished rendering.
        time.sleep(0.5)
        screenshot_bytes = self._page.screenshot(type="png", full_page=False)
        return EnvState(screenshot=screenshot_bytes, url=self._page.url)

    def open_browser(self):
        return self.current_state()

    def screen_size(self):
        viewport_size = self._page.viewport_size
        # If available, try to take the local playwright viewport size.
        if viewport_size:
            return viewport_size["width"], viewport_size["height"]
        # If unavailable, fall back to the original provided size.
        return self._screen_size

    def go_back(self):
        self._page.go_back()
        self._page.wait_for_load_state()
        return self.current_state()

    def go_forward(self):
        self._page.go_forward()
        self._page.wait_for_load_state()
        return self.current_state()

    def search(self):
        return self.navigate(self._search_engine_url)

    def navigate(self, url: str):
        normalized_url = url
        if not normalized_url.startswith(("http://", "https://")):
            normalized_url = "https://" + normalized_url
        self._page.goto(normalized_url)
        self._page.wait_for_load_state()
        return self.current_state()

    def click_at(self, x: int, y: int):
        self._page.mouse.click(x, y)
        self._page.wait_for_load_state()
        return self.current_state()


    def hover_at(self, x: int, y: int):
        self._page.mouse.move(x, y)
        self._page.wait_for_load_state()
        return self.current_state()

    def type_text_at(self, x: int, y: int, text: str, press_enter: bool = True, clear_before_typing: bool = True):
        self._page.mouse.click(x, y)
        self._page.wait_for_load_state()

        if clear_before_typing:
            self.key_combination(["Control", "A"])
            self.key_combination(["Delete"])

        self._page.keyboard.type(text)
        self._page.wait_for_load_state()

        if press_enter:
            self.key_combination(["Enter"])
        self._page.wait_for_load_state()
        return self.current_state()


    def key_combination(self, keys: list[str]):
        keys = [PLAYWRIGHT_KEY_MAP.get(k.lower(), k) for k in keys]

        for key in keys[:-1]:
            self._page.keyboard.down(key)

        self._page.keyboard.press(keys[-1])

        for key in reversed(keys[:-1]):
            self._page.keyboard.up(key)

        return self.current_state()

    def scroll_document(self, direction: Literal["up", "down", "left", "right"]):
        if direction == "down":
            return self.key_combination(["PageDown"])
        elif direction == "up":
            return self.key_combination(["PageUp"])
        elif direction in ("left", "right"):
            return self._horizontal_document_scroll(direction)
        else:
            raise ValueError("Unsupported direction: ", direction)

    def _horizontal_document_scroll(
            self, direction: Literal["left", "right"]
    ) -> EnvState:
        # Scroll by 50% of the viewport size.
        horizontal_scroll_amount = self.screen_size()[0] // 2
        if direction == "left":
            sign = "-"
        else:
            sign = ""
        scroll_argument = f"{sign}{horizontal_scroll_amount}"
        # Scroll using JS.
        self._page.evaluate(f"window.scrollBy({scroll_argument}, 0); ")
        return self.current_state()

    def scroll_at(
            self,
            x: int,
            y: int,
            direction: Literal["up", "down", "left", "right"],
            magnitude: int = 800,
    ):
        self._page.mouse.move(x, y)
        self._page.wait_for_load_state()

        dx = 0
        dy = 0
        if direction == "up":
            dy = -magnitude
        elif direction == "down":
            dy = magnitude
        elif direction == "left":
            dx = -magnitude
        elif direction == "right":
            dx = magnitude
        else:
            raise ValueError("Unsupported direction: ", direction)

        self._page.mouse.wheel(dx, dy)
        return self.current_state()








