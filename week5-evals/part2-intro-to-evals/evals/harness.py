# harness.py — run a model over the cases, grade the answers, compare runs.
#
#   load_cases(name)                        the labeled cases
#   run(name, model, prompt, cases)         one model, one prompt, every case: saved to runs/
#   grade(run, cases, grader)               right / wrong per field, and "completed"
#   report(runs, floor)                     one row per run: accuracy, cost, cost per task
#   cheapest(runs, floor)                   the decision
import json
from pathlib import Path

from llm import chat
from models import cost
from prompts import EXTRACT_V1, EXTRACT_V2

HERE = Path(__file__).parent
RUNS = HERE / "runs"
PROMPTS = {"v1": EXTRACT_V1, "v2": EXTRACT_V2}
CATEGORIES = ("typical", "multi_service", "open")


def load_cases(name="golden.json"):
    return json.loads((HERE / "datasets" / name).read_text())


# ---- run --------------------------------------------------------------------

def run(name, model, prompt, cases):
    """Ask the model about every case. Keep the answers and what each call cost."""
    rows = []
    for case in cases:
        reply = chat(model.id, PROMPTS[prompt], case["report"])
        rows.append({"id": case["id"], "category": case["category"],
                     "answer": parse_answer(reply.text), "raw": reply.text,
                     "cost": cost(model, reply)})
    result = {"name": name, "tier": model.tier, "model": model.id, "prompt": prompt,
              "cost": sum(row["cost"] for row in rows), "rows": rows}
    save(result)
    return result


def parse_answer(text):
    """The JSON object in the reply. With prompt v2 a <source> quote comes first."""
    text = text.split("</source>")[-1]
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return None                                  # unparseable counts as wrong


def save(result):
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{result['name']}.json").write_text(json.dumps(result, indent=1))


def load_run(name):
    path = RUNS / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"runs/{name}.json is missing: run the earlier step first.")
    return json.loads(path.read_text())


# ---- grade ------------------------------------------------------------------

def grade(result, cases, grader):
    """A case is completed only when every field is right."""
    by_id = {case["id"]: case for case in cases}
    for row in result["rows"]:
        row["grades"] = grader(by_id[row["id"]], row["answer"])
        row["completed"] = all(row["grades"][field] for field in ("service", "severity", "root_cause"))
    save(result)
    return result


# ---- compare ----------------------------------------------------------------

def stats(result):
    rows = result["rows"]
    done = sum(row["completed"] for row in rows)
    by_category = {}
    for category in CATEGORIES:
        mine = [row for row in rows if row["category"] == category]
        by_category[category] = sum(row["completed"] for row in mine) / len(mine) if mine else None
    return {"accuracy": done / len(rows), "completed": done, "cases": len(rows), "by_category": by_category,
            "per_1000": result["cost"] / done * 1000 if done else None}


def report(results, floor):
    """The table you decide from. Cost per completed task, not per call:
    a cheap model that gets half the cases wrong is not cheap."""
    head = f"{'run':<22}{'typical':>9}{'multi':>7}{'open':>7}{'overall':>9}{'run cost':>11}{'per 1,000 done':>16}"
    lines = [head, "-" * len(head)]
    for result in results:
        s = stats(result)
        cats = "".join(f"{pct(s['by_category'][c]):>{w}}" for c, w in zip(CATEGORIES, (9, 7, 7)))
        mark = "  ✓" if s["accuracy"] >= floor else "  below the floor"
        per = f"${s['per_1000']:.4f}" if s["per_1000"] is not None else "—"
        lines.append(f"{label(result):<22}{cats}{pct(s['accuracy']):>9}{'$' + format(result['cost'], '.5f'):>11}{per:>16}{mark}")
    return "\n".join(lines)


def cheapest(results, floor):
    """The cheapest model per completed task that clears the floor."""
    passing = [r for r in results if stats(r)["accuracy"] >= floor]
    if not passing:
        return None
    return min(passing, key=lambda r: stats(r)["per_1000"])


def label(result):
    return f"{result['tier']} · {result['prompt']}"


def pct(value):
    return "—" if value is None else f"{value:.0%}"
