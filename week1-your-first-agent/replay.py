"""Replay mode: answers every model call without a key or a network.

The scripted replies do what the real model did with the example inputs
(recorded from gpt-4o-mini). Tools still run for real, so file changes,
shell output and code results are real. Other inputs get a simple keyword
script; anything it can't handle says so and asks you to switch to Live.
"""
import json
import re

from llm import Reply, ToolCall

NO_RECORDING = "(Replay has no recorded answer for this input. Switch to Live (M) to ask the model.)"
FILENAME = re.compile(r"[\w./-]+\.(?:txt|md|json|csv|py|js)\b")


class Replay:
    def __init__(self, step):
        self.step = step
        self.ids = 0

    # ---- the four calls in llm.py --------------------------------------------

    def ask(self, prompt, system):
        if prompt.startswith("Summarize this conversation"):
            return SUMMARY
        if self.step.startswith("step1_") and any(w in prompt.lower() for w in ("time", "date", "file", "folder")):
            return ("I can't check the time or look at your files. I only have the text you send me "
                    "and what I learned in training, so I have no clock and no way to open a folder.")
        return NO_RECORDING

    def ask_json(self, prompt, system):
        answer = prompt.rsplit("The agent's final answer:", 1)[-1]
        if "Replay has no recorded answer" in answer:
            return {"score": 1, "reason": "There is no real answer to grade."}
        return {"score": 10, "reason": "Correct, and it uses the tool results it was given."}

    def search(self, query):
        if "weather" in query.lower():
            return ("[recorded search result] Tehran today: clear skies. About 13°C now, a high of "
                    "21°C around 2 pm and a low of 10°C tonight. Light wind from the north, no rain expected.")
        return NO_RECORDING

    def chat(self, messages, tools):
        names = [tool.__name__ for tool in tools]
        user, seen = last_turn(messages)
        script = SCRIPTS.get(self.step.split("_")[0], generic)
        result = script(self, user.lower(), seen, names)
        return result if isinstance(result, Reply) else Reply(result)

    def call(self, name, **args):
        self.ids += 1
        return Reply("", [ToolCall(f"call_{self.ids}", name, args)])


def last_turn(messages):
    """The last user message, and the tool calls (name, args, result) made since."""
    start = max(i for i, m in enumerate(messages) if m["role"] == "user")
    calls, seen = {}, []
    for message in messages[start + 1:]:
        for call in message.get("tool_calls") or []:
            calls[call["id"]] = (call["function"]["name"], json.loads(call["function"]["arguments"]))
        if message["role"] == "tool":
            name, args = calls.get(message["tool_call_id"], ("?", {}))
            seen.append((name, args, message["content"]))
    return messages[start]["content"], seen


def done(seen, name):
    return any(n == name for n, _, _ in seen)


# ---------------------------------------------------------------- scripts per step

def step2(r, user, seen, names):
    if any(w in user for w in ("time", "date", "day")):
        if not seen:
            return r.call("get_current_time")
        return f"It is {seen[-1][2]}."
    return known_answer(user)


def step3(r, user, seen, names):
    """One choice per prompt, like the recorded run (it looked before deleting)."""
    if "remove the old todo" in user:
        return r.call("list_files", directory=".")
    if "show me around" in user or "what's in this project" in user:
        return r.call("list_files", directory=".")
    file = FILENAME.search(user)
    if any(w in user for w in ("delete", "remove")):
        return r.call("delete_file", path=file.group() if file else "todo.txt")
    if any(w in user for w in ("create", "write", "save")):
        return r.call("write_file", path=file.group() if file else "new.txt", content="hi")
    if any(w in user for w in ("read", "contents", "inside", "open")):
        return r.call("read_file", path=file.group() if file else "README.md")
    if any(w in user for w in ("files", "folder", "directory", "list")):
        folder = re.search(r"in the (\w+) folder", user)
        return r.call("list_files", directory=folder.group(1) if folder else ".")
    if any(w in user for w in ("run ", "install", "git", "version", "command")):
        return r.call("run_command", command="python3 --version")
    return known_answer(user) if known_answer(user) != NO_RECORDING else "(answers without a tool)"


def step4(r, user, seen, names):
    if "todo" in user and "urgent" in user:
        if not done(seen, "list_files"):
            return r.call("list_files", directory=".")
        if not done(seen, "read_file"):
            return r.call("read_file", path="todo.txt")
        urgent = next((line for line in seen[-1][2].splitlines() if "URGENT" in line), "")
        return f"The most urgent task is: **{urgent.replace('- URGENT:', '').strip()}**."
    return generic(r, user, seen, names)


def step5(r, user, seen, names):
    if "api endpoint" in user:
        if not seen:
            return r.call("read_file", path="config.json")
        endpoint = json.loads(seen[0][2]).get("api_endpoint", "?")
        return f"The API endpoint is {endpoint}."
    if "port" in user and "3000" in user:
        if not done(seen, "read_file"):
            return r.call("read_file", path="config.json")
        if not done(seen, "write_file"):
            config = json.loads(seen[-1][2])
            config["port"] = 3000
            return r.call("write_file", path="config.json", content=json.dumps(config))
        return "Done: the port in config.json is now 3000 (it was 8080)."
    if "2 + 2" in user:
        return "2 + 2 = 4."
    return generic(r, user, seen, names)


def step6(r, user, seen, names):
    if "port" in user and "todo" in user:
        steps = [name for name, _, _ in seen]
        if not steps:
            return r.call("read_file", path="config.json")
        if steps == ["read_file"]:
            config = json.loads(seen[0][2])
            config["port"] = 3000
            return r.call("write_file", path="config.json", content=json.dumps(config, indent=2) + "\n")
        if steps == ["read_file", "write_file"]:
            return r.call("read_file", path="todo.txt")
        if steps == ["read_file", "write_file", "read_file"]:
            return r.call("write_file", path="todo.txt", content=seen[-1][2].rstrip("\n") + "\n- deploy on Friday\n")
        return "Done: the port in config.json is now 3000, and 'deploy on Friday' is at the end of todo.txt."
    return generic(r, user, seen, names)


def step7(r, user, seen, names):
    if "capital of france" in user:
        return "Paris."
    if any(w in user for w in ("weather", "news", "latest", "price", "today")):
        if not seen:
            return r.call("web_search", query=user.rstrip("?"))
        result = seen[-1][2]
        return result if result == NO_RECORDING else result.replace("[recorded search result] ", "")
    return generic(r, user, seen, names)


def step8(r, user, seen, names):
    if "database" in user or "port" in user:
        return "We chose **SQLite** (not PostgreSQL), and the app runs on **port 3000** (we changed it from 8080)."
    return generic(r, user, seen, names)


CSV_CODE = """import csv

total = 0
with open("data/sales.csv") as file:
    for row in csv.DictReader(file):
        total += int(row["amount"])
print(total)"""


def step9(r, user, seen, names):
    if "python" in user and "sales.csv" in user:
        if not seen:
            return r.call("run_command", command="python3 --version")
        if len(seen) == 1:
            return r.call("execute_code", code=CSV_CODE, language="python")
        return (f"Python here is **{seen[0][2].strip().replace('Python ', '')}**, and the amount column "
                f"in data/sales.csv adds up to **{seen[1][2].strip()}**.")
    if "lines" in user and "notes" in user:
        if not seen:
            return r.call("run_command", command="wc -l notes/*")
        return f"Lines per file:\n\n{seen[0][2]}"
    return generic(r, user, seen, names)


def step10(r, user, seen, names):
    if "delete todo.txt" in user:
        if not seen:
            return r.call("delete_file", path="todo.txt")
        if len(seen) == 1:
            return r.call("list_files", directory=".")
        files = ", ".join(line.split()[-1] for line in seen[1][2].splitlines())
        if "said no" in seen[0][2]:
            return f"OK, I did not delete todo.txt. The workspace has: {files}."
        return f"Deleted todo.txt. What's left: {files}."
    return generic(r, user, seen, names)


def generic(r, user, seen, names):
    """For inputs without a recording: look at what the words point to, then report."""
    file = FILENAME.search(user)
    if any(w in user for w in ("delete", "remove")) and file and "delete_file" in names and not seen:
        return r.call("delete_file", path=file.group())
    if file and "read_file" in names and not done(seen, "read_file"):
        return r.call("read_file", path=file.group())
    if seen and seen[-1][2].startswith("Error: file not found") and "list_files" in names and not done(seen, "list_files"):
        return r.call("list_files", directory=".")
    if any(w in user for w in ("files", "list", "folder", "left")) and "list_files" in names and not done(seen, "list_files"):
        return r.call("list_files", directory=".")
    if any(w in user for w in ("time", "date")) and "get_current_time" in names and not seen:
        return r.call("get_current_time")
    if not seen:
        return known_answer(user)
    name, args, result = seen[-1]
    missing = [a.get("path") for n, a, res in seen if res.startswith("Error: file not found")]
    if missing and name == "list_files":
        return f"There is no {missing[0]} in the workspace. These are the files there:\n\n{result}"
    if result.startswith("Error"):
        reads = [res for n, _, res in seen if n == "read_file"]
        if reads and "outside the workspace" in reads[0]:
            return f"I can't do that: {reads[0][7:]}. I can only use files inside the workspace."
        return f"That didn't work: {result[7:]}" + (f"\nThe workspace has:\n{result}" if name == "list_files" else "")
    return f"Here is what I found ({name}):\n\n{result}"


def known_answer(user):
    if "capital of france" in user:
        return "Paris."
    if "python used for" in user:
        return "Python is used for web development, data analysis, automation, AI and scripting."
    if "2 + 2" in user:
        return "4."
    return NO_RECORDING


SCRIPTS = {"step2": step2, "step3": step3, "step4": step4, "step5": step5, "step6": step6,
           "step7": step7, "step8": step8, "step9": step9, "step10": step10}

SUMMARY = """Goal: build Pocket Notes, a simple terminal notes app (title, body, tags, date) for a Python beginner.
Decisions:
- Name: Pocket Notes.
- Storage: SQLite, not PostgreSQL. All database code in storage.py.
- Port: 3000 instead of 8080, kept only in config.json.
- Tags: one comma-separated text column for v1, behind find_by_tag(tag).
Open tasks before Friday (v1.0): Sara fixes the empty-password login crash (+ a test), change the port to 3000, write the README, test every command on a fresh copy.
Later (v1.1): markdown export, dark theme, proper tag tables. Next: the README or the port change."""
