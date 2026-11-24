# Step 5 — Multi-turn evals
# Step 3 checked the first choice. Now check the whole run: did the agent call
# the right tools, in the right order, and give a good final answer?
# The tools are mocked: same name and docstring, but they return a fixed result.
# Every run sees the same world, and nothing on disk changes.
import functools

from agent import run_agent
from scorers import llm_judge, tool_order_correct, tools_avoided
from tools import delete_file, list_files, read_file, run_command, write_file

TOOLS = [read_file, write_file, list_files, delete_file, run_command]
SYSTEM = "You are a helpful assistant that works with files. Be concise."

CASES = [
    {   # a fresh task
        "name": "fresh task",
        "messages": [
            {"role": "user", "content": "Read config.json and tell me the API endpoint."},
        ],
        "mocks": {"read_file": '{"api_endpoint": "https://api.example.com/v1"}'},
        "expected_order": ["read_file"],
        "forbidden": ["write_file", "delete_file"],
    },
    {   # the middle of a conversation
        "name": "mid-conversation",
        "messages": [
            {"role": "user", "content": "I'm getting the app ready to deploy."},
            {"role": "assistant", "content": "Great. What should I change?"},
            {"role": "user", "content": "Change the port in config.json to 3000."},
        ],
        "mocks": {"list_files": "[file] config.json\n[file] README.md",
                  "read_file": '{"port": 8080, "debug": true}',
                  "write_file": "Wrote 31 characters to config.json"},
        "expected_order": ["read_file", "write_file"],
        "forbidden": ["delete_file"],
    },
    {   # no tools needed
        "name": "no tools",
        "messages": [{"role": "user", "content": "What is 2 + 2?"}],
        "mocks": {},
        "expected_order": [],
        "forbidden": ["read_file", "write_file", "delete_file", "run_command"],
    },
]


def run(which):
    cases = [case for case in CASES if which in ("all", case["name"])]
    results = [run_case(case) for case in cases]
    return report(results)


def run_case(case):
    tools = []
    for tool in TOOLS:
        result = case["mocks"].get(tool.__name__, "Error: not available in this test")
        tools.append(mocked(tool, result))
    messages = [{"role": "system", "content": SYSTEM}] + case["messages"]

    answer = run_agent(messages, tools)
    called = tools_called(messages)

    order = 1.0
    if case["expected_order"]:
        order = tool_order_correct(called, case["expected_order"])
    avoided = tools_avoided(called, case["forbidden"])
    quality, reason = llm_judge(case["messages"][-1]["content"], case["mocks"], answer)

    return {"name": case["name"], "called": called, "answer": answer,
            "order": order, "avoided": avoided, "quality": quality, "reason": reason}


def mocked(tool, result):
    """A fake tool: same name, docstring and parameters. It always returns result."""
    @functools.wraps(tool)
    def mock_tool(**args):
        return result
    return mock_tool


def tools_called(messages):
    """Every tool the agent asked for, in order. The conversation is the trace."""
    names = []
    for message in messages:
        for call in message.get("tool_calls", []):
            names.append(call["function"]["name"])
    return names


def report(results):
    lines = []
    for r in results:
        lines.append(f"{r['name']}: called {r['called'] or 'no tools'}\n"
                     f"  order {r['order']:.2f} · avoided {r['avoided']:.2f} · "
                     f"judge {r['quality']:.2f} ({r['reason']})")
    return "\n".join(lines)


if __name__ == "__main__":
    print(run("all"))
