# Gemini Computer Use Web Agent with Planner

This project implements an autonomous web agent capable of **navigating** and **interacting** with live web applications like **Linear** and **Notion**. 

Built using the [Gemini 2.5 Computer Use](https://ai.google.dev/gemini-api/docs/computer-use) model, this agent distinguishes itself by utilizing a **two-stage architecture**: a high-level "Planner" agent translates user user intentions into structured steps, which are then executed by the "Computer Use" agent via Playwright.


> **Note:** The core computer use logic is based on the [Google Gemini Computer Use Reference Implementation](https://github.com/google-gemini/computer-use-preview). This project extends that reference by adding a **Planner module**. This addition is critical because demonstrating features on live web applications (like Linear or Notion) requires complex task handling, context setup, and strict adherence to multi-step workflows that a single-shot instruction often misses.


## Two-Stage Architecture
* **Planner (Gemini 2.5 Flash):** Analyzes the user's natural language query and generates a concise, high-level plan (e.g., setting up demo data, performing a specific filter, cleaning up).
* **Executor (Gemini 2.5 Computer Use):** Receives the plan and autonomously controls the browser to achieve the goal.


## Prerequisites

* Python 3.10+
* A Google Cloud Project with the Gemini API enabled.
* Access to `gemini-2.5-computer-use-preview-10-2025` and `gemini-2.5-flash`.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name
    ```

2.  **Install dependencies:**
    ```bash
    pip install google-genai playwright rich termcolor pillow
    ```

3.  **Install Playwright browsers:**
    ```bash
    playwright install chromium
    ```

## Configuration

### 1. API Key
Set your Gemini API key as an environment variable:
```bash
export GEMINI_API_KEY="your_api_key_here"
```
# Usage
You can now run the agent on **any** website using command-line arguments.

### Arguments
* `--initial_url`: (Recommened) The website to start on. Defaults to Google. This prevent model from failing to login.
* `--auth_state`: (Optional) Path to a JSON file containing cookies/local storage.
* `--verbose`: (Recommened) Prints the Planner's output and Web Agent's reasoning chain.


### Example 1: Notion (With Auth)

```bash
python webagent.py \
  --initial_url "https://www.notion.so" \
  --auth_state "auth_state_notion.json" \
  --verbose
```

### Example 2: Linear (With Auth)

```bash
python webagent.py \
  --initial_url "https://linear.app/your-team-id" \
  --auth_state "auth_state_linear.json" \
  --verbose
```
