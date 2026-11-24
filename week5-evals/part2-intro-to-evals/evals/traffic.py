# traffic.py — stand-in for production: the reports that arrive each night (step 8).
#
#   night(n) -> [{"report": ..., "truth": {...}}]   every report filed that night
#
# Generated, so the lesson needs no real logs. Nobody labels production
# traffic: `truth` is here only so Replay can play the model and the judge.
# From night 14 a new status-page tool files some reports with "Priority: P1"
# instead of "Severity: sev1". Nothing in our prompt mentions it. That is drift.
import random

REPORTS_PER_NIGHT = 400
NEW_TOOL_FROM = 14

CAUSES = {
    "checkout": ["a config push lowered the connection pool size", "a feature flag sent traffic to an unscaled service"],
    "payments": ["a vendor API key expired", "a migration locked the transactions table"],
    "search": ["the index rebuild ran out of disk", "a memory leak in the query parser"],
    "auth": ["a deploy rotated the token signing key", "clock skew made tokens look expired"],
    "notifications": ["the email provider rate-limited us", "a DNS change pointed at an old cluster"],
    "shipping": ["the carrier changed its API format", "a timezone bug in label generation"],
}
SYMPTOMS = ["Error rate rose to {n}% for {m} minutes.", "Requests were slow (p95 {n}s) for {m} minutes.",
            "{n}% of requests failed for {m} minutes."]


def night(n):
    rng = random.Random(n)
    reports = []
    for i in range(REPORTS_PER_NIGHT):
        service = rng.choice(sorted(CAUSES))
        level = rng.choice([1, 2, 2, 3, 3, 3])
        cause = rng.choice(CAUSES[service]) if rng.random() > 0.2 else None
        symptom = rng.choice(SYMPTOMS).format(n=rng.randint(2, 40), m=rng.randint(5, 90))
        new_tool = n >= NEW_TOOL_FROM and rng.random() < 0.3
        reports.append({"report": write(n, i, service, level, cause, symptom, new_tool),
                        "truth": {"service": service, "severity": f"sev{level}",
                                  "root_cause": cause[0].upper() + cause[1:] + "." if cause else None}})
    return reports


def write(n, i, service, level, cause, symptom, new_tool):
    because = f"Cause: {cause}." if cause else "Cause: still under investigation."
    if new_tool:
        return f"# {service} incident · filed from the status page\nPriority: P{level}\n{symptom}\n{because}\n"
    return f"# INC-{n:02d}{i:03d} · {service}\nSeverity: sev{level}\n{symptom}\n{because}\n"


def sample(reports, share, seed):
    """A random share of the night's reports: 1-5% is plenty to see a trend."""
    k = max(1, round(len(reports) * share))
    return random.Random(seed).sample(reports, k)
