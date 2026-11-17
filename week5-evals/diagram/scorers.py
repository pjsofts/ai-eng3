# scorers.py — small functions that turn one agent run into a score from 0 to 1.
#
# Every scorer looks like this:
#     def name(case, output) -> float, or None when it does not apply
# `case` is one test case from the dataset. `output` is what the run produced:
#     {"text": the final answer, "elements": the canvas, "tool_calls": [names]}
# Returning None skips the case, so one scorer only grades the cases it is about.
#
#   step 2:  schema, structure, preservation, label_keywords
#   step 3:  bound_arrows, connectivity
#   step 4:  tool_choice (replaces preservation)
#   step 5:  bound_labels
#   step 7:  no_overlaps
import re

from overlaps import count_pairs, find_overlaps

SHAPES = ("rectangle", "ellipse", "diamond")
TYPES = SHAPES + ("text", "arrow", "line")


def of_type(output, *types):
    return [e for e in output["elements"] if e.get("type") in types]


# ---- step 2 -----------------------------------------------------------------

def schema(case, output):
    """1 if there are elements and every one has the fields a canvas needs."""
    if not output["elements"]:
        return 0.0
    for element in output["elements"]:
        if element.get("type") not in TYPES:
            return 0.0
        if any(field not in element for field in ("id", "x", "y", "width", "height")):
            return 0.0
    return 1.0


NAMES = {"rectangle": ["rectangle", "box"], "ellipse": ["ellipse", "circle"],
         "diamond": ["diamond", "decision"], "arrow": ["arrow"]}


def structure(case, output):
    """Does it have the right number of each type? The case says how many:
    "3 rectangles", "2 arrows". Being off by one costs a little, not everything."""
    wanted = expected_counts(" ".join(case["expected"]))
    if not wanted:
        return None
    scores = []
    for kind, n in wanted.items():
        found = len(of_type(output, kind))
        scores.append(max(0.0, 1 - abs(found - n) / n))
    return sum(scores) / len(scores)


def expected_counts(text):
    """ "3 rectangles and 2 arrows" -> {"rectangle": 3, "arrow": 2} """
    counts = {}
    for kind, words in NAMES.items():
        for word in words:
            for n in re.findall(rf"(\d+) {word}", text.lower()):
                counts[kind] = max(counts.get(kind, 0), int(n))
    return counts


def preservation(case, output):
    """Modify cases: are the elements that should stay still there, same type?"""
    keep = case.get("preserved", [])
    if not keep:
        return None
    seed = {e["id"]: e["type"] for e in case["seed"]["elements"]}
    now = {e["id"]: e["type"] for e in output["elements"]}
    return sum(1 for id in keep if now.get(id) == seed[id]) / len(keep)


def label_keywords(case, output):
    """Are the right words somewhere: in the answer or on the canvas?"""
    keywords = case.get("keywords", [])
    if not keywords:
        return None
    words = [output["text"]] + [e.get("text", "") for e in output["elements"]]
    found = " ".join(words).lower()
    return sum(1 for word in keywords if word.lower() in found) / len(keywords)


# ---- step 3: does it make a picture? ----------------------------------------

def bound_arrows(case, output):
    """Of all arrows, how many are attached to a shape at BOTH ends?"""
    arrows = of_type(output, "arrow")
    if not arrows:
        return None
    ids = {e["id"] for e in output["elements"]}
    attached = [a for a in arrows if attached_to(a, "startBinding", ids) and attached_to(a, "endBinding", ids)]
    return len(attached) / len(arrows)


def attached_to(arrow, end, ids):
    binding = arrow.get(end) or {}
    return binding.get("elementId") in ids


CONNECTED = ("flow", "between", "from", "chart", "sequence", "process")   # a guess: tune it


def connectivity(case, output):
    """For a flow or a chart: how many shapes can you reach from the first one,
    following the arrows? 5 boxes with 2 connected scores 0.4."""
    if not any(word in case["input"].lower() for word in CONNECTED):
        return None
    shapes = [e["id"] for e in of_type(output, *SHAPES)]
    if len(shapes) < 2:
        return None
    neighbours = {id: set() for id in shapes}
    for arrow in of_type(output, "arrow", "line"):
        a = (arrow.get("startBinding") or {}).get("elementId")
        b = (arrow.get("endBinding") or {}).get("elementId")
        if a in neighbours and b in neighbours:
            neighbours[a].add(b)
            neighbours[b].add(a)
    seen, todo = {shapes[0]}, [shapes[0]]
    while todo:
        for next_id in neighbours[todo.pop()] - seen:
            seen.add(next_id)
            todo.append(next_id)
    return len(seen) / len(shapes)


# ---- step 4: the right tool, in the right order -----------------------------

def tool_choice(case, output):
    """create: it must call add_elements.
    modify: it must call query_canvas BEFORE it changes anything."""
    calls = output["tool_calls"]
    if case["category"] in ("create", "domain"):
        return 1.0 if "add_elements" in calls else 0.0
    if case["category"] == "modify":
        changes = [i for i, name in enumerate(calls)
                   if name in ("add_elements", "update_elements", "remove_elements")]
        if not changes:
            return 0.0
        looked = "query_canvas" in calls[:changes[0]]
        return 1.0 if looked else 0.5
    return None


# ---- step 5: is every shape labelled? ---------------------------------------

def bound_labels(case, output):
    """Of all shapes, how many have a text element bound inside them?
    Thin lifelines in a sequence diagram (narrower than 20px) need no label."""
    shapes = [e for e in of_type(output, *SHAPES) if e["width"] >= 20]
    if not shapes:
        return None
    labelled = {e.get("containerId") for e in of_type(output, "text")}
    return sum(1 for shape in shapes if shape["id"] in labelled) / len(shapes)


# ---- step 7: is anything on top of something else? --------------------------

def no_overlaps(case, output):
    """1 minus the share of box pairs that overlap."""
    pairs = count_pairs(output["elements"])
    if pairs == 0:
        return None
    return 1 - len(find_overlaps(output["elements"])) / pairs
