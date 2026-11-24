# overlaps.py — which boxes sit on top of each other? (step 7)
#
# One function, used in two places:
#   the agent:  add_elements returns the overlaps, so the model can fix them
#   the eval:   the no_overlaps scorer counts them
# If the two disagreed, the agent would fix one thing and the eval grade another.
#
# Not checked: arrows and lines (they cross shapes on purpose), and the label
# inside a shape (it is meant to be there). Arrow labels ARE checked.

EPSILON = 4   # pixels: two boxes that just touch are not overlapping


def find_overlaps(elements):
    """Every pair of element ids whose boxes overlap."""
    boxes = [e for e in elements if can_overlap(e, elements)]
    pairs = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if intersects(a, b):
                pairs.append(sorted([a["id"], b["id"]]))
    return pairs


def can_overlap(element, elements):
    if element.get("type") in ("arrow", "line"):
        return False
    return not is_label_in_a_shape(element, elements)


def is_label_in_a_shape(element, elements):
    parent = next((e for e in elements if e["id"] == element.get("containerId")), None)
    return parent is not None and parent["type"] in ("rectangle", "ellipse", "diamond")


def intersects(a, b):
    return (a["x"] + EPSILON < b["x"] + b["width"] and b["x"] + EPSILON < a["x"] + a["width"] and
            a["y"] + EPSILON < b["y"] + b["height"] and b["y"] + EPSILON < a["y"] + a["height"])


def count_pairs(elements):
    """How many pairs could overlap: the scorer divides by this."""
    n = sum(1 for e in elements if can_overlap(e, elements))
    return n * (n - 1) // 2
