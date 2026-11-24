# Week 1 · Your first agent: live visualizer

An AI agent built from an empty file in ten small steps of plain Python, with
no framework. Pick a step, press **Enter**, and watch it run: the diagram lights
up each function, the code view highlights the line that is running, and the
**Data** panel shows the conversation the model sees, eval scores and token counts.

The code in `agent/` is plain Python with no tracing in it. Every step also runs
on its own:

```bash
cd agent && python step4_agent_loop.py
```

## Run it

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # openai, python-dotenv
cp .env.example .env          # only needed for Live mode
python server.py              # → http://127.0.0.1:8768
```

The slides are served by the same server at **http://127.0.0.1:8768/slides/**
(or open `slides/index.html` directly). `←` `→` to move, `F` fullscreen, `PDF` to print.
Slides marked **▶ Demo · Step N** are where you switch to the visualizer.

## Replay vs Live

- **Replay** (default) needs no key and no network. The model's replies are
  recorded from real gpt-4o-mini runs of the example inputs. **The tools still
  run for real**, so files change, and shell output and code results are real.
  Other inputs get a simple keyword script, or a message asking you to switch to Live.
- **Live** calls `MODEL` from `.env` (any OpenAI-compatible endpoint). Step 7 also
  needs `SEARCH_MODEL`, a model with built-in web search: `gpt-4o-mini-search-preview`
  on OpenAI, or `openai/gpt-4o-mini:online` on OpenRouter.

The agent can only touch `agent/workspace/`. It is copied fresh from
`agent/sample_workspace/` before every run in the visualizer.

## The steps

| | File | Adds | Try |
|---|---|---|---|
| 1 | `step1_just_an_llm.py` | one LLM call: no tools, no loop, no memory | it can't tell the time |
| 2 | `step2_one_tool_call.py` | one tool, three acts: ask, run, ask again | `What is the capital of France?` (no tool) |
| 3 | `step3_single_turn_evals.py` | golden / secondary / negative cases and scorers | add a case: `prompt -> tool` |
| 4 | `step4_agent_loop.py` | **the loop**; the model decides when to stop | count the LLM calls |
| 5 | `step5_multi_turn_evals.py` | mocked tools, tool order, an LLM judge | `mid-conversation` |
| 6 | `step6_file_tools.py` | list / read / write / delete, errors as text | `Read secrets.txt`, `Read ../tools.py` |
| 7 | `step7_web_search.py` | web search, and when not to search | `What is the capital of France?` |
| 8 | `step8_context.py` | count tokens, compact at 80% | watch the gauge in the Data panel |
| 9 | `step9_shell_and_code.py` | `run_command`, `execute_code` | `How many lines does each file in notes/ have?` |
| 10 | `step10_human_approval.py` | risky tools wait for your yes | answer No, then Yes |

Shared code: `llm.py` (the only code that talks to the model), `tools.py`,
`agent.py` (the step 4 loop as a function, used by steps 5–9), `scorers.py`,
`past_conversation.py` (the long history for step 8).

`diff agent/step4_agent_loop.py agent/step10_human_approval.py` is the whole
lesson of step 10: the same loop, plus one `if`.

## On stage

Same keys as the week 7 and workflows pages: `Enter` run, `S` step mode, `Space` next,
`↑` `↓` change step, `-` `=` speed, `1` `2` `3` layout, `[` `]` code file,
`D` Data / Trace panel, `L` hide it, `T` theme, `?` help.
In step 10, the `input()` call becomes a dialog: **`Y`** yes, **`N`** no.

Good live moments:
- Step 1, then step 2 with the same question: the tool is the difference.
- Step 3: one case fails (`Remove the old todo.txt` → `list_files`). Is the model wrong, or the test?
- Step 4: open the Data panel. The conversation grows with every turn of the loop.
- Step 6 with `Read ../tools.py`: the path check refuses, and the model explains.
- Step 8: 14 messages ≈ 1,080 tokens → over 800 → compacted to 2 messages, and the answer is still right.
- Step 10: say No. The model is told, and tells you.

## Files

```
agent/       what the audience sees
  llm.py       ask / ask_json / chat / search_web
  tools.py     the tools: plain functions, docstrings are the instructions
  agent.py     run_agent(): the loop from step 4
  scorers.py   eval scorers for steps 3 and 5
  step*.py     the ten steps
  sample_workspace/   the files the agent works on
catalog.py   titles, example inputs and the diagram of each step
replay.py    recorded replies for Replay mode
server.py    runs a step under sys.settrace and streams events (SSE)
ui/          the visualizer page
slides/      the slides
```

You can edit the files in `agent/` while the server is running. Each run reloads them.
