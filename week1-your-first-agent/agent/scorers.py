# scorers.py — small functions that turn one agent run into a score from 0 to 1.
#
#   single turn (step 3):  tools_selected, tools_avoided, selection_score
#   multi turn  (step 5):  tool_order_correct, tools_avoided, llm_judge
from llm import ask_json


def tools_selected(chosen, expected):
    """1 if the model picked every expected tool, else 0."""
    return 1.0 if all(tool in chosen for tool in expected) else 0.0


def tools_avoided(chosen, forbidden):
    """1 if the model picked none of the forbidden tools, else 0."""
    return 0.0 if any(tool in chosen for tool in forbidden) else 1.0


def selection_score(chosen, expected):
    """Partial credit (the F1 score): the right tools, and only the right tools."""
    right = len(set(chosen) & set(expected))
    if right == 0:
        return 0.0
    precision = right / len(set(chosen))    # of what it picked, how much was right?
    recall = right / len(set(expected))     # of what was right, how much did it pick?
    return 2 * precision * recall / (precision + recall)


def tool_order_correct(called, expected_order):
    """How much of the expected order was followed. Other calls in between are fine:
    called   [list_files, read_file, write_file]
    expected [read_file, write_file]               -> 1.0"""
    found = 0
    for tool in called:
        if found < len(expected_order) and tool == expected_order[found]:
            found += 1
    return found / len(expected_order)


JUDGE = """You grade the final answer of an AI agent.
Score it from 1 to 10:
  10   fully solves the task and uses the tool results correctly
  7-9  mostly right, small problems
  4-6  partly solves the task
  1-3  wrong or off topic
Reply as JSON: {"score": <1-10>, "reason": "<one sentence>"}"""


def llm_judge(task, tool_results, answer):
    """Ask a model to grade the answer. Returns (score from 0 to 1, reason)."""
    prompt = (f"Task: {task}\n\n"
              f"Tool results the agent saw: {tool_results}\n\n"
              f"The agent's final answer: {answer}")
    verdict = ask_json(prompt, system=JUDGE)
    return verdict["score"] / 10, verdict["reason"]
