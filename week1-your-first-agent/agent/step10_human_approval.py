# Step 10 — A human approves
# The shell can do anything you can, including deleting your files. So before a
# risky tool runs, the loop stops and asks you. Reading is safe; changing is not.
# A "no" is not an error: the model is told, and decides what to do next.
# This is the loop from step 4 plus one if.
from llm import chat, tool_result
from tools import (delete_file, execute_code, list_files, read_file,
                   run_command, write_file)

TOOLS = {"list_files": list_files, "read_file": read_file,
         "write_file": write_file, "delete_file": delete_file,
         "run_command": run_command, "execute_code": execute_code}
NEEDS_APPROVAL = {"write_file", "delete_file", "run_command", "execute_code"}
MAX_STEPS = 10

SYSTEM = """You are a helpful assistant that works with the files in a workspace folder.
Some tools need the user's approval. If the user says no, do not try another way.
Be concise."""


def run(task):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    for step in range(MAX_STEPS):
        reply = chat(messages, tools=TOOLS.values())
        messages.append(reply.message)

        if not reply.tool_calls:
            return reply.text

        for call in reply.tool_calls:
            if call.name in NEEDS_APPROVAL and not approved(call):   # the gate
                result = "The user said no, so this was NOT done. Tell them."
            else:
                result = TOOLS[call.name](**call.args)
            messages.append(tool_result(call, result))

    return "Stopped: too many steps."


def approved(call):
    answer = input(f"Allow {call.name}({call.args})? [y/n] ")
    return answer.strip().lower() == "y"


if __name__ == "__main__":
    print(run("Delete todo.txt, then tell me which files are left."))
