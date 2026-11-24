# agent.py — an agent is an LLM in a loop, with tools.
# This is the same loop as react.py, packaged as a class so the
# multi-agent workflows can create several agents in one line each.
from llm import chat, tool_result

MAX_STEPS = 8


class Agent:
    def __init__(self, name, instructions, tools=()):
        self.name = name
        self.instructions = instructions
        self.tools = {tool.__name__: tool for tool in tools}

    def run(self, task):
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": task},
        ]
        for step in range(MAX_STEPS):
            reply = chat(messages, tools=list(self.tools.values()))
            messages.append(reply.message)

            if not reply.tool_calls:  # no tool needed: this is the answer
                return reply.text

            for call in reply.tool_calls:
                result = self.tools[call.name](**call.args)
                messages.append(tool_result(call, result))

        return "Stopped: too many steps."
