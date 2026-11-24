# Step 7 — Measure the layout, and let the agent see it
# A new scorer, no_overlaps, and the same check inside add_elements: every
# result now lists the boxes that collide, so the agent can fix them right away.
# One function (overlaps.find_overlaps) for both, so they can never disagree.
#
# And a more honest dataset, golden_2.json: the modify seeds are drawn the way
# the app draws them, and new cases push on layout (long labels, a tight grid).
import tools
from agent import run_agent
from evals import called_tools, compare, load_dataset, load_experiment, run_eval
from overlaps import find_overlaps
from prompts import OVERLAPS, SKELETON
from schemas import ADD_SKELETON
from scorers import no_overlaps
from step6_honest_eval import SCORERS as STEP6_SCORERS
from tools import CANVAS, new_canvas, query_canvas, remove_elements, update_elements

SCORERS = STEP6_SCORERS + [no_overlaps]


def add_elements(elements):
    result = tools.add_elements(elements)
    result["overlaps"] = find_overlaps(CANVAS)    # feedback, the moment it happens
    return result


add_elements.__doc__ = tools.add_elements.__doc__ + (
    "\n\nThe result lists overlaps: pairs of ids whose boxes collide. "
    "If there are any, move them apart with update_elements.")
add_elements.schema = ADD_SKELETON
TOOLS = [query_canvas, add_elements, update_elements, remove_elements]


def run(dataset):
    experiment = run_eval("step7_overlaps", load_dataset(dataset), task, SCORERS)
    return compare(load_experiment("step6_honest"), experiment)


def task(case):
    seed = case.get("seed", {})
    new_canvas(seed.get("elements", []))
    messages = [
        {"role": "system", "content": SKELETON + OVERLAPS},
        {"role": "user", "content": case["input"]},
    ]
    answer = run_agent(messages, TOOLS)
    return {"text": answer, "elements": list(CANVAS), "tool_calls": called_tools(messages)}


if __name__ == "__main__":
    print(run("golden_2.json"))
