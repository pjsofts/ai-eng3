"""Runs a background-agents step and streams what it does to the browser.

The code in agent/ stays plain Python using the Inngest SDK's ctx.step API.
Here, local_inngest.Engine answers those calls in-process (app.py uses the
real Inngest Dev Server instead), and sys.settrace watches every line. Each
function call, step, LLM call, crash and retry becomes an event sent to the
page over Server-Sent Events. Nothing in this file is shown to the audience.

    python server.py            # then open http://127.0.0.1:8767
"""
import importlib
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
CODE = ROOT / "agent"
UI = ROOT / "ui"
sys.path.insert(0, str(CODE))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

try:
    import llm  # noqa: E402  (decide is wrapped below, before any step imports it)
except Exception:  # no API key: replay still works
    os.environ["OPENAI_API_KEY"] = "missing"
    import llm  # noqa: E402
HAS_KEY = os.environ.get("OPENAI_API_KEY") != "missing"

import inngest  # noqa: E402

import catalog  # noqa: E402
import local_inngest  # noqa: E402
import replay  # noqa: E402

PORT = int(os.environ.get("PORT", 8767))
SPEEDS = {  # seconds to pause per traced line, per replayed LLM call; how much to shorten waits
    "slow": (0.3, 1.8, 1.3),
    "normal": (0.1, 1.0, 1.0),
    "fast": (0.0, 0.3, 0.5),
}
SLEEP_CAP = 6           # a 10 s step.sleep lasts at most this long on stage (seconds)
EVENT_CAP = 20          # a 2 min wait for checkout/recovered: at most this long
ANSWER_CAP = 45         # a 10 min wait for a person: at most this long
SLOW_REPEATS = 3        # a line that runs more often than this is fast-forwarded
QUIET = {"load", "save", "error_rate"}   # tiny file helpers: not traced
RELOAD = ["policy", "checkout", "inbox"]  # reloaded each run, so live edits show up
TEXT_LIMIT = 4000
RUN_IDS = count(1)


class StopRun(Exception):
    pass


def short(value, limit=TEXT_LIMIT):
    if isinstance(value, inngest.Event):
        value = {"event": value.name, "data": value.data}
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + " …"


def parse_scenario(text):
    words = text.lower().split()
    fault = next((word for word in words if word in catalog.FAULTS), None)
    if not fault:
        raise ValueError(f"Type one of: {', '.join(catalog.FAULTS)} (optionally followed by lose-reply)")
    return fault, "lose-reply" in words


# ---------------------------------------------------------------- one run

class Run:
    def __init__(self, name, scenario, mode, step, speed):
        self.name = name
        self.number = int(name[4])
        self.scenario = scenario
        self.graph = catalog.STEPS[name]
        self.nodes = {node["id"]: node for node in self.graph["nodes"]}
        self.edges = {(a, b): by for a, b, by, _ in self.graph["edges"]}
        self.replay = mode == "replay"
        self.step = step
        self.set_speed(speed)
        self.events = queue.Queue()
        self.gate = threading.Event()
        self.stopped = False
        self.crash_requested = False
        self.frames = []           # (function name, node) for every traced call still running
        self.node_stack = []       # diagram nodes currently running, innermost last
        self.last_node = "input"   # where the next edge starts
        self.last_line = None
        self.line_runs = {}
        self.run_id = f"run-{next(RUN_IDS)}"
        self.engine = local_inngest.Engine(self)
        self.started = time.time()

    # ---- plumbing ------------------------------------------------------------

    def set_speed(self, speed):
        self.speed = speed if speed in SPEEDS else "normal"
        self.line_delay, self.llm_delay, self.wait_scale = SPEEDS[self.speed]

    def emit(self, event):
        event["t"] = round(time.time() - self.started, 3)
        self.events.put(event)

    def check(self):
        if self.stopped:
            raise StopRun()
        if self.crash_requested:
            self.crash_requested = False
            raise local_inngest.Crash()

    def pause(self, seconds):
        deadline = time.time() + seconds
        self.wait_until(lambda: time.time() >= deadline)

    def wait_until(self, condition):
        while not condition():
            time.sleep(0.05)
            self.check()

    # ---- the diagram ---------------------------------------------------------

    def match(self, key, value):
        for node in self.graph["nodes"]:
            if node["match"].get(key) == value:
                return node["id"]
        return None

    def enter(self, node, args, memo=False):
        if (self.last_node, node) in self.edges:
            self.emit({"type": "edge", "from": self.last_node, "to": node, "by": self.edges[(self.last_node, node)]})
        self.last_node = node
        self.node_stack.append(node)
        self.emit({"type": "enter", "node": node, "args": args, "memo": memo})
        if self.step and not memo:
            self.emit({"type": "paused", "node": node})
            self.gate.clear()
            while not self.gate.wait(0.1):
                self.check()
            self.emit({"type": "resumed", "node": node})

    def exit(self, node, value, failed=False, memo=False):
        if node in self.node_stack:
            self.node_stack.remove(node)
        self.emit({"type": "exit", "node": node, "value": short(value, 600), "failed": failed, "memo": memo})

    def current_node(self):
        return self.node_stack[-1] if self.node_stack else None

    def show_service(self):
        state = sys.modules["checkout"].load()
        state["error_rate"] = sys.modules["checkout"].error_rate(state)
        self.emit({"type": "service", "state": state})

    def show_inbox(self):
        self.emit({"type": "inbox", "requests": sys.modules["inbox"].load()})

    # ---- called by local_inngest.Engine ---------------------------------------

    def shorten(self, seconds, kind):
        cap = SLEEP_CAP if kind == "sleep" else ANSWER_CAP if seconds >= 300 else EVENT_CAP
        return min(seconds, cap) * self.wait_scale

    def step_start(self, step_id, kind, info=None):
        info = info or {}
        status = {"run": "running", "sleep": "sleeping", "event": "waiting"}[kind]
        self.emit({"type": "step", "id": step_id, "status": status, "info": info,
                   "until": round(info["deadline"] - self.started, 2) if "deadline" in info else None})
        node = self.match("step", step_id.rsplit("-", 1)[0])
        if node:
            shown = {"step id": step_id}
            if kind == "sleep":
                shown["sleep"] = f"{info['seconds']:g} s"
            if kind == "event":
                shown.update({"event": info["event"], "timeout": f"{info['seconds']:g} s"})
                if info["if"]:
                    shown["if"] = info["if"]
            self.enter(node, shown)

    def step_end(self, step_id, value, failed=False):
        self.emit({"type": "step", "id": step_id, "status": "failed" if failed else "done", "value": short(value, 300)})
        node = self.match("step", step_id.rsplit("-", 1)[0])
        if node:
            self.exit(node, value, failed)

    def step_memo(self, step_id, value):
        self.emit({"type": "step", "id": step_id, "status": "memo", "value": short(value, 300)})
        node = self.match("step", step_id.rsplit("-", 1)[0])
        if node:
            self.enter(node, {"step id": step_id}, memo=True)
            self.exit(node, value, memo=True)
        self.pause(0.25 * self.wait_scale)

    def step_retry(self, step_id, error, attempt):
        self.emit({"type": "retry", "id": step_id, "attempt": attempt, "error": f"{type(error).__name__}: {error}"})
        self.show_service()
        self.pause(1.2 * self.wait_scale)

    def function_retry(self, error, attempt):
        self.emit({"type": "retry", "id": None, "attempt": attempt, "error": f"{type(error).__name__}: {error}"})
        self.restarted(crash=False)

    def crashed(self):
        self.frames.clear()
        self.node_stack.clear()
        self.emit({"type": "crash", "saved": list(self.engine.journal)})
        time.sleep(1.5)

    def restarted(self, crash=True):
        sys.settrace(self.tracer)       # a crash raised inside the tracer switches tracing off
        self.last_node = "input"
        self.last_line = None
        self.emit({"type": "restart", "crash": crash})
        time.sleep(0.6)

    # ---- sys.settrace hooks --------------------------------------------------

    def tracer(self, frame, event, arg):
        if event != "call":
            return None
        code = frame.f_code
        if not code.co_filename.startswith(str(CODE)) or code.co_filename.endswith(("llm.py", "client.py")):
            return None
        if code.co_name == "<module>" or code.co_name in QUIET:
            return None
        if code.co_name.startswith("<"):  # generator expressions and lambdas: lines only
            return self.lines_only
        names = code.co_varnames[:code.co_argcount]
        args = {name: short(frame.f_locals.get(name), 300) for name in names if name != "ctx"}
        node = self.match("fn", code.co_name)
        self.frames.append((code.co_name, node))
        if node:
            self.enter(node, args)
        return self.local_tracer

    def local_tracer(self, frame, event, arg):
        if event == "line":
            self.on_line(frame)
        elif event == "return":
            self.emit({"type": "ret", "file": Path(frame.f_code.co_filename).name})
            fn, node = self.frames.pop() if self.frames else (None, None)
            if node:
                self.exit(node, arg)
            if fn in ("read_state", "run_tool", "start_incident"):
                self.show_service()
            if fn in ("ask", "answer"):
                self.show_inbox()
        return self.local_tracer

    def lines_only(self, frame, event, arg):
        if event == "line":
            self.on_line(frame)
        return self.lines_only

    def on_line(self, frame):
        file, line = Path(frame.f_code.co_filename).name, frame.f_lineno
        if self.last_line == (file, line):
            return
        self.last_line = (file, line)
        self.emit({"type": "line", "file": file, "line": line})
        runs = self.line_runs[(file, line)] = self.line_runs.get((file, line), 0) + 1
        if self.line_delay and runs <= SLOW_REPEATS:
            time.sleep(self.line_delay)
        self.check()

    # ---- the run itself ------------------------------------------------------

    def load_step(self):
        for name in RELOAD:
            importlib.reload(importlib.import_module(name))
        return importlib.reload(importlib.import_module(self.name))

    def execute(self):
        self.emit({"type": "start", "workflow": self.name, "mode": "replay" if self.replay else "live",
                   "run_id": self.run_id})
        try:
            fault, lose_reply = parse_scenario(self.scenario)
            module = self.load_step()
            sys.modules["checkout"].start_incident(fault, lose_next_reply=lose_reply)
            sys.modules["inbox"].clear()
            self.show_service()
            self.show_inbox()

            alert = {"service": "checkout", "summary": "checkout error rate is 42%"}
            self.emit({"type": "enter", "node": "input", "args": {"event": "checkout/alert"}})
            self.emit({"type": "exit", "node": "input", "value": short(alert)})
            event = inngest.Event(name="checkout/alert", data=alert)

            sys.settrace(self.tracer)
            try:
                result = self.engine.execute(module.incident_agent._handler, event, self.run_id)
            finally:
                sys.settrace(None)
            if (self.last_node, "output") in self.edges:
                self.emit({"type": "edge", "from": self.last_node, "to": "output", "by": self.edges[(self.last_node, "output")]})
            self.emit({"type": "enter", "node": "output", "args": {}})
            self.emit({"type": "exit", "node": "output", "value": short(result, 600)})
            self.show_service()
            self.emit({"type": "done", "result": short(result)})
        except StopRun:
            self.emit({"type": "stopped"})
        except Exception as error:
            frames = [f for f in traceback.extract_tb(error.__traceback__) if f.filename.startswith(str(CODE))]
            where = frames[-1] if frames else None
            self.emit({"type": "error", "message": f"{type(error).__name__}: {error}",
                       "file": Path(where.filename).name if where else None,
                       "line": where.lineno if where else None,
                       "trace": traceback.format_exc()})
        self.emit({"type": "end"})

    # ---- buttons in the World panel -------------------------------------------

    def world(self, action, query):
        checkout = sys.modules["checkout"]
        if action == "kill":
            self.crash_requested = True
            return
        if action in ("fix_gateway", "fix_quietly"):
            checkout.fix_gateway()
            sent = action == "fix_gateway"
            if sent:
                self.engine.send("checkout/recovered", {"service": "checkout"})
            self.emit({"type": "world", "text": "The payments team fixed the gateway" +
                       (" and sent checkout/recovered" if sent else ", and told nobody (no event)")})
        elif action == "deploy":
            checkout.someone_deploys()
            self.emit({"type": "world", "text": "Another engineer changed checkout (version +1)"})
        elif action == "answer":
            approved = query.get("approved") == "1"
            event = sys.modules["inbox"].answer(query["request"], approved, query.get("reply", ""))
            self.engine.send(event["name"], event["data"])
            self.emit({"type": "world", "text": f"You answered {query['request']}: " +
                       (query.get("reply") or ("yes" if approved else "no")) + " → sent inbox/answered"})
            self.show_inbox()
        self.show_service()


CURRENT = None
CURRENT_LOCK = threading.Lock()


# ---------------------------------------------------------------- the model call

real_decide = llm.decide


def decide(goal, state, notes):
    """Wraps llm.decide so each call shows up in the page, and is answered
    from replay.py without the network in Replay mode."""
    run = CURRENT
    if run is None:
        return real_decide(goal, state, notes)
    node = run.current_node()
    prompt = (f"Goal: {goal}\n\nCheckout right now: {json.dumps(state)}\n\n"
              f"What happened so far:\n" + ("\n".join(notes) or "(nothing yet)"))
    run.emit({"type": "llm_start", "node": node, "request": {"system": llm.SYSTEM, "prompt": prompt}})
    began = time.time()
    if run.replay:
        run.pause(run.llm_delay)
        choice = replay.decide(goal, state, notes, run.number)
    else:
        choice = real_decide(goal, state, notes)
    run.check()
    text = f"{choice['action']}: {choice['reason']}" + (f"\nQuestion: {choice['question']}" if choice.get("question") else "")
    run.emit({"type": "llm_end", "node": node, "reply": {"text": text, "tool_calls": []},
              "seconds": round(time.time() - began, 2)})
    return choice


llm.decide = decide


# ---------------------------------------------------------------- the page's API

def step_files(name):
    """The step file, every agent/ file it imports, then llm.py and client.py."""
    order, todo = [], [name]
    while todo:
        module = todo.pop(0)
        if module in order or not (CODE / f"{module}.py").exists():
            continue
        order.append(module)
        source = (CODE / f"{module}.py").read_text()
        for from_name, import_name in re.findall(r"^(?:from (\w+) import|import (\w+))", source, re.MULTILINE):
            todo.append(from_name or import_name)
    order = [m for m in order if m not in ("llm", "client")] + ["llm", "client"]
    return {f"{m}.py": (CODE / f"{m}.py").read_text() for m in order}


def describe():
    steps = []
    for module, names in catalog.MODULES:
        for name in names:
            meta = dict(catalog.STEPS[name])
            meta["edges"] = [{"from": a, "to": b, "by": by, "label": label} for a, b, by, label in meta["edges"]]
            steps.append({"name": name, "module": module, **meta, "files": step_files(name)})
    return {"workflows": steps, "has_key": HAS_KEY, "model": llm.MODEL,
            "base_url": os.environ.get("OPENAI_BASE_URL", "api.openai.com")}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        query = {key: values[-1] for key, values in parse_qs(url.query).items()}
        if url.path == "/api/workflows":
            return self.send(200, json.dumps(describe(), ensure_ascii=False))
        if url.path == "/api/run":
            return self.stream(query)
        if url.path == "/api/control":
            return self.control(query)
        if url.path == "/slides":
            self.send_response(301)
            self.send_header("Location", "/slides/")
            self.end_headers()
            return
        if url.path.startswith("/slides/"):
            return self.slides(url.path[len("/slides/"):] or "index.html")
        files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
        if url.path in files:
            path = UI / files[url.path]
            kind = {"html": "text/html", "js": "text/javascript", "css": "text/css"}[path.suffix[1:]]
            return self.send(200, path.read_bytes(), f"{kind}; charset=utf-8")
        self.send(404, "not found", "text/plain")

    def slides(self, name):
        folder = (ROOT / "slides").resolve()
        path = (folder / name).resolve()
        if folder not in path.parents or not path.is_file():
            return self.send(404, "not found", "text/plain")
        kinds = {".html": "text/html; charset=utf-8", ".png": "image/png", ".woff2": "font/woff2"}
        self.send(200, path.read_bytes(), kinds.get(path.suffix, "application/octet-stream"))

    def control(self, query):
        run = CURRENT
        action = query.get("action")
        if run:
            if action == "next":
                run.gate.set()
            elif action == "stop":
                run.stopped = True
            elif action == "step":
                run.step = query.get("value") == "1"
                if not run.step:
                    run.gate.set()
            elif action == "speed":
                run.set_speed(query.get("value"))
            else:
                run.world(action, query)
        self.send(200, json.dumps({"ok": True, "running": run is not None}))

    def stream(self, query):
        global CURRENT
        name = query.get("workflow")
        if name not in catalog.STEPS:
            return self.send(400, "unknown step", "text/plain")
        run = Run(name, query.get("task") or catalog.STEPS[name]["example"],
                  query.get("mode", "replay"), query.get("step") == "1", query.get("speed", "normal"))
        with CURRENT_LOCK:
            if CURRENT:
                CURRENT.stopped = True
                time.sleep(0.3)
            CURRENT = run

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        def work():
            global CURRENT
            try:
                run.execute()
            finally:
                if CURRENT is run:
                    CURRENT = None

        threading.Thread(target=work, daemon=True).start()
        try:
            while True:
                try:
                    event = run.events.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n".encode())
                self.wfile.flush()
                if event["type"] == "end":
                    break
        except (BrokenPipeError, ConnectionResetError):
            run.stopped = True


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print(f"Background agents → http://127.0.0.1:{PORT}   (slides: /slides/)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
