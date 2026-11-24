# Week 4 · Background agents with Inngest: live visualizer

An incident agent for a pretend checkout service, built up in six steps of
plain Python. Pick a step, press **Enter**, and watch it run: the diagram lights
up each step, the code view highlights the line that is running, and the **Run**
panel shows the Inngest journal, checkout's state, and an inbox where you answer
the agent. You play the world: kill the agent, approve, deny, fix the gateway.

The code in `agent/` uses the real Inngest SDK (`ctx.step.run`, `step.sleep`,
`step.wait_for_event`) and has no tracing in it.

## Run it

```bash
cd week4-background-agents
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # only needed for Live mode and app.py
python server.py              # → http://127.0.0.1:8767
```

The slides are served by the same server at **http://127.0.0.1:8767/slides/**
(or open `slides/index.html` directly). `←` `→` to move, `F` fullscreen, `PDF` to print.
Slides marked **▶ Demo · Step N** are where you switch to the visualizer.

## Replay vs Live

- **Replay** (default) needs no key and no network. The model's choices come
  from `replay.py`: look at the logs first, then do what they point at.
- **Live** calls `MODEL` from `.env` (any OpenAI-compatible endpoint).

Either way, the visualizer runs the step's function on `local_inngest.py`, a
small in-process stand-in for Inngest, so every line can be traced. It keeps
Inngest's rules: finished steps are saved, a crash re-runs the function from the
top with saved steps returning instantly, timers survive the crash, and a
failing step is retried. Long waits are shortened on stage (a 10 min approval
timeout becomes 45 s); the journal shows both numbers.

## Run it for real, on Inngest

`app.py` serves the same functions to the real Inngest Dev Server:

```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest   # terminal 1, dashboard → http://127.0.0.1:8288
python app.py 2                                                    # terminal 2: serve step 2
python world.py alert feature                                      # terminal 3: break checkout, send the alert
```

`world.py` is you, playing everyone else: `inbox`, `approve req-1`, `deny req-1`,
`answer req-1 "text"`, `fix-gateway [--quiet]`, `deploy`, `state`,
`alert <fault> [--lose-reply] [--times 3]`. Serve one step at a time: they all
listen to `checkout/alert`. Durability drill: Ctrl-C terminal 2 while the run
sleeps, start it again, and watch the dashboard continue from the last step.

## The steps

| | File | Adds | Try |
|---|---|---|---|
| 1 | `step1_goal_loop.py` | observe → decide → act; `goal_met()` in code; `policy.py` | `release` stops: needs a person. **K** mid-run: starts over |
| 2 | `step2_durable_steps.py` | `ctx.step.run` per piece of work, `step.sleep` | **K** while it sleeps: 6 steps come back ↺, no LLM call repeated |
| 3 | `step3_wait_for_event.py` | `wait_for_event("checkout/recovered")` + timeout, singleton | 🔧 rings the doorbell; 🤫 fixes silently, the timeout notices |
| 4 | `step4_human_approval.py` | inbox + `wait_for_event("inbox/answered")`, re-check version | approve · deny · ignore · 🚀 then approve: the yes goes stale |
| 5 | `step5_safe_retries.py` | `action_id = run:cycle:action` | `feature lose-reply`: once here, **twice** on step 2 |
| 6 | `step6_ask_for_help.py` | `ask_human`; the answer is information → `continue` | answer it: still broken, so it waits; then 🔧 |

Each step is the previous one plus a few lines, so `diff agent/step4_*.py agent/step5_*.py`
is the whole lesson.

Shared code: `checkout.py` (the service, a JSON file in `.data/`), `policy.py`,
`inbox.py`, `llm.py`, `client.py`.

## The scenario (the input box)

`feature`, `release` or `dependency`, optionally followed by `lose-reply`.

- **feature**: the express checkout feature crashes. The agent may turn it off.
- **release**: release v2 broke payments. Rolling back needs a person's yes.
- **dependency**: the payment gateway (another team's) is down. Nothing to fix: wait or ask.
- **lose-reply**: the next change happens, but its reply is lost, so the step is retried.

## On stage

Same keys as week 7: `Enter` run, **`K` kill the agent**, `S` step mode, `Space` next,
`↑` `↓` change step, `-` `=` speed, `1` `2` `3` layout, `[` `]` code file,
`D` Run / Trace panel, `L` hide it, `T` theme, `?` help.

Good live moments:
- Step 1, then step 2, both killed mid-run: count the LLM calls in the status line.
- Step 3 with 🤫: the event never comes, the timeout finds the fix anyway.
- Step 4: press 🚀 while the approval is pending, then approve. It asks again at version 2.
- Step 2 vs step 5 with `feature lose-reply`: look at "Changes made to checkout".
- Step 6: answer "the payments team is on it". It looks again, still broken, and waits.
