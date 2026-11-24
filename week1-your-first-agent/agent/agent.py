# agent.py — the agent loop from step 4, packaged so later steps can reuse it.
#
#   run_agent(messages, tools) -> the final answer
#
# messages is the conversation. The loop adds to it, so after the run it holds
# everything that happened: every reply, every tool call, every result.
from llm import chat, tool_result

MAX_STEPS = 10  # never let an agent loop forever


def run_agent(messages, tools):
    tools = {tool.__name__: tool for tool in tools}

    for step in range(MAX_STEPS):
        reply = chat(messages, tools=tools.values())    # think
        messages.append(reply.message)

        if not reply.tool_calls:                        # no tools: the answer
            return reply.text

        for call in reply.tool_calls:                   # act
            result = run_tool(tools, call)
            messages.append(tool_result(call, result))  # observe

    return "Stopped: too many steps."


def run_tool(tools, call):
    """Run one tool. Any problem becomes a message for the model, not a crash."""
    if call.name not in tools:
        return f"Error: there is no tool called {call.name}"
    try:
        return tools[call.name](**call.args)
    except Exception as error:
        return f"Error: {error}"
