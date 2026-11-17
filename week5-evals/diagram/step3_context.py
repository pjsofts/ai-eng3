# Step 3 — Context engineering
# Same agent, same tools. Two changes to what the model reads:
#   1. a real system prompt: a niche, hard rules, a layout grid, patterns,
#      "do NOT" lines and a worked example (prompts.CONTEXT)
#   2. the canvas, summarized as short text, in the system prompt every turn
# Two new scorers check the picture, not just the parts. Then compare with step 2.
from agent import run_agent
from canvas import summarize
from evals import called_tools, compare, load_dataset, load_experiment, run_eval
from prompts import CONTEXT
from scorers import bound_arrows, connectivity
from step0_first_agent import TOOLS
from step2_scorers import SCORERS as STEP2_SCORERS
from tools import CANVAS, new_canvas

SCORERS = STEP2_SCORERS + [bound_arrows, connectivity]


def run(dataset):
    experiment = run_eval("step3_context", load_dataset(dataset), task, SCORERS)
    return compare(load_experiment("step2_baseline"), experiment)


def task(case):
    seed = case.get("seed", {})
    new_canvas(seed.get("elements", []))
    messages = [
        {"role": "system", "content": system_prompt(CANVAS)},
        {"role": "user", "content": case["input"]},
    ]
    answer = run_agent(messages, TOOLS)
    return {"text": answer, "elements": list(CANVAS), "tool_calls": called_tools(messages)}


def system_prompt(elements):
    """The rules, then what is on the canvas right now."""
    return f"{CONTEXT}\n\n# The canvas now\n\n{summarize(elements)}"


if __name__ == "__main__":
    print(run("golden.json"))
