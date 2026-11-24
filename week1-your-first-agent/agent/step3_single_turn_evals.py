# Step 3 — Single-turn evals
# Before giving the agent more power, measure the one decision nothing later
# can fix: which tool does the model pick?
# One prompt in, one reply out. No tool is run: the model only sees the name,
# parameters and docstring, so we can test those before the tools even work.
from llm import chat
from scorers import selection_score, tools_avoided, tools_selected
from tools import delete_file, list_files, read_file, run_command, write_file

TOOLS = [read_file, write_file, list_files, delete_file, run_command]
ALL = ["read_file", "write_file", "list_files", "delete_file", "run_command"]

CASES = [
    # golden: it must pick this tool
    {"prompt": "Read the contents of config.json",
     "category": "golden", "expected": ["read_file"]},
    {"prompt": "Show me all the files in the notes folder",
     "category": "golden", "expected": ["list_files"]},
    {"prompt": "Create a file called hello.txt that says hi",
     "category": "golden", "expected": ["write_file"]},
    {"prompt": "Check which Python version is installed",
     "category": "golden", "expected": ["run_command"]},

    # secondary: more than one tool is reasonable, so partial credit
    {"prompt": "What's in this project? Show me around.",
     "category": "secondary", "expected": ["list_files", "read_file"]},

    # negative: it must NOT reach for these
    {"prompt": "What is the capital of France?",
     "category": "negative", "forbidden": ALL},
    {"prompt": "What is Python used for?",
     "category": "negative", "forbidden": ["run_command"]},
]


def run(new_case):
    # The input box adds one golden case: "prompt -> tool_name"
    cases = list(CASES)
    prompt, _, tool = new_case.partition("->")
    if tool.strip():
        cases.append({"prompt": prompt.strip(), "category": "golden", "expected": [tool.strip()]})

    results = [score_case(case) for case in cases]
    return report(results)


def score_case(case):
    reply = chat([{"role": "user", "content": case["prompt"]}], tools=TOOLS)
    chosen = [call.name for call in reply.tool_calls]

    if case["category"] == "golden":
        score = tools_selected(chosen, case["expected"])
    elif case["category"] == "secondary":
        score = selection_score(chosen, case["expected"])
    else:
        score = tools_avoided(chosen, case["forbidden"])

    return {"prompt": case["prompt"], "category": case["category"],
            "chosen": chosen, "score": score}


def report(results):
    lines = []
    for result in results:
        verdict = "PASS" if result["score"] >= 0.5 else "FAIL"
        chosen = ", ".join(result["chosen"]) or "no tool"
        lines.append(f"{verdict}  {result['score']:.2f}  {result['category']:<9}  "
                     f"{result['prompt']}  →  {chosen}")
    passed = sum(1 for result in results if result["score"] >= 0.5)
    lines.append(f"\n{passed}/{len(results)} passed")
    return "\n".join(lines)


if __name__ == "__main__":
    print(run("Remove the old todo.txt -> delete_file"))
