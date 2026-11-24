# Step 4 — The agent loop
# One tool call is not enough: real tasks need several, and you don't know how
# many in advance. So we loop: ask the model, run the tools it asks for, give it
# the results, ask again. The model decides when to stop, by asking for no tools.
from llm import chat, tool_result
from tools import get_current_time, list_files, read_file

TOOLS = {"get_current_time": get_current_time,
         "list_files": list_files,
         "read_file": read_file}
MAX_STEPS = 10  # a confused model would loop forever, on your money

SYSTEM = """You are a helpful assistant.
You can look at the files in a workspace folder.
Use the tools when they help. Be concise."""


def run(task):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    for step in range(MAX_STEPS):
        reply = chat(messages, tools=TOOLS.values())     # think
        messages.append(reply.message)                   # remember what it said

        if not reply.tool_calls:                         # no tools: the answer
            return reply.text

        for call in reply.tool_calls:                    # act
            result = TOOLS[call.name](**call.args)
            messages.append(tool_result(call, result))   # observe

    return "Stopped: too many steps."


if __name__ == "__main__":
    print(run("List the files in the workspace, then read the todo list "
              "and tell me what is most urgent."))
