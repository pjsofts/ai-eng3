# schemas.py — what the model may put in a diagram tool call.
#
# The schema is part of the prompt: the model reads every field name and
# every description. This week it changes three times:
#
#   NAIVE     steps 0-3   any element, any field. Labels and arrows are a guess.
#   RUNTIME   steps 4-5   containerId and startBinding, with strict descriptions.
#                         These are the names Excalidraw uses AFTER it draws.
#   SKELETON  steps 6-7   label and start/end: the names Excalidraw READS.


def obj(required=(), **properties):
    return {"type": "object", "properties": properties, "required": list(required)}


def num(description=""):
    return {"type": "number", "description": description}


def text(description=""):
    return {"type": "string", "description": description}


def one_of(*names):
    return {"type": "string", "enum": list(names)}


def list_of(item, description=""):
    return {"type": "array", "items": item, "description": description}


POSITION = {
    "x": num("X position in pixels"),
    "y": num("Y position in pixels"),
    "width": num("Width in pixels"),
    "height": num("Height in pixels"),
}
STYLE = {
    "strokeColor": text("Line color, like #1e1e1e"),
    "backgroundColor": text("Fill color, like #fa5252, or transparent"),
}
BASE = ("id", "type", "x", "y", "width", "height")

# ---- NAIVE: the first agent (steps 0-3) -------------------------------------

NAIVE_ELEMENT = obj(
    BASE,
    id=text("Unique identifier"),
    type=one_of("rectangle", "ellipse", "diamond", "text", "arrow", "line"),
    **POSITION, **STYLE,
    text=text("Text content (for text elements)"),
    startBinding=obj(["elementId"], elementId=text()),
    endBinding=obj(["elementId"], elementId=text()),
)

GENERATE = obj(["elements"], elements=list_of(NAIVE_ELEMENT, "Every element of the diagram"))

MODIFY = obj(
    ["element_id", "updates"],
    element_id=text("The id of the element to change"),
    updates=obj(**POSITION, **STYLE, text=text()),
)

# ---- RUNTIME: strict descriptions, the wrong field names (steps 4-5) ----------

RUNTIME_ELEMENT = obj(
    BASE,
    id=text("Concise, meaningful and unique, like rect_login or arrow_login_db."),
    type=one_of("rectangle", "ellipse", "diamond", "text", "arrow", "line"),
    **POSITION, **STYLE,
    text=text("REQUIRED for text elements. FORBIDDEN on shapes: text on a rectangle "
              "draws nothing. Label a shape with a separate text element."),
    containerId=text("Text elements only: the id of the shape this label sits INSIDE. "
                     "This is the ONLY way to label a shape."),
    startBinding=obj(["elementId"], elementId=text(
        "REQUIRED on an arrow that connects two shapes: the shape it starts at. "
        "Without it the arrow floats free, which is always a bug.")),
    endBinding=obj(["elementId"], elementId=text("REQUIRED on a connecting arrow: the shape it ends at.")),
)

ADD_RUNTIME = obj(["elements"], elements=list_of(RUNTIME_ELEMENT, "New elements to add"))

# ---- SKELETON: the names Excalidraw reads (steps 6-7) ------------------------

LABEL = obj(["text"], text=text("The text shown inside the shape, or on the arrow"))
ENDPOINT = obj(["id"], id=text("The id of a shape in this call or already on the canvas"))

SHAPE = obj(BASE, id=text("Like rect_login"), type=one_of("rectangle", "ellipse", "diamond"),
            **POSITION, **STYLE,
            label=dict(LABEL, description="The ONLY way to put text inside a shape."))
ARROW = obj(BASE + ("start", "end"), id=text("Like arrow_login_db"), type=one_of("arrow", "line"),
            **POSITION, **STYLE, start=ENDPOINT, end=ENDPOINT,
            label=dict(LABEL, description="Optional, short: yes, no, 1. login"))
NOTE = obj(BASE + ("text",), id=text(), type=one_of("text"), **POSITION, **STYLE,
           text=text("A floating note. Never use this to label a shape."))

ADD_SKELETON = obj(["elements"], elements=list_of({"anyOf": [SHAPE, ARROW, NOTE]}, "New elements to add"))

# ---- the other canvas tools (steps 4-7) -------------------------------------

UPDATE = obj(["updates"], updates=list_of(obj(
    ["id", "fields"],
    id=text("The id of an element on the canvas"),
    fields=obj(**POSITION, **STYLE),
)))

REMOVE = obj(["ids"], ids=list_of(text(), "Ids of elements on the canvas"))
