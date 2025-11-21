import os
from typing import Any
import argparse
import sys
from datetime import datetime
import termcolor
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from PIL import Image
import io

from google import genai
from google.genai import types

from computers.playwright import PlaywrightComputer

PLAYWRIGHT_SCREEN_SIZE = (1440, 900)
MAX_RECENT_TURN_WITH_SCREENSHOTS = 3

class WebAgent:
    def __init__(
            self,
            verbose: bool = True,
            console: Console = None,
            context_state_path: str = None,
            initial_url: str = None
    ):
        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        with open("prompts/planner_prompt.md", "r") as fp:
            planner_prompt = fp.read()
        self._gemini_flash_use_generation_content_config = types.GenerateContentConfig(system_instruction=planner_prompt)
        self._computer_use_generation_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            tools=[
                types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER,
                        excluded_predefined_functions=[
                            "wait_5_seconds",
                            "drag_and_drop"
                        ]
                    )
                )
            ]
        )
        # Directly jump to App page at the beginning
        self.playwright = PlaywrightComputer(PLAYWRIGHT_SCREEN_SIZE, context_state_path=context_state_path, initial_url=initial_url)
        self._contents = []
        self._verbose = verbose
        if verbose and console is None:
            raise ValueError("Console must be provided in verbose mode.")
        self._console = console

        folder_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._folder_path = os.path.join("screenshots", folder_name)
        if not os.path.exists(self._folder_path):
            os.makedirs(self._folder_path)
        self._iteration = 0

    def denormalize_x(self, x: int):
        return int(x / 1000 * self.playwright.screen_size()[0])

    def denormalize_y(self, y: int):
        return int(y / 1000 * self.playwright.screen_size()[1])

    def handle_action(self, action: types.FunctionCall):
        fname = action.name
        args = action.args
        if fname == "open_web_browser":
            return self.playwright.open_browser()
        elif fname == "wait_5_seconds":
            pass
        elif fname == "drag_and_drop":
            pass
        elif fname == "go_back":
            return self.playwright.go_back()
        elif fname == "go_forward":
            return self.playwright.go_forward()
        elif fname == "search":
            return self.playwright.search()
        elif fname == "navigate":
            return self.playwright.navigate(args["url"])
        elif fname == "click_at":
            x = self.denormalize_x(args["x"])
            y = self.denormalize_y(args["y"])
            return self.playwright.click_at(x, y)
        elif fname == "hover_at":
            x = self.denormalize_x(args["x"])
            y = self.denormalize_y(args["y"])
            return self.playwright.hover_at(x, y)
        elif fname == "type_text_at":
            x = self.denormalize_x(args["x"])
            y = self.denormalize_y(args["y"])
            return self.playwright.type_text_at(
                x,
                y,
                args["text"],
                args.get("press_enter", True),
                args.get("clear_before_typing", True)
            )
        elif fname == "key_combination":
            return self.playwright.key_combination(args["keys"].split("+"))
        elif fname == "scroll_document":
            return self.playwright.scroll_document(args["direction"])
        elif fname == "scroll_at":
            x = self.denormalize_x(args["x"])
            y = self.denormalize_y(args["y"])
            magnitude = args.get("magnitude", 800)
            direction = args["direction"]

            if direction in ("up", "down"):
                magnitude = self.denormalize_y(magnitude)
            elif direction in ("left", "right"):
                magnitude = self.denormalize_x(magnitude)
            else:
                raise ValueError("Unknown direction: ", direction)
            return self.playwright.scroll_at(x, y, direction, magnitude)
        else:
            raise ValueError(f"Unsupported function call: {action}")


    def get_model_response(self):
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-computer-use-preview-10-2025",
                contents=self._contents,
                config=self._computer_use_generation_content_config
            )
            return response
        except Exception as e:
            print(e)

    # Retrieve reasoning part
    def get_text(self, candidate: types.Candidate):
        if not candidate.content or not candidate.content.parts:
            return None
        text = []
        for part in candidate.content.parts:
            if part.text:
                text.append(part.text)
        return " ".join(text) or None

    def extract_function_calls(self, candidate: types.Candidate) -> list[types.FunctionCall]:
        if not candidate.content or not candidate.content.parts:
            return []
        ret = []
        for part in candidate.content.parts:
            if part.function_call:
                ret.append(part.function_call)
        return ret

    # Direct human Intervention
    def _handle_safety_confirmation(self):
        termcolor.cprint(
            "Require safety confirmation, direct human intervention.",
            color="yellow",
            attrs=["bold"]
        )
        finish = ""
        while finish.lower() not in ("y", "n", "ye", "yes", "no"):
            finish = input("Human intervention finished? ('yes' to continue/'no' to exit the program): ")
        print()
        if finish.lower() in ("n", "no"):
            termcolor.cprint("Exiting program", color="red")
            sys.exit(0)

        return self.playwright.current_state()

    def run_one_iteration(self):
        try:
            response = self.get_model_response()
        except Exception as e:
            return "COMPLETE"

        if not response.candidates:
            print("Response has no candidates!")
            print(response)
            raise ValueError("Empty response")

        candidate = response.candidates[0]
        if candidate.content:
            self._contents.append(candidate.content)

        reasoning = self.get_text(candidate)
        function_calls = self.extract_function_calls(candidate)

        # retry the request
        if(
            not function_calls
            and not reasoning
            and candidate.finish_reason == types.FinishReason.MALFORMED_FUNCTION_CALL
        ):
            return "CONTINUE"

        if not function_calls:
            print(f"Agent Loop Complete: {reasoning}")
            return "COMPLETE"

        function_call_strs = []
        for function_call in function_calls:
            function_call_str = f"Name: {function_call.name}"
            if function_call.args:
                function_call_str += f"\nArgs:"
                for key, value in function_call.args.items():
                    function_call_str += f"\n{key}: {value}"
            function_call_strs.append(function_call_str)

        table = Table(expand=True)
        table.add_column("Gemini Computer User Reasoning", header_style="magenta", ratio=1)
        table.add_column("Function Call(s)", header_style="cyan", ratio=1)
        table.add_row(reasoning, "\n".join(function_call_strs))
        if self._verbose:
            self._console.print(table)
            print()

        # Executing function calls
        # Skipping safety check for now
        function_responses = []
        for idx, function_call in enumerate(function_calls):
            extra_fr_fields = {}
            if function_call.args and function_call.args.get("safety_decision"):
                fc_result = self._handle_safety_confirmation()
                extra_fr_fields["safety_acknowledgement"] = "true"
            else:
                fc_result = self.handle_action(function_call)

            function_responses.append(
                types.FunctionResponse(
                    name=function_call.name,
                    response={"url": fc_result.url, **extra_fr_fields},
                    parts=[
                        types.FunctionResponsePart(
                            inline_data=types.FunctionResponseBlob(
                                mime_type="image/png", data=fc_result.screenshot
                            )
                        )
                    ]
                )
            )
            screenshot = Image.open(io.BytesIO(fc_result.screenshot))
            screenshot.save(os.path.join(self._folder_path, f"{self._iteration}_{idx}.png"))


        self._contents.append(
            types.Content(
                role="user",
                parts=[types.Part(function_response=fr) for fr in function_responses]
            )
        )

        # only keep screenshots in the few most recent turns, remove the screenshot images from the old turns.
        turn_with_screenshots_found = 0
        for content in reversed(self._contents):
            if content.role == "user" and content.parts:
                turn_with_screenshots_found += 1
                # remove the screenshot image if the number of screenshots exceed the limit.
                if turn_with_screenshots_found > MAX_RECENT_TURN_WITH_SCREENSHOTS:
                    for part in content.parts:
                        if (
                                part.function_response
                                and part.function_response.parts
                                and part.function_response.name
                        ):
                            part.function_response.parts = None

        return "CONTINUE"

    def _generate_plan(self, user_query: str):
        response = self._client.models.generate_content(
            model="gemini-2.5-flash",
            config=self._gemini_flash_use_generation_content_config,
            contents=user_query
        )
        plan_query = f"User query: {user_query}\nPlan:\n{response.text}"
        if self._verbose:
            self._console.print(
                Panel(response.text, title="[bold magenta]Execution Plan[/bold magenta]", border_style="green"),
                justify="left"
            )
            print()
        return plan_query

    def start_agent_loop(self, plan_query: str, clear_content_history: bool = False):
        self._iteration = 0

        new_message = types.Content(
                    role="user",
                    parts=[types.Part(text=plan_query)]
                )
        if clear_content_history:
            self._contents = [new_message]
        else:
            self._contents.append(new_message)

        status = "CONTINUE"
        while status == "CONTINUE":
            status = self.run_one_iteration()
            self._iteration += 1

    def main(self):
        user_query = input("Please input the task: ")
        plan_query = self._generate_plan(user_query)
        self.start_agent_loop(plan_query)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--auth_state", type=str, required=False)
    parser.add_argument("--initial_url", type=str, required=False)
    args = parser.parse_args()

    agent = WebAgent(
        verbose=args.verbose,
        console=Console(),
        context_state_path=args.auth_state,
        initial_url=args.initial_url
    )
    agent.main()














