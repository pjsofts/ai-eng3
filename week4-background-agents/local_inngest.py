"""A small stand-in for Inngest, used only by the visualizer.

The step files call ctx.step.run / sleep / wait_for_event. In app.py the real
Inngest SDK answers those calls. In the visualizer this file does, so the
function runs inside the page's process and every line can be watched.

It keeps Inngest's promise:
  - every finished step is saved in a journal (step id -> result)
  - when the process dies, the function runs again FROM THE TOP, and every
    step already in the journal returns its saved result instead of running
  - timers and event waits belong to Inngest, not to the process: a crash
    does not restart them
  - a step that raises is retried; a finished step never runs twice

One difference: real Inngest goes back to the top after EVERY step (one HTTP
request per step). This stand-in only does that after a crash, so the page
stays readable.
"""
import json
import logging
import re
import time
from datetime import timedelta
from types import SimpleNamespace

import inngest


class Crash(BaseException):
    """The agent process died (the 💥 button).
    A BaseException, so no `except Exception` in the agent can catch it."""


class Engine:
    def __init__(self, show, retries=3):
        self.show = show          # the visualizer: draws every step, owns the clock
        self.retries = retries
        self.journal = {}         # step id -> saved result. This is what survives a crash.
        self.timers = {}          # step id -> (started, deadline). Inngest holds these, not us.
        self.received = []        # events sent to Inngest: (time, name, data)

    def send(self, name, data):
        self.received.append((time.time(), name, data))

    # ---- running the function ---------------------------------------------------

    def execute(self, handler, event, run_id):
        attempt = 0
        while True:
            ctx = SimpleNamespace(event=event, events=[event], run_id=run_id, attempt=attempt,
                                  step=self, logger=logging.getLogger("agent"))
            try:
                return handler(ctx)
            except Crash:
                self.show.crashed()
                self.show.restarted()            # Inngest calls the function again, from the top
            except Exception as error:           # an error outside any step: retry the function
                if attempt >= self.retries:
                    raise
                attempt += 1
                self.show.function_retry(error, attempt)

    # ---- ctx.step ---------------------------------------------------------------

    def run(self, step_id, handler, *args):
        if step_id in self.journal:
            return self.saved(step_id)

        self.show.step_start(step_id, "run")
        for attempt in range(1, self.retries + 2):
            try:
                result = handler(*args)
                break
            except Exception as error:
                if attempt > self.retries:
                    self.show.step_end(step_id, f"{type(error).__name__}: {error}", failed=True)
                    raise
                self.show.step_retry(step_id, error, attempt)

        self.journal[step_id] = json.loads(json.dumps(result))    # saved as JSON, like Inngest does
        self.show.step_end(step_id, result)
        return self.journal[step_id]

    def sleep(self, step_id, duration):
        if step_id in self.journal:
            return self.saved(step_id)
        seconds = to_seconds(duration)
        started, deadline = self.timer(step_id, self.show.shorten(seconds, "sleep"))
        self.show.step_start(step_id, "sleep", {"seconds": seconds, "deadline": deadline})
        self.show.wait_until(lambda: time.time() >= deadline)
        self.journal[step_id] = None
        self.show.step_end(step_id, "woke up")

    def wait_for_event(self, step_id, *, event, if_exp=None, timeout):
        if step_id in self.journal:
            data = self.saved(step_id)
            return None if data is None else inngest.Event(name=event, data=data)
        seconds = to_seconds(timeout)
        started, deadline = self.timer(step_id, self.show.shorten(seconds, "event"))
        self.show.step_start(step_id, "event", {"event": event, "if": if_exp, "seconds": seconds, "deadline": deadline})

        def arrived():
            # Only events that arrive AFTER the wait started count. Earlier ones are missed.
            for received_at, name, data in self.received:
                if name == event and received_at >= started and matches(if_exp, data):
                    return data
            return None

        self.show.wait_until(lambda: arrived() is not None or time.time() >= deadline)
        data = arrived()
        self.journal[step_id] = data
        self.show.step_end(step_id, f"{event} arrived" if data is not None else "timed out")
        return None if data is None else inngest.Event(name=event, data=data)

    # ---- helpers ----------------------------------------------------------------

    def saved(self, step_id):
        self.show.step_memo(step_id, self.journal[step_id])
        return self.journal[step_id]

    def timer(self, step_id, seconds):
        if step_id not in self.timers:
            now = time.time()
            self.timers[step_id] = (now, now + seconds)
        return self.timers[step_id]


def to_seconds(duration):
    if isinstance(duration, timedelta):
        return duration.total_seconds()
    return duration / 1000          # the SDK takes plain numbers as milliseconds


def matches(if_exp, data):
    """Enough of Inngest's expression language for `async.data.key == 'value'`."""
    if not if_exp:
        return True
    found = re.fullmatch(r"\s*async\.data\.(\w+)\s*==\s*['\"](.*)['\"]\s*", if_exp)
    if not found:
        raise ValueError(f"the local stand-in can't read this if_exp: {if_exp}")
    key, value = found.groups()
    return str(data.get(key)) == value
