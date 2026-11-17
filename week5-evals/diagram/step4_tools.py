# Step 4 — Small tools, one job each
# One big generate_diagram becomes four small tools: query_canvas, add_elements,
# update_elements, remove_elements. The canvas leaves the system prompt: the
# agent reads it when it needs to. The schema's descriptions teach the rules.
# tool_choice replaces preservation: on a modify case, did it look first?
from agent import run_agent
from evals import called_tools, compare, load_dataset, load_experiment, run_eval
from prompts import TOOLS as SYSTEM
from schemas import ADD_RUNTIME
from scorers import (bound_arrows, bound_labels, connectivity, label_keywords,
                     schema, structure, tool_choice)
from tools import CANVAS, new_canvas, query_canvas, remove_elements, update_elements

SCORERS = [schema, structure, tool_choice, label_keywords,
           bound_arrows, connectivity, bound_labels]


def add_elements(elements):
    """Add new elements to the canvas.
    To label a shape, add a text element with containerId set to the shape's id.
    To connect two shapes, set startBinding and endBinding on the arrow."""
    CANVAS.extend(elements)       # keep exactly what the model sent
    return {"added": len(elements)}


add_elements.schema = ADD_RUNTIME
TOOLS = [query_canvas, add_elements, update_elements, remove_elements]


def run(dataset):
    experiment = run_eval("step4_tools", load_dataset(dataset), task, SCORERS)
    return compare(load_experiment("step3_context"), experiment)


def task(case):
    seed = case.get("seed", {})
    new_canvas(seed.get("elements", []))
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": case["input"]},
    ]
    answer = run_agent(messages, TOOLS)
    return {"text": answer, "elements": list(CANVAS), "tool_calls": called_tools(messages)}


if __name__ == "__main__":
    print(run("golden.json"))
