# Web Agent

This project demonstrates a web agent powered by Gemini that can interact with web applications like Linear and Notion.

## Demos
*   **Linear 1:** "Create a project in Linear"
*   **Linear 2:** "Create an issue in Linear and set its priority to 'Urgent'"
*   **Notion 1:** "Create a new page in Notion"
*   **Notion 2:** "Filter a database in Notion"

## Setup

Before running the agent, you need to complete the following setup steps:

### 1. Gemini API Key

You need to have a Gemini API key. Set it as an environment variable:

```bash
export GEMINI_API_KEY="YOUR_API_KEY"
```

### 2. Authentication State

To allow the agent to access your Linear and Notion accounts, you need to provide it with a logged-in session state. The agent uses Playwright to control the browser, and you can save your authentication state after logging in manually.

The project expects the following files for the authentication state:
- `auth_state_linear.json` for Linear
- `auth_state_notion.json` for Notion

You will need to generate these files. One way to do this is to use the save_auth() function in utils.py.