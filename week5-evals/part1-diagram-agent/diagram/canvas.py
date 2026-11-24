# canvas.py — what the user sees, and how the model reads it.
#
#   draw(elements)       -> the elements Excalidraw really puts on the canvas
#   summarize(elements)  -> a short text the model can read (not JSON)
#
# draw() stands in for Excalidraw's convertToExcalidrawElements. In the real
# app the browser runs it and we don't control it. It reads only two things:
#   label: {"text": ...}           on a shape: a label centred inside it
#   start: {"id"}, end: {"id"}     on an arrow: the shapes it is attached to
# Everything else that looks like a label or a binding is dropped, without a
# warning: `text` on a rectangle, `containerId`, `startBinding`, `endBinding`.

SHAPES = ("rectangle", "ellipse", "diamond")
ARROWS = ("arrow", "line")
DROPPED = ("containerId", "startBinding", "endBinding", "boundElements")


def draw(elements):
    """The elements on the canvas after Excalidraw reads the model's input."""
    drawn = []
    for element in elements:
        element = without_nulls(element)
        label = element.pop("label", None)
        start = element.pop("start", None)
        end = element.pop("end", None)
        for name in DROPPED:
            element.pop(name, None)
        if element.get("type") != "text":
            element.pop("text", None)        # text on a shape draws nothing

        if element.get("type") in ARROWS:
            if start:
                element["startBinding"] = {"elementId": start["id"]}
            if end:
                element["endBinding"] = {"elementId": end["id"]}

        drawn.append(element)
        if label and label.get("text"):      # the label is its own text element
            drawn.append(label_for(element, label["text"]))
    return drawn


def label_for(parent, text):
    """The text element Excalidraw creates for a label, bound to its parent."""
    parent["boundElements"] = [{"id": parent["id"] + "_label", "type": "text"}]
    return {"id": parent["id"] + "_label", "type": "text", "text": text,
            "x": parent["x"], "y": parent["y"],
            "width": parent["width"], "height": parent["height"],
            "containerId": parent["id"]}


def without_nulls(value):
    """A copy without the null fields: null means "use the default"."""
    if isinstance(value, dict):
        return {key: without_nulls(v) for key, v in value.items() if v is not None}
    if isinstance(value, list):
        return [without_nulls(v) for v in value]
    return value


# ---- the canvas, as text for the model (step 3) ----------------------------

def summarize(elements):
    """One line per element. Arrows name the shapes they connect.
    Much shorter than the JSON, and it is what the model needs to know."""
    if not elements:
        return "The canvas is empty."
    labels = labels_by_id(elements)
    lines, counts = [], {}
    for element in elements:
        if element.get("containerId"):
            continue                          # a label: shown on its shape
        kind = element["type"]
        counts[kind] = counts.get(kind, 0) + 1
        if kind in ARROWS:
            start = name_of(element.get("startBinding"), labels)
            end = name_of(element.get("endBinding"), labels)
            lines.append(f"- {kind} {element['id']}: {start} → {end}")
        else:
            label = labels.get(element["id"])
            text = f' "{label}"' if label else ""
            lines.append(f"- {kind} {element['id']}{text} at ({round(element['x'])}, "
                         f"{round(element['y'])}) {round(element['width'])}x{round(element['height'])}")
    total = ", ".join(f"{n} {kind}{'s' if n > 1 else ''}" for kind, n in counts.items())
    return f"The canvas has {total}:\n" + "\n".join(lines)


def labels_by_id(elements):
    """Each element's visible text: its bound label, or its own text."""
    labels = {}
    for element in elements:
        if element.get("type") == "text" and element.get("containerId"):
            labels[element["containerId"]] = element["text"]
        elif element.get("text"):
            labels.setdefault(element["id"], element["text"])
    return labels


def name_of(binding, labels):
    if not binding:
        return "(nothing)"
    shape = binding["elementId"]
    return f'{shape} ("{labels[shape]}")' if shape in labels else shape
