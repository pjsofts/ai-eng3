# tools.py — the canvas, and the tools the agent uses to draw on it.
#
# In the real app the canvas lives in the browser. Here it is one list:
# CANVAS. The tools change it, and the evals score what is in it.
#
#   steps 0-3   generate_diagram, modify_diagram       two big, naive tools
#   steps 4-7   query_canvas, add_elements,            small tools, one job each
#               update_elements, remove_elements
from canvas import draw, summarize, without_nulls
from schemas import ADD_SKELETON, GENERATE, MODIFY, REMOVE, UPDATE

CANVAS = []   # the elements on the canvas


def new_canvas(elements=()):
    """Start from an empty canvas, or from the elements a test case gives."""
    CANVAS[:] = [dict(element) for element in elements]


def find(element_id):
    return next((e for e in CANVAS if e.get("id") == element_id), None)


# ---- steps 0-3: two big tools -----------------------------------------------

def generate_diagram(elements):
    """Generate a complete diagram as a list of Excalidraw elements. Use this when
    the user asks you to create, draw or design a new diagram. Return all the
    elements: shapes, text labels, and arrows connecting them."""
    CANVAS[:] = elements
    return f"Drew {len(elements)} elements."


def modify_diagram(element_id, updates):
    """Change one existing element on the canvas, by its id."""
    element = find(element_id)
    if element is None:
        return f"Error: there is no element {element_id}"
    element.update(without_nulls(updates))
    return f"Updated {element_id}."


generate_diagram.schema = GENERATE
modify_diagram.schema = MODIFY


# ---- steps 4-7: small tools, one job each ------------------------------------

def query_canvas():
    """Read what is on the canvas now: every element's id, type, position and
    label. Call this before you change or add to an existing diagram."""
    return summarize(CANVAS)


def add_elements(elements):
    """Add new elements to the canvas.

    To label a shape, set its label: {"text": "Login"}. Do NOT create a separate
    text element to label a shape. To connect two shapes, set start: {"id": ...}
    and end: {"id": ...} on the arrow. The shapes must be in this call or on
    the canvas already.

    Example: [
      {"type": "rectangle", "id": "rect_user", "x": 100, "y": 100, "width": 240, "height": 100, "label": {"text": "User"}},
      {"type": "rectangle", "id": "rect_api", "x": 420, "y": 100, "width": 240, "height": 100, "label": {"text": "API"}},
      {"type": "arrow", "id": "arrow_user_api", "x": 340, "y": 150, "width": 80, "height": 0,
       "start": {"id": "rect_user"}, "end": {"id": "rect_api"}}]"""
    drawn = draw(elements)        # what Excalidraw really puts on the canvas
    CANVAS.extend(drawn)
    return {"added": len(drawn)}


def update_elements(updates):
    """Change existing elements by id: move, resize or recolor them.
    Only use ids that are on the canvas. Call query_canvas first if unsure."""
    changed = []
    for update in updates:
        element = find(update["id"])
        if element:
            element.update(without_nulls(update["fields"]))
            changed.append(update["id"])
    return {"updated": changed}


def remove_elements(ids):
    """Delete elements from the canvas by id."""
    CANVAS[:] = [e for e in CANVAS if e.get("id") not in ids]
    return {"removed": ids}


add_elements.schema = ADD_SKELETON
update_elements.schema = UPDATE
remove_elements.schema = REMOVE
