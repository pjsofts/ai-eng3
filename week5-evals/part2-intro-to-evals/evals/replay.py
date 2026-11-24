"""Replay mode: plays the models and the judge, with no key and no network.

Each model answers from the expected answer, in its own words, with the
mistakes a model of that size really makes with that prompt:

    small · v1    picks the first severity it sees (r06), and writes a root
                  cause for reports that have none (r21-r24)
    small · v2    the prompt fixes both
    medium/large  right, though large words r09 so differently that the
                  step 1 word-overlap check calls it wrong

The judge reads the report the way the rubric says. Replay knows the expected
answers so it can play the judge; the real judge never sees them.

Every grader, the harness, the costs and the decisions run for real on these
replies: the numbers you see are computed, not written down.
"""
import hashlib
import json
import random
import re

from llm import Reply
from models import LADDER
from prompts import EXTRACT_V1, EXTRACT_V2, RUBRIC_FULL, RUBRIC_V2

NO_RECORDING = "Replay has no recorded answer for this input. Set EVAL_MODE=live in .env to ask a real model."

# A model's own wording of the root cause, where it differs from the label.
WORDING = {
    ("medium", "r01"): "The checkout load balancer's TLS certificate expired.",
    ("large", "r01"): "The TLS certificate on checkout's load balancer expired after its renewal job was disabled.",
    ("medium", "r07"): "The carrier changed its label API response format without notice.",
    ("large", "r09"): "Pool limit dropped to five after a bad configuration deploy.",
    ("large", "r13"): "DNS for the push gateway was changed to the old cluster, which was shut down.",
    ("medium", "r16"): "Two search nodes were drained for maintenance and never replaced.",
}

MISTAKES = {
    ("small", "v1", "r06"): {"severity": "sev1"},
    ("small", "v1", "r21"): {"root_cause": "The certificate renewal planned for Friday."},
    ("small", "v1", "r22"): {"root_cause": "The checkout pods needed a restart."},
    ("small", "v1", "r23"): {"root_cause": "The cache layer (suspected, not confirmed)."},
    ("small", "v1", "r24"): {"root_cause": "A queue backlog delayed SMS messages."},
}


def chat(model, system, user, schema=None):
    if schema:
        text = json.dumps(judge(user))
    elif system in (EXTRACT_V1, EXTRACT_V2):
        text = extract(tier_of(model), "v1" if system == EXTRACT_V1 else "v2", user)
    else:
        text = NO_RECORDING
    return Reply(text, (len(system) + len(user)) // 4, len(text) // 4)


# ---- the models -------------------------------------------------------------

def extract(tier, version, report):
    found = lookup(report)
    if found is None:
        return NO_RECORDING
    case_id, truth = found
    answer = dict(truth)
    if case_id.startswith("t"):
        answer.update(traffic_slip(tier, version, report, truth))
    else:
        answer["root_cause"] = WORDING.get((tier, case_id), truth["root_cause"])
        answer.update(MISTAKES.get((tier, version, case_id), {}))
    text = json.dumps(answer)
    if version == "v2":
        text = f"<source>{quote(report, answer['root_cause'])}</source>\n{text}"
    return text


def traffic_slip(tier, version, report, truth):
    """Production: about 1 report in 25 loses its root cause, and the new
    status-page reports keep their "P1" instead of a severity."""
    changes = {}
    if "Priority: P" in report:
        changes["severity"] = re.search(r"Priority: (P\d)", report).group(1)
    if truth["root_cause"] and int(hashlib.sha1(report.encode()).hexdigest(), 16) % 25 == 0:
        changes["root_cause"] = None
    return changes


def quote(report, cause):
    if cause is None:
        return "none"
    wanted = set(re.findall(r"[a-z]{4,}", cause.lower()))
    lines = [line for line in report.splitlines() if line and not line.startswith("#")]
    return max(lines, key=lambda line: len(wanted & set(re.findall(r"[a-z]{4,}", line.lower()))))


# ---- the judge --------------------------------------------------------------

def judge(user):
    report = between(user, "report").strip() + "\n"
    answer = json.loads(between(user, "answer"))
    rubric = between(user, "rubric").strip()
    found = lookup(report)
    if found is None:
        return {"explanation": NO_RECORDING, "verdict": "unknown"}
    case_id, truth = found
    if rubric == RUBRIC_FULL.strip():
        return judge_full(case_id, truth, answer)
    return judge_root_cause(case_id, truth["root_cause"], answer, strict=rubric == RUBRIC_V2.strip())


def judge_root_cause(case_id, expected, answer, strict):
    if expected is None and answer is None:
        return verdict("correct", "The report states no cause, and the answer is null.")
    if expected is None and "not confirmed" in answer and not strict:
        return verdict("unknown", "The report names a suspected cause but says it is not confirmed. "
                                  "The rubric does not say whether that counts.")
    if expected is None:
        return verdict("incorrect", "The report states no root cause. The answer names one the report does not state.")
    if answer is None:
        return verdict("incorrect", "The report states a cause, but the answer is null.")
    if answer in accepted(case_id, expected):
        return verdict("correct", "The answer names the same cause the report states.")
    return verdict("incorrect", "The answer names a different cause from the one the report states.")


def judge_full(case_id, truth, answer):
    if answer.get("severity") not in ("sev1", "sev2", "sev3"):
        return verdict("incorrect", f"severity is {answer.get('severity')!r}, which is not sev1, sev2 or sev3.")
    if answer.get("service") != truth["service"]:
        return verdict("incorrect", "The service is not the one where the incident happened.")
    if answer.get("severity") != truth["severity"]:
        return verdict("incorrect", "The severity does not match the report.")
    if (answer.get("root_cause") is None) != (truth["root_cause"] is None):
        return verdict("incorrect", "The report states a cause, but root_cause is null."
                       if answer.get("root_cause") is None else "root_cause names a cause the report does not state.")
    return verdict("correct", "All three fields match the report.")


def accepted(case_id, expected):
    return {expected} | {text for (tier, cid), text in WORDING.items() if cid == case_id}


def verdict(kind, why):
    return {"explanation": why, "verdict": kind}


def between(text, tag):
    return text.split(f"<{tag}>")[1].split(f"</{tag}>")[0]


# ---- batches ----------------------------------------------------------------

BATCHES = {}


def submit_batch(requests):
    batch_id = f"batch_replay_{len(BATCHES) + 1}"
    BATCHES[batch_id] = requests
    return batch_id


def collect_batch(batch_id):
    requests = list(BATCHES.get(batch_id, []))
    random.Random(5).shuffle(requests)                # results come back in any order
    replies = {r["custom_id"]: chat(r["model"], r["system"], r["user"]) for r in requests}
    return "completed", {"total": len(requests), "completed": len(requests), "failed": 0}, replies


# ---- lookups ----------------------------------------------------------------

def tier_of(model_id):
    return next((m.tier for m in LADDER if m.id == model_id), "large")


_INDEX = {}


def lookup(report):
    """(case id, expected answer) for a golden case or a generated traffic report."""
    if not _INDEX:
        from harness import load_cases
        import traffic
        for case in load_cases():
            _INDEX[case["report"]] = (case["id"], case["expected"])
        for n in range(1, 31):
            for i, item in enumerate(traffic.night(n)):
                _INDEX.setdefault(item["report"], (f"t{n}_{i}", item["truth"]))
    return _INDEX.get(report)
