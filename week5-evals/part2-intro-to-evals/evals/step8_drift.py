# Step 8 — Catch drift: grade a sample of live traffic every night.
# Lesson 4: the cases you wrote stop looking like real traffic. Inputs change
# slowly, and accuracy drops without anyone touching the prompt. So every night:
#   1. sample a few percent of the day's reports
#   2. grade them with the judge: report + answer + rubric, no expected answer
#   3. alert only if tonight is more than 2 standard deviations below recent nights
#   4. every answer graded incorrect becomes a new case for the suite
#
#   python step8_drift.py             night 14: a new status-page tool goes live
#   python step8_drift.py --night 10  an ordinary night
import argparse
import json
import statistics
from pathlib import Path

import traffic
from graders import judge
from harness import PROMPTS, parse_answer
from llm import chat
from prompts import RUBRIC_FULL
from step6_smoke_eval import SHIPPED

SHARE = 0.05             # 5% of 400 reports: 20 a night. Tune it.
BASELINE_NIGHTS = 7
HERE = Path(__file__).parent


def score_night(n):
    """The share of sampled answers the judge calls correct, and the ones it doesn't."""
    sampled = traffic.sample(traffic.night(n), SHARE, seed=f"night-{n}")
    wrong = []
    for item in sampled:
        reply = chat(SHIPPED.id, PROMPTS["v2"], item["report"])
        answer = parse_answer(reply.text)
        verdict = judge(item["report"], answer, RUBRIC_FULL) if answer else {
            "verdict": "incorrect", "explanation": "The reply was not valid JSON."}
        if verdict["verdict"] != "correct":
            wrong.append({"report": item["report"], "answer": answer, "why": verdict["explanation"]})
    return 1 - len(wrong) / len(sampled), wrong


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--night", type=int, default=traffic.NEW_TOOL_FROM)
    n = parser.parse_args().night

    history = json.loads((HERE / "datasets" / "drift_history.json").read_text())
    recent = [h["score"] for h in history if h["night"] < n][-BASELINE_NIGHTS:]
    mean, sd = statistics.mean(recent), statistics.stdev(recent)
    score, wrong = score_night(n)

    print(f"Last {len(recent)} nights: {', '.join(f'{s:.0%}' for s in recent)}")
    print(f"Baseline {mean:.1%}, alert below {mean - 2 * sd:.1%} (2 standard deviations)")
    print(f"Night {n}: {score:.0%}  " + ("ALERT: accuracy dropped" if score < mean - 2 * sd else "ok"))

    for item in wrong:
        print(f"\n  {item['report'].splitlines()[0]}\n  answer: {item['answer']}\n  judge:  {item['why']}")

    if wrong:                                   # a person writes the expected answers,
        path = HERE / "runs" / "new_cases.json"   # then they join golden.json
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps([{"report": w["report"], "expected": None} for w in wrong], indent=1))
        print(f"\n{len(wrong)} reports saved to runs/new_cases.json: label them, add them to the suite.")


if __name__ == "__main__":
    main()
