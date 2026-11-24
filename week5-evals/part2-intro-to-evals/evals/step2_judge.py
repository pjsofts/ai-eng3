# Step 2 — A minimum viable eval: the right grader for each field.
# Lesson 2: service and severity have one right value, so code checks them.
# root_cause is a sentence that can be said many ways, so an LLM judge grades it
# with a rubric. The judge sees the report, the answer and the rubric, but NOT
# our expected answer: a right answer in other words must not lose points.
#
# No new model calls: we grade the answers step 1 already saved.
from functools import partial

from graders import with_judge
from harness import grade, load_cases, load_run, report
from models import LADDER
from prompts import RUBRIC_V1
from step1_pick_a_model import FLOOR


def main():
    cases = load_cases()
    judged = []
    for model in LADDER:
        before = {row["id"]: row["grades"]["root_cause"] for row in load_run(f"step1_{model.tier}")["rows"]}
        result = grade(load_run(f"step1_{model.tier}"), cases, partial(with_judge, rubric=RUBRIC_V1))
        judged.append(result)
        for row in result["rows"]:
            if row["grades"]["root_cause"] != before[row["id"]] or row["grades"].get("verdict", {}).get("verdict") == "unknown":
                show(model.tier, row, before[row["id"]])

    print("\nWith the judge on root_cause:\n")
    print(report(judged, FLOOR))


def show(tier, row, word_check):
    verdict = row["grades"]["verdict"]
    print(f"{tier} · {row['id']}  word check: {'right' if word_check else 'wrong'}   judge: {verdict['verdict']}")
    print(f"    answer: {row['answer']['root_cause']}")
    print(f"    why:    {verdict['explanation']}\n")


if __name__ == "__main__":
    main()
