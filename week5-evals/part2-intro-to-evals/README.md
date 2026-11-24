# Introduction to evals · code + slides

*Choose a model and a prompt from evidence, not from a feeling.* Eight small
steps of plain Python, no framework, in four lessons:

| Lesson | Steps | The question |
|---|---|---|
| 1 · Which model? | 1 | What is the cheapest model that is good enough? |
| 2 · A minimum viable eval | 2, 3 | How do I grade a free-text answer, and can I trust the grader? |
| 3 · Fix the prompt first | 4, 5 | Is it the model or the prompt? |
| 4 · Evals in production | 6, 7, 8 | How do I keep it good after I ship? |

Follows the arc of Anthropic Academy's
[Introduction to evals](https://academy.claude.com/courses/introduction-to-evals/),
with its own example and an OpenAI-compatible client.

**The task:** read an incident report, extract three fields as JSON:

```json
{"service": "checkout", "severity": "sev2", "root_cause": "A config push set the connection pool size to 5."}
```

`service` and `severity` have one right value. `root_cause` is a sentence that
can be written many ways, and `null` when the report states no cause. That mix
is why the eval needs two kinds of grader.

## Run it

Requires Python 3.11+.

```bash
cd week5-evals/part2-intro-to-evals
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd evals
python step1_pick_a_model.py                          # then step2, step3, … in order
```

Slides: open `slides/index.html` in a browser. `←` `→` to move, `F` fullscreen.
Slides marked **▶ Run · step N** are where you switch to the terminal.

## Replay vs Live

- **Replay** (the default) needs no key and no network. `replay.py` plays the
  three models and the judge, with the mistakes each one makes (read its
  docstring). The harness, the graders, the costs and every decision run for
  real on those replies.
- **Live**: `cp .env.example .env`, add your key. Every step then calls the
  models in `.env`. Your numbers will differ from the slides (those are
  Replay's), and from run to run: run each setup twice before you believe it.

Step 7 uses the OpenAI Batch API, which most other OpenAI-compatible endpoints
don't have. Step 8's history of earlier nights (`datasets/drift_history.json`)
was recorded in Replay.

## The steps

| | File | Shows | Watch for |
|---|---|---|---|
| 1 | `step1_pick_a_model.py` | an accuracy floor, three models, cost per completed task | small is cheapest and below the floor: buy medium? |
| 2 | `step2_judge.py` | code for exact fields, an LLM judge with a rubric for the sentence | large r09: the word check said wrong, the judge says right |
| 3 | `step3_calibrate.py` | the judge against a person's grades | r23: "unknown" → a rule the rubric was missing |
| 4 | `step4_read_failures.py` | failures grouped by kind and field | 4 of 5 failures: a root cause for a report that has none |
| 5 | `step5_fix_the_prompt.py` | prompt v2: when null applies, quote first, final severity | small · v2 clears the floor: the cheapest model wins |
| 6 | `step6_smoke_eval.py` | 8 cases on every PR, a threshold, exit code 1 | `--prompt v1`: 62%, merge blocked |
| 7 | `step7_batch.py` | the full suite as one batch, keyed by custom_id | results out of order; half the price |
| 8 | `step8_drift.py` | a 5% nightly sample, judged, alert at 2 standard deviations | night 14: "P2" is not a severity |

Steps 2–5 grade the answers that step 1 saved in `runs/`, so run the steps in
order once. The judge's grades are cached in `runs/judge_cache.json`: grading
the same answer twice costs nothing.

```
evals/
  llm.py          chat() and the batch calls: the only code that talks to the model
  models.py       the ladder (small, medium, large), prices, cost()
  prompts.py      every prompt and rubric of the lesson, in order: diff them
  graders.py      exact, loose, the LLM judge, with_judge()
  harness.py      run, grade, report, cheapest: what an eval tool does, small
  traffic.py      generated "production" reports for step 8
  replay.py       the scripted models and judge for Replay mode
  datasets/
    golden.json        24 labeled cases: 14 typical, 5 multi_service, 5 open
    hand_labels.json   a person's grades of step 1's small model, for step 3
    drift_history.json scores of nights 1–13, for step 8
  runs/           one JSON file per run (created when you run the steps)
.github/workflows/smoke-eval.yml   step 6 in CI
slides/           the slides
```

## The smoke eval in CI

`.github/workflows/smoke-eval.yml` runs step 6 on every pull request with
`EVAL_MODE=live`, comments the result on the PR, then fails the check if the
score is under the threshold. Add `OPENAI_API_KEY` as a repository secret, then
make `smoke-eval` a required status check in the branch protection rule for
`main`. Move the folder to the repository root, or fix the paths, if this
project lives in a subfolder.
