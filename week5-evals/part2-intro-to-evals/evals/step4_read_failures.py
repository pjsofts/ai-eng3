# Step 4 — Read the failures before you change anything.
# Lesson 3: a low score does not say whether the model or the prompt is at
# fault. Group the failed cases by kind and by field, read the answers, and
# find what they have in common. The fix depends on the pattern.
from collections import defaultdict

from graders import with_judge
from harness import grade, load_cases, load_run, stats

RUN = "step1_small"


def main():
    cases = {case["id"]: case for case in load_cases()}
    result = grade(load_run(RUN), list(cases.values()), with_judge)     # the calibrated judge
    s = stats(result)
    print(f"{RUN}: {s['cases'] - s['completed']} of {s['cases']} failed\n")

    groups = defaultdict(list)
    for row in result["rows"]:
        for field, ok in row["grades"].items():
            if field != "verdict" and not ok:
                groups[(row["category"], field)].append(row)

    for (category, field), rows in sorted(groups.items()):
        print(f"{category} · {field}: {len(rows)} failed")
        for row in rows:
            expected = cases[row["id"]]["expected"][field]
            print(f"    {row['id']}  expected {expected!r}")
            print(f"         got      {row['answer'][field]!r}")
        print()


if __name__ == "__main__":
    main()
