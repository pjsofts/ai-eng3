# Step 6 — File system tools
# Real hands: list, read, write and delete files. Files are also the agent's
# notebook: memory, state and a scratch pad that outlive one conversation.
# Two rules keep it safe enough for class (both in tools.py):
#   1. every path must stay inside the workspace folder (inside_workspace)
#   2. errors come back as text, so the model can read them and recover
from agent import run_agent
from tools import delete_file, list_files, read_file, write_file

TOOLS = [list_files, read_file, write_file, delete_file]

SYSTEM = """You are a helpful assistant that works with the files in a workspace folder.
Read a file before you change it. Be concise."""


def run(task):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    return run_agent(messages, TOOLS)


if __name__ == "__main__":
    print(run("Change the port in config.json to 3000, "
              "then add 'deploy on Friday' to todo.txt."))
