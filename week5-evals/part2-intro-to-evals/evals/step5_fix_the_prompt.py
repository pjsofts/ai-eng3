# Step 5 — Fix the prompt, then decide on the model again.
# Lesson 3: the failures had a pattern, so the prompt gets three changes
# (prompts.EXTRACT_V2, diff it with V1):
#   1. say when null applies: under investigation, suspected, not confirmed
#   2. quote the sentence first: <source>…</source>, or <source>none</source>
#   3. if the severity changed, use the final one
# Then rerun ALL the cases on ALL the models, and check every column: a fix
# for one kind of case can break another.
from graders import with_judge
from harness import cheapest, grade, load_cases, load_run, report, run
from models import LADDER
from step1_pick_a_model import FLOOR


def main():
    cases = load_cases()
    before = [grade(load_run(f"step1_{m.tier}"), cases, with_judge) for m in LADDER]
    after = [grade(run(f"step5_{m.tier}", m, "v2", cases), cases, with_judge) for m in LADDER]

    print(report(before + after, FLOOR))
    for old, new in zip(before, after):
        broke = [o["id"] for o, n in zip(old["rows"], new["rows"]) if o["completed"] and not n["completed"]]
        print(f"{new['tier']}: right before, wrong now: {', '.join(broke) or 'none'}")

    choice = cheapest(after, FLOOR)
    print(f"\nFloor {FLOOR:.0%}. Pick: {choice['tier']} with prompt v2 ({choice['model']})")


if __name__ == "__main__":
    main()
