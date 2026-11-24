# CodeAct: the agent acts by writing code instead of calling fixed tools.
# We run its code and show it the output, in a loop.
#
# Who decides what happens next?  The model, and it can do anything code can,
# so in production this must run inside a sandbox.
import re
import subprocess
import sys

from llm import chat

MAX_STEPS = 5

SYSTEM = """Solve the task by writing Python code.
To run code, reply with one ```python code block that prints what you need.
When you know the final answer, reply with: ANSWER: <your answer>"""


def run_python(code):
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, timeout=10)
    return (result.stdout + result.stderr).strip()


def extract_code(text):
    match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    return match.group(1) if match else ""


def run(task):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    for step in range(MAX_STEPS):
        reply = chat(messages).text
        messages.append({"role": "assistant", "content": reply})

        if "ANSWER:" in reply:
            return reply.split("ANSWER:")[1].strip()

        output = run_python(extract_code(reply))
        messages.append({"role": "user", "content": f"Output:\n{output}"})

    return "Stopped: too many steps."


if __name__ == "__main__":
    print(run("How many prime numbers are there below 10,000, and what is their sum?"))
