# Step 1 — Which model? Let the cases decide.
# Lesson 1: set an accuracy floor, run every model on the same cases with the
# same prompt, and buy the cheapest one that clears the floor, measured by cost
# per COMPLETED task, not cost per call.
#
# The task: read an incident report, extract service, severity and root_cause.
from graders import by_code
from harness import cheapest, grade, load_cases, report, run
from models import LADDER

# The floor comes from what a wrong answer costs. A wrong root cause sends the
# on-call engineer the wrong way; the review team can catch and fix about 1
# report in 10. So 9 in 10 must be right.
FLOOR = 0.90


def main():
    cases = load_cases()
    results = []
    for model in LADDER:                                       # same cases, same prompt
        result = run(f"step1_{model.tier}", model, "v1", cases)
        results.append(grade(result, cases, by_code))

    print(report(results, FLOOR))
    choice = cheapest(results, FLOOR)
    print(f"\nFloor {FLOOR:.0%}. Pick: {choice['tier']} ({choice['model']})" if choice
          else f"\nNo model clears {FLOOR:.0%}.")


if __name__ == "__main__":
    main()
