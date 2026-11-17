# Step 1 — An eval harness, by hand
# Before you change anything, measure. Run every case of the golden dataset
# through the agent and save what came back. Then a person reads each result
# and scores it from 1 to 5 with the rubric. That is an eval. It is also slow,
# and two people give the same diagram different scores.
import json
import time
from datetime import datetime
from pathlib import Path

from agent import run_agent
from evals import load_dataset
from prompts import FIRST
from step0_first_agent import TOOLS
from tools import CANVAS, new_canvas

RUBRIC = """5  every expected characteristic, clean layout
4  most of them, small problems
3  the structure is there, but overlaps, wrong links or missing labels
2  recognisable, mostly wrong
1  empty, an error, or the wrong kind of diagram"""


def run(dataset):
    cases = load_dataset(dataset)
    results = [run_case(case) for case in cases]
    path = save(results)

    empty = sum(1 for result in results if not result["elements"])
    return (f"{len(results)} cases, {empty} drew nothing. Saved to results/{path.name}\n\n"
            f"Now open the file and give each case a score:\n{RUBRIC}")


def run_case(case):
    new_canvas()
    messages = [
        {"role": "system", "content": FIRST},
        {"role": "user", "content": case["input"]},
    ]
    started = time.time()
    answer = run_agent(messages, TOOLS)
    return {"id": case["id"], "input": case["input"], "expected": case["expected"],
            "answer": answer, "elements": list(CANVAS),
            "seconds": round(time.time() - started, 1),
            "score": None, "notes": ""}          # a person fills these in


def save(results):
    folder = Path(__file__).parent / "results"
    folder.mkdir(exist_ok=True)
    path = folder / f"{datetime.now():%Y-%m-%d_%H%M%S}.json"
    path.write_text(json.dumps(results, indent=1))
    return path


if __name__ == "__main__":
    print(run("golden.json"))
