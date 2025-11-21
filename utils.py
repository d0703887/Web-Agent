import argparse
from playwright.sync_api import sync_playwright


def save_auth(target_url: str, output_path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"Navigating to {target_url}...")
        page.goto(target_url)

        print("-" * 50)
        print(f"ACTION REQUIRED: Please log in the browser window.")
        print("-" * 50)

        save = ""
        while save.lower() not in ("yes", "y"):
            save = input(f"Login complete? Type 'yes' to save state to '{output_path}': ")

        context.storage_state(path=output_path)
        print(f"SUCCESS: Authentication state saved to {output_path}")
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate authentication state for the Web Agent.")
    parser.add_argument("--target_url", type=str, required=True, help="The application's login page.")
    parser.add_argument("--output_path", type=str, required=True, help="The output file path.")
    args = parser.parse_args()

    save_auth(args.target_url, args.output_path)