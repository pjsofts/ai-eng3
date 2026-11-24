# Week 5 · AI Engineering: evals and the diagram agent · live visualizer + slides

*Build it. Measure it. Then check the measure.* Eight small steps of plain
Python, no framework: a diagram agent that draws on an Excalidraw canvas, a
golden dataset, scorers, and the improvement loop, including the moment the
eval turns out to be lying.

Ported from the `complete` branch of `ai-engineering-fundamentals/` (lessons 2,
4, 5, 6, 7 and 8; the TypeScript, Cloudflare and Braintrust parts become plain
Python). RAG (lesson 9) is week 7.

Pick a step, press **Enter**, and watch it run: the diagram lights up each
function, the code view highlights the line that is running, and the **Data**
panel shows the conversation the model sees, **the canvas the agent drew**,
one row per eval case with its scores (click a diagram to see it big), and
the comparison with the previous experiment.

The code in `diagram/` is plain Python with no tracing in it. Every step also
runs on its own:

```bash
cd diagram && python step3_context.py
```

## Run it

Requires Python 3.11+.

```bash
cd week5-evals/part1-diagram-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # openai, python-dotenv
cp .env.example .env          # only needed for Live mode
python server.py              # → http://127.0.0.1:8769
```

The slides are served by the same server at **http://127.0.0.1:8769/slides/**
(or open `slides/index.html` directly). `←` `→` to move, `F` fullscreen, `PDF` to print.
Slides marked **▶ Demo · Step N** are where you switch to the visualizer.

## Replay vs Live

- **Replay** (default) needs no key and no network. The model's replies are
  scripted for the dataset cases, but **the tools, `draw()` and every scorer
  run for real**: the scores are computed, not written down. Each step's
  scripted model draws in that step's vocabulary, with that step's mistakes
  (see `replay.py`). Other inputs ask you to switch to Live.
- **Live** calls `MODEL` from `.env` (any OpenAI-compatible endpoint) on every
  case. Your numbers will differ from the slides (those are Replay's), and
  from run to run. That is the point of step 1's pass@k / pass^k slide:
  watch the *direction* a score moves, not the digits.

In the eval steps the first case plays at the chosen speed, the rest fast
forward (`FIRST_CASE_ONLY` in `server.py`).

## The steps

| | File | Shows | Watch for |
|---|---|---|---|
| 0 | `step0_first_agent.py` | one big tool, a friendly prompt | “Done!”: empty boxes, red dashed arrows |
| 1 | `step1_eval_harness.py` | golden dataset, a loop, `results/*.json`, a 1–5 rubric | score the table yourself |
| 2 | `step2_scorers.py` | scorers, `run_eval`, the baseline experiment | preservation 0% |
| 3 | `step3_context.py` | a real prompt + the canvas as text | the comparison with step 2 |
| 4 | `step4_tools.py` | query / add / update / remove, schema descriptions | connectivity *drops*: read the modify-add row |
| 5 | `step5_lying_eval.py` | score what was sent vs what is drawn | 100% vs 0% on the same run |
| 6 | `step6_honest_eval.py` | label / start / end + the eval runs `draw()` | same digits as step 4, now true |
| 7 | `step7_overlaps.py` | `find_overlaps` for agent and eval, `golden_2.json` | create-long-labels: add → overlaps → update |

The eval steps compare themselves with the step before, so run them in order
once (Replay experiments are already in `diagram/experiments/`).

Shared code:

```
diagram/
  llm.py        chat(): the only code that talks to the model (a tool can bring its own schema)
  agent.py      run_agent(): the week 1 loop, unchanged all week
  canvas.py     draw(): what Excalidraw really draws; summarize(): the canvas as text
  tools.py      CANVAS, and the tools that draw on it
  schemas.py    what a tool call may contain: NAIVE, RUNTIME, SKELETON
  prompts.py    every system prompt of the week, in order: diff them
  scorers.py    schema, structure, preservation, label_keywords, bound_arrows,
                connectivity, tool_choice, bound_labels, no_overlaps
  overlaps.py   find_overlaps(): one check for the agent and the eval
  evals.py      load_dataset, run_eval, compare: what Braintrust does, small
  datasets/     golden.json (frozen), golden_2.json (honest seeds + layout stress)
  experiments/  one JSON file per run_eval: the history you compare against
catalog.py   titles, example inputs and the diagram of each step
replay.py    scripted model replies for Replay mode
server.py    runs a step under sys.settrace and streams events (SSE)
ui/          the visualizer page (it draws the canvas the way Excalidraw does)
slides/      the slides
```

You can edit the files in `diagram/` while the server is running. Each run reloads them.

## On stage

Same keys as the other weeks: `Enter` run, `S` step mode, `Space` next,
`↑` `↓` change step, `-` `=` speed, `1` `2` `3` layout, `[` `]` code file,
`D` Data / Trace panel, `L` hide it, `T` theme, `?` help. Click any diagram in
the eval table to open it big; `Esc` closes it.

Good live moments:
- Step 0: the agent says “Done!”, then the canvas: three empty boxes.
- Step 1: ask the room to score create-org from 1 to 5. Compare answers.
- Step 2 → 3: preservation 0% → 100%. Open modify-color in both.
- Step 4: connectivity goes *down*. Click modify-add: the dataset's own arrow was never attached.
- Step 5: two canvases side by side. “Which one is the product?”
- Step 6: the comparison shows no change. Ask why that is still progress.
- Step 7: open create-long-labels in the Trace: the overlaps in the tool result, then the fix.
