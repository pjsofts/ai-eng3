# Step 7 — Web search
# The model's knowledge stopped on the day its training did. For anything
# newer, it has to look it up. web_search is one more tool; its docstring
# also says when NOT to use it, or the agent googles the capital of France.
from agent import run_agent
from tools import get_current_time, web_search

TOOLS = [web_search, get_current_time]

SYSTEM = """You are a helpful assistant. Answer from what you know when you can.
Search the web only for things that change. Be concise."""


def run(question):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    return run_agent(messages, TOOLS)


if __name__ == "__main__":
    print(run("What is the weather in Tehran today?"))
