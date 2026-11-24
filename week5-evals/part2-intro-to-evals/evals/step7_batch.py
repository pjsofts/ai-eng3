# Step 7 — The full suite, as one batch, at half price.
# Lesson 4: the smoke eval is small so it can be fast. The full suite (every
# case on every model) doesn't need an answer in a minute, so send it as a
# batch: one file of requests, run within 24 hours, at half the price.
#
#   python step7_batch.py                     submit, and in Replay collect at once
#   python step7_batch.py --collect BATCH_ID  Live: collect later
#
# Results come back in any order: key them by custom_id, never by position.
import argparse

from graders import with_judge
from harness import PROMPTS, grade, load_cases, parse_answer, save
from llm import MODE, collect_batch, submit_batch
from models import LADDER, cost


def requests(cases, prompt="v2"):
    return [{"custom_id": f"{case['id']}__{model.tier}", "model": model.id,
             "system": PROMPTS[prompt], "user": case["report"]}
            for model in LADDER for case in cases]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect")
    batch_id = parser.parse_args().collect
    cases = load_cases()

    if batch_id is None:
        batch_id = submit_batch(requests(cases))
        print(f"Submitted {len(cases) * len(LADDER)} requests as {batch_id}.")
        if MODE == "live":
            print(f"Collect it later: python step7_batch.py --collect {batch_id}")
            return

    status, counts, replies = collect_batch(batch_id)
    print(f"Status: {status}. Counts: {counts}")
    if status != "completed":
        return                         # check the counts before you score anything
    print(f"First results back: {', '.join(list(replies)[:4])}, …\n")

    for model in LADDER:
        rows, batch_cost, full_cost = [], 0.0, 0.0
        for case in cases:
            reply = replies.get(f"{case['id']}__{model.tier}")
            if reply is None:
                continue                                   # failed or expired: no answer
            batch_cost += cost(model, reply, batch=True)
            full_cost += cost(model, reply)
            rows.append({"id": case["id"], "category": case["category"],
                         "answer": parse_answer(reply.text), "raw": reply.text, "cost": cost(model, reply, batch=True)})
        result = {"name": f"step7_{model.tier}", "tier": model.tier, "model": model.id,
                  "prompt": "v2", "cost": batch_cost, "rows": rows}
        save(result)
        done = sum(row["completed"] for row in grade(result, cases, with_judge)["rows"])
        print(f"{model.tier:<7} {done}/{len(rows)} right   batch ${batch_cost:.5f}   standard ${full_cost:.5f}")


if __name__ == "__main__":
    main()
