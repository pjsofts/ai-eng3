# Step 3 — Check the judge before you trust it.
# Lesson 2, last step: a person graded the small model's root_cause answers by
# hand (datasets/hand_labels.json). Where the judge and the person disagree,
# the rubric is missing a rule. Write the rule down, grade again.
import json
from pathlib import Path

from graders import judge
from harness import load_cases, load_run
from prompts import RUBRIC_V1, RUBRIC_V2


def main():
    hand = json.loads((Path(__file__).parent / "datasets" / "hand_labels.json").read_text())
    people = {label["id"]: label for label in hand["labels"]}
    reports = {case["id"]: case["report"] for case in load_cases()}
    answers = {row["id"]: row["answer"]["root_cause"] for row in load_run(hand["run"])["rows"]}

    for name, rubric in (("rubric v1", RUBRIC_V1), ("rubric v2", RUBRIC_V2)):
        disagree = []
        for case_id, person in people.items():
            verdict = judge(reports[case_id], answers[case_id], rubric)
            if verdict["verdict"] != person["verdict"]:
                disagree.append((case_id, person, verdict))
        agree = len(people) - len(disagree)
        print(f"{name}: the judge agrees with the person on {agree} of {len(people)} ({agree / len(people):.0%})")
        for case_id, person, verdict in disagree:
            print(f"    {case_id}  person: {person['verdict']:<9} judge: {verdict['verdict']}")
            print(f"           answer: {answers[case_id]}")
            print(f"           person: {person.get('note', '')}")
            print(f"           judge:  {verdict['explanation']}")
        print()


if __name__ == "__main__":
    main()
