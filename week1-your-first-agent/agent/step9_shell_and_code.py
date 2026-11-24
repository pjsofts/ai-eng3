# Step 9 — Shell and code
# Give the agent the tools developers use: a shell, and a way to run code.
# Code is exact where the model is not: it adds up a column without mistakes.
#   run_command   one shell command (ls, wc, git, python --version ...)
#   execute_code  write a program to a file, run it, delete the file: 3 steps, 1 tool
# Warning: this runs on YOUR machine with YOUR permissions. Step 10 adds a gate.
from agent import run_agent
from tools import execute_code, list_files, read_file, run_command

TOOLS = [list_files, read_file, run_command, execute_code]

SYSTEM = """You are a helpful assistant with a shell and a code runner,
in a workspace folder.
For any calculation, write and run code. Never do maths in your head. Be concise."""


def run(task):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    return run_agent(messages, TOOLS)


if __name__ == "__main__":
    print(run("Which Python version is installed? "
              "And what is the total of the amount column in data/sales.csv?"))
