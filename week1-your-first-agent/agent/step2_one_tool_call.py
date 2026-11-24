# Step 2 — One tool call
# Give the model a tool. It cannot run the tool itself: it can only ASK us to.
# So one tool call is three acts:
#   1. we ask, with the tool on the table
#   2. the model asks for the tool; WE run it and add the result
#   3. we ask again; now the model can answer
from llm import chat, tool_result
from tools import get_current_time


def run(question):
    messages = [{"role": "user", "content": question}]

    reply = chat(messages, tools=[get_current_time])   # 1. ask
    messages.append(reply.message)

    if not reply.tool_calls:                           # no tool needed
        return reply.text

    for call in reply.tool_calls:                      # 2. run the tool
        result = get_current_time(**call.args)
        messages.append(tool_result(call, result))

    final = chat(messages, tools=[get_current_time])   # 3. ask again
    return final.text


if __name__ == "__main__":
    print(run("What time is it right now?"))
