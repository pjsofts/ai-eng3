# evals.py — a small eval harness. Braintrust, Evalite and LangSmith do the
# same four things, with a dashboard on top:
#
#   load_dataset(name)                      the golden test cases
#   run_eval(name, cases, task, scorers)    run every case, score it, save it
#   compare(baseline, experiment)           did the numbers move?
#   called_tools(messages)                  which tools the agent called
#
# An experiment is one run of the whole dataset, saved to experiments/<name>.json.
# Keep them: the point of an eval is comparing today's run with yesterday's.
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
EXPERIMENTS = HERE / "experiments"


def load_dataset(name):
    return json.loads((HERE / "datasets" / name).read_text())


def run_eval(name, cases, task, scorers):
    rows = [run_case(case, task, scorers) for case in cases]
    experiment = {"name": name, "scores": averages(rows), "rows": rows}
    EXPERIMENTS.mkdir(exist_ok=True)
    (EXPERIMENTS / f"{name}.json").write_text(json.dumps(experiment, indent=1))
    return experiment


def run_case(case, task, scorers):
    """Run the agent on one case, then let every scorer grade the output."""
    started = time.time()
    output = task(case)
    scores = {}
    for scorer in scorers:
        score = scorer(case, output)
        if score is not None:                  # None: this scorer skips this case
            scores[scorer.__name__] = round(score, 2)
    return {"id": case["id"], "category": case["category"], "scores": scores,
            "seconds": round(time.time() - started, 1), "output": output}


def called_tools(messages):
    """The tools the agent called after the last user message, in order."""
    last = max(i for i, message in enumerate(messages) if message["role"] == "user")
    return [call["function"]["name"]
            for message in messages[last:] for call in message.get("tool_calls", [])]


def averages(rows):
    """One number per scorer: the mean over the cases it graded."""
    names = {name for row in rows for name in row["scores"]}
    means = {}
    for name in sorted(names):
        graded = [row["scores"][name] for row in rows if name in row["scores"]]
        means[name] = round(sum(graded) / len(graded), 2)
    return means


def load_experiment(name):
    path = EXPERIMENTS / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else None


def compare(baseline, experiment):
    """A table: each scorer, before and after. The arrow is what you look at."""
    if baseline is None:
        return report(experiment)
    lines = [f"{'scorer':<16}{baseline['name']:>22}{experiment['name']:>22}"]
    for name in sorted(set(baseline["scores"]) | set(experiment["scores"])):
        old, new = baseline["scores"].get(name), experiment["scores"].get(name)
        move = "" if old is None or new is None else f"   {arrow(new - old)} {new - old:+.0%}"
        lines.append(f"{name:<16}{percent(old):>22}{percent(new):>22}{move}")
    return "\n".join(lines)


def report(experiment):
    return "\n".join(f"{name:<16}{percent(score):>8}" for name, score in experiment["scores"].items())


def percent(score):
    return "—" if score is None else f"{score:.0%}"


def arrow(change):
    return "▲" if change > 0.005 else "▼" if change < -0.005 else "="
