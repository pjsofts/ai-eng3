# Step 6 — A smoke eval on every pull request.
# Lesson 4: a prompt edit can break answers that were right. So every PR that
# touches the prompt runs a small, fast slice of the suite: 8 cases covering
# every kind of report, on the model we ship. Below the threshold, the check
# fails and branch protection blocks the merge.
#
#   python step6_smoke_eval.py               the prompt on main: passes
#   python step6_smoke_eval.py --prompt v1   a PR that "simplifies" the prompt
#
# CI: ../.github/workflows/smoke-eval.yml runs this, comments the result on the
# PR, then fails the check if the exit code is 1.
import argparse
import sys
from pathlib import Path

from graders import with_judge
from harness import grade, load_cases, run, stats
from models import by_tier

SMOKE = ["r01", "r06", "r09", "r12", "r15", "r17", "r21", "r23"]   # typical, multi_service, open
THRESHOLD = 7 / 8
SHIPPED = by_tier("small")                                        # the decision from step 5


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="v2")
    prompt = parser.parse_args().prompt

    cases = [case for case in load_cases() if case["id"] in SMOKE]
    result = grade(run("smoke", SHIPPED, prompt, cases), cases, with_judge)
    s = stats(result)
    passed = s["accuracy"] >= THRESHOLD

    failed = [row["id"] for row in result["rows"] if not row["completed"]]
    comment = (f"### Smoke eval: {'passed' if passed else 'FAILED'}\n\n"
               f"{s['completed']} of {s['cases']} cases right ({s['accuracy']:.0%}). "
               f"Threshold {THRESHOLD:.1%}. Model {SHIPPED.id}, prompt {prompt}.\n\n"
               + (f"Failed: {', '.join(failed)}\n" if failed else ""))
    (Path(__file__).parent / "smoke_comment.md").write_text(comment)
    print(comment)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
