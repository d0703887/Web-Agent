import time
from playwright.sync_api import sync_playwright

def save_auth():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="auth_state_notion.json")
        page = context.new_page()

        save = ""
        while save.lower() not in ("yes", "y"):
            save = input("Input yes to save authentication info: ")

        context.storage_state(path="auth_state.json")
        browser.close()

if __name__ == '__main__':
    save_auth()