# ReAct: Reason + Act, in a loop.
# The model thinks, calls a tool, sees the result (observation), and repeats
# until it can answer. This loop is what makes it an agent.
#
# Who decides what happens next?  The model, at every step.
from llm import chat, tool_result
from tools import calculate, search

TOOLS = {"search": search, "calculate": calculate}
MAX_STEPS = 6  # never let an agent loop forever

SYSTEM = """Answer the user's question using the tools.
Before each tool call, write one short sentence about what you are doing and why."""


def run(question):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for step in range(MAX_STEPS):
        reply = chat(messages, tools=TOOLS.values())   # Reason
        messages.append(reply.message)

        if not reply.tool_calls:                       # nothing left to do
            return reply.text

        for call in reply.tool_calls:                  # Act
            observation = TOOLS[call.name](**call.args)
            messages.append(tool_result(call, observation))  # Observe

    return "Stopped: too many steps."


if __name__ == "__main__":
    print(run("How old was the engineer behind the Eiffel Tower when it opened?"))
