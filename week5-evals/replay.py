"""Replay mode: answers every model call without a key or a network.

Each test case has one intended diagram (DIAGRAMS below). Each step's model
draws it in the vocabulary that step's prompt and schema teach, with the
mistakes a model of that step really makes:

    naive     steps 0-2   text on the rectangles, arrows not attached, ids like rect-1
    context   step 3      separate text elements, arrows with startBinding
    runtime   steps 4-5   text with containerId, small tools, query before modify
    skeleton  steps 6-7   label and start/end; step 7 fixes overlaps it is told about

The tools, draw() and every scorer still run for real on these replies, so the
scores you see are computed, not scripted. Other inputs ask you to switch to Live.
"""
from llm import Reply, ToolCall

NO_RECORDING = "(Replay has no recorded answer for this input. Switch to Live (M) to ask the model.)"
ERA = {"step0": "naive", "step1": "naive", "step2": "naive", "step3": "context",
       "step4": "runtime", "step5": "runtime", "step6": "skeleton", "step7": "skeleton"}


class Replay:
    def __init__(self, step):
        self.step = step.split("_")[0]
        self.era = ERA[self.step]
        self.ids = 0

    def chat(self, messages, tools):
        user = [m for m in messages if m["role"] == "user"]
        task = user[-1]["content"]
        turn = sum(1 for m in messages[messages.index(user[-1]):] if m["role"] == "assistant")
        script = self.script(task, has_history=len(user) > 1)
        if script is None:
            return Reply(NO_RECORDING)
        if turn >= len(script):
            return Reply("Done.")
        return self.reply(script[turn])

    def reply(self, turn):
        """A script turn is a string (the answer) or a list of (tool, args)."""
        if isinstance(turn, str):
            return Reply(turn)
        calls = []
        for name, args in turn:
            self.ids += 1
            calls.append(ToolCall(f"call_{self.ids}", name, args))
        return Reply("", calls)

    def script(self, task, has_history):
        key = CASES.get(task.strip())
        if key is None:
            return None
        if key in MODIFY:
            return MODIFY[key](self.era, has_history)
        if key == "edge-vague" and self.era == "naive":
            return ["Sure! What would you like me to draw? A flowchart, an architecture diagram, or something else?"]
        diagram = DIAGRAMS[key](self.era)
        if self.era in ("naive", "context"):
            return [[("generate_diagram", {"elements": naive(diagram) if self.era == "naive" else context(diagram)})],
                    DONE[key]]
        if self.era == "runtime":
            return [[("add_elements", {"elements": runtime(diagram)})], DONE[key]]
        if key == "create-long-labels" and self.step == "step7":
            return LONG_LABELS_WITH_FEEDBACK
        return [[("add_elements", {"elements": skeleton(diagram)})], DONE[key]]


CASES = {
    "Draw a flow from User to API to Database": "user-api-db",
    "Draw a single rectangle labeled Hello": "create-box",
    "Draw a simple flowchart with Start, Process and End boxes connected by arrows": "create-flow",
    "Draw a login flowchart: Login, then a decision \"Password correct?\". Yes goes to Dashboard, no goes to Error.": "create-decision",
    "Draw an org chart: a CEO at the top, 3 VPs below (Engineering, Sales, Marketing), and 2 directors under each VP": "create-org",
    "Draw an architecture, left to right: Web Browser, API / Resource Server, Authentication Service, Primary Database, connected by arrows": "create-long-labels",
    "Draw a 3 by 3 grid of boxes labeled A to I, edge to edge with no gaps": "create-tight-grid",
    "Make the login box red": "modify-color",
    "Add a Cache box between the API and the Database": "modify-add",
    "Draw the OAuth 2.0 authorization code flow": "domain-oauth",
    "draw something": "edge-vague",
}


# ---------------------------------------------------------------- the diagrams
# A diagram is shapes [(id, label, type, x, y, width, height)] and
# arrows [(id, from, to, label)]. Each era turns it into elements below.

def box(id, label, x, y, w=240, h=100, kind="rectangle"):
    return (id, label, kind, x, y, w, h)


def row(*labels, y=100, x=100, stride=320, prefix="rect_"):
    return [box(prefix + key(label), label, x + i * stride, y) for i, label in enumerate(labels)]


def key(label):
    return label.lower().replace(" ", "_").replace("/", "").replace("__", "_").strip("_")


def chain(shapes):
    return [(f"arrow_{key(a[1])}_{key(b[1])}", a[0], b[0], None) for a, b in zip(shapes, shapes[1:])]


def flow(*labels):
    shapes = row(*labels)
    return lambda era: (shapes, chain(shapes))


def decision(era):
    login = box("rect_login", "Login", 260, 100)
    check = box("diamond_password", "Password correct?", 310, 280, 140, 140, "diamond")
    dashboard = box("rect_dashboard", "Dashboard", 100, 500)
    error = box("rect_error", "Error", 420, 500)
    if era == "naive":                          # the decision as a box, not a diamond
        check = box("rect_password", "Password correct?", 260, 280)
    arrows = [("arrow_login_check", login[0], check[0], None),
              ("arrow_yes", check[0], dashboard[0], "yes"),
              ("arrow_no", check[0], error[0], "no")]
    return [login, check, dashboard, error], arrows


ORG = {"Engineering": ["Platform Director", "Product Director"],
       "Sales": ["EMEA Director", "US Director"],
       "Marketing": ["Brand Director", "Growth Director"]}


def org(era):
    ceo = box("rect_ceo", "CEO", 900, 100)
    shapes, arrows = [ceo], []
    for i, (vp, directors) in enumerate(ORG.items()):
        vp_box = box("rect_" + key(vp), "VP " + vp, 260 + i * 640, 280)
        shapes.append(vp_box)
        arrows.append((f"arrow_ceo_{key(vp)}", ceo[0], vp_box[0], None))
        if era == "naive":                      # it gives up halfway: one director each
            directors = directors[:1]
        for j, name in enumerate(directors):
            director = box("rect_" + key(name), name, 100 + (2 * i + j) * 320, 460)
            shapes.append(director)
            arrows.append((f"arrow_{key(vp)}_{key(name)}", vp_box[0], director[0], None))
    return shapes, arrows


def oauth(era):
    user, client = box("rect_user", "User", 100, 100), box("rect_client", "Client app", 100, 400)
    auth = box("rect_auth", "Authorization Server", 740, 400, 280)
    api = box("rect_resource", "Resource Server", 740, 700)
    messages = [(user, client, "1. sign in"), (client, auth, "2. redirect to /authorize"),
                (auth, client, "3. authorization code"), (client, auth, "4. code for an access token"),
                (client, api, "5. API call with the access token")]
    if era == "naive":                          # vaguer from memory: no redirect, no access token
        messages = [(user, client, "1. log in"), (client, auth, "2. ask for login"),
                    (auth, client, "3. authorization code"), (client, api, "4. call the API")]
    elif era == "context":
        messages[1] = (client, auth, "2. send the user to log in")
    arrows = [(f"arrow_{i + 1}", a[0], b[0], label) for i, (a, b, label) in enumerate(messages)]
    return [user, client, auth, api], arrows


def grid(era):
    shapes = [box("rect_" + c.lower(), c, 100 + 120 * (i % 3), 100 + 80 * (i // 3), 120, 80)
              for i, c in enumerate("ABCDEFGHI")]
    return shapes, []


LONG = ["Web Browser", "API / Resource Server", "Authentication Service", "Primary Database"]


def long_labels(x_positions):
    shapes = [box("rect_" + key(label), label, x, 100, max(240, 14 * len(label)))
              for label, x in zip(LONG, x_positions)]
    return shapes, chain(shapes)


def something(era):
    return flow("Idea", "Plan", "Ship")(era)


DIAGRAMS = {
    "user-api-db": flow("User", "API", "Database"),
    "create-box": lambda era: ([box("rect_hello", "Hello", 100, 100)], []),
    "create-flow": flow("Start", "Process", "End"),
    "create-decision": decision,
    "create-org": org,
    "create-long-labels": lambda era: long_labels([100, 420, 794, 1182]),
    "create-tight-grid": grid,
    "domain-oauth": oauth,
    "edge-vague": something,
}

DONE = {
    "user-api-db": "Done! I drew User → API → Database, left to right, connected by arrows.",
    "create-box": "Done: one rectangle labeled Hello.",
    "create-flow": "Done: Start → Process → End, connected by arrows.",
    "create-decision": "Done: Login, then the decision, with yes to Dashboard and no to Error.",
    "create-org": "Done: the CEO, three VPs, and their directors, top to bottom.",
    "create-long-labels": "Done: four services, left to right.",
    "create-tight-grid": "Done: a 3 by 3 grid, A to I, edge to edge.",
    "domain-oauth": "Done: the OAuth 2.0 authorization code flow, one numbered arrow per message.",
    "edge-vague": "I drew a small flow: Idea → Plan → Ship.",
}


# ---------------------------------------------------------------- the eras

def arrow_box(shapes, a, b):
    """Where an arrow from shape a to shape b goes: edge to edge."""
    pos = {s[0]: s for s in shapes}
    _, _, _, ax, ay, aw, ah = pos[a]
    _, _, _, bx, by, bw, bh = pos[b]
    (acx, acy), (bcx, bcy) = (ax + aw / 2, ay + ah / 2), (bx + bw / 2, by + bh / 2)
    if abs(bcx - acx) >= abs(bcy - acy):        # sideways
        x0 = ax + aw if bcx > acx else ax
        x1 = bx if bcx > acx else bx + bw
        return {"x": x0, "y": acy, "width": x1 - x0, "height": bcy - acy}
    y0 = ay + ah if bcy > acy else ay           # up or down
    y1 = by if bcy > acy else by + bh
    return {"x": acx, "y": y0, "width": bcx - acx, "height": y1 - y0}


def naive(diagram):
    """Steps 0-2: what an untrained prompt gets. Labels as `text` on the shape
    (Excalidraw draws nothing), arrows placed by hand and attached to nothing."""
    shapes, arrows = diagram
    short = {"rectangle": "rect", "ellipse": "ellipse", "diamond": "diamond"}
    rename = {s[0]: f"{short[s[2]]}-{i + 1}" for i, s in enumerate(shapes)}
    elements = [{"id": rename[id], "type": kind, "x": x, "y": y, "width": w, "height": h,
                 "text": label, "strokeColor": "#1e1e1e", "backgroundColor": "transparent"}
                for id, label, kind, x, y, w, h in shapes]
    for i, (id, a, b, label) in enumerate(arrows):
        elements.append({"id": f"arrow-{i + 1}", "type": "arrow", **arrow_box(shapes, a, b),
                         "strokeColor": "#1e1e1e"})
        if label:
            place = arrow_box(shapes, a, b)
            elements.append({"id": f"text-{i + 1}", "type": "text", "text": label,
                             "x": place["x"] + place["width"] / 2 + 6, "y": place["y"] + place["height"] / 2 - 10,
                             "width": 14 * len(label), "height": 20})
    return elements


def context(diagram):
    """Step 3: the prompt's rules, in runtime names. A separate text element
    over each shape; arrows with startBinding and endBinding."""
    shapes, arrows = diagram
    elements = []
    for id, label, kind, x, y, w, h in shapes:
        elements.append({"id": id, "type": kind, "x": x, "y": y, "width": w, "height": h})
        elements.append({"id": id.replace("rect_", "text_").replace("diamond_", "text_"), "type": "text",
                         "text": label, "x": x, "y": y, "width": w, "height": h})
    for id, a, b, label in arrows:
        elements.append({"id": id, "type": "arrow", **arrow_box(shapes, a, b),
                         "startBinding": {"elementId": a}, "endBinding": {"elementId": b}})
        if label:
            elements.append({"id": id + "_text", "type": "text", "text": label,
                             **arrow_box(shapes, a, b)})
    return elements


def runtime(diagram, extra_shapes=()):
    """Steps 4-5: what the schema descriptions ask for. Text with containerId,
    arrows with startBinding: the names Excalidraw uses AFTER it draws."""
    shapes, arrows = diagram
    everything = list(shapes) + list(extra_shapes)
    elements = []
    for id, label, kind, x, y, w, h in shapes:
        elements.append({"id": id, "type": kind, "x": x, "y": y, "width": w, "height": h})
        elements.append({"id": id + "_text", "type": "text", "text": label, "containerId": id,
                         "x": x, "y": y, "width": w, "height": h})
    for id, a, b, label in arrows:
        elements.append({"id": id, "type": "arrow", **arrow_box(everything, a, b),
                         "startBinding": {"elementId": a}, "endBinding": {"elementId": b}})
        if label:
            elements.append({"id": id + "_text", "type": "text", "text": label, "containerId": id,
                             **arrow_box(everything, a, b)})
    return elements


def skeleton(diagram, extra_shapes=()):
    """Steps 6-7: label on the shape, start/end on the arrow."""
    shapes, arrows = diagram
    everything = list(shapes) + list(extra_shapes)
    elements = [{"id": id, "type": kind, "x": x, "y": y, "width": w, "height": h, "label": {"text": label}}
                for id, label, kind, x, y, w, h in shapes]
    for id, a, b, label in arrows:
        element = {"id": id, "type": "arrow", **arrow_box(everything, a, b),
                   "start": {"id": a}, "end": {"id": b}}
        if label:
            element["label"] = {"text": label}
        elements.append(element)
    return elements


# ---------------------------------------------------------------- step 7: overlap feedback
# First try: it widens the long labels but keeps the old 280px stride, so
# three boxes collide. The tool result lists the overlaps; it moves them.

LONG_LABELS_WITH_FEEDBACK = [
    [("add_elements", {"elements": skeleton(long_labels([100, 380, 660, 940]))})],
    [("update_elements", {"updates": [
        {"id": "rect_api_resource_server", "fields": {"x": 420}},
        {"id": "rect_authentication_service", "fields": {"x": 794}},
        {"id": "rect_primary_database", "fields": {"x": 1182}}]})],
    "Done: four services, left to right. The first layout overlapped, so I moved three boxes apart.",
]


# ---------------------------------------------------------------- modify cases

CACHE = box("rect_cache", "Cache", 740, 100)


def modify_color(era, has_history):
    if era == "naive" and not has_history:      # step 1: no seed, no canvas
        return ["I don't see a login box on the canvas yet. Should I draw one?"]
    if era == "naive":                          # step 2: it redraws everything, new ids
        return [[("generate_diagram", {"elements": [
            {"id": "rect-1", "type": "rectangle", "x": 100, "y": 100, "width": 240, "height": 100,
             "text": "login", "backgroundColor": "#fa5252"},
            {"id": "rect-2", "type": "rectangle", "x": 420, "y": 100, "width": 240, "height": 100,
             "text": "database"}]})],
                "Done: the login box is red now."]
    if era == "context":                        # step 3: the ids are in the prompt
        return [[("modify_diagram", {"element_id": "rect_login", "updates": {"backgroundColor": "#fa5252"}})],
                "Done: rect_login is red."]
    return [[("query_canvas", {})],
            [("update_elements", {"updates": [{"id": "rect_login", "fields": {"backgroundColor": "#fa5252"}}]})],
            "Done: the login box is red. Nothing else changed."]


def modify_add(era, has_history):
    new = [box("rect_user", "User", 100, 100), box("rect_api", "API", 420, 100), CACHE,
           box("rect_db", "Database", 1060, 100)]
    arrows = [("arrow_api_cache", "rect_api", "rect_cache", None), ("arrow_cache_db", "rect_cache", "rect_db", None)]
    if era == "naive" and not has_history:      # step 1: no canvas, so it draws its own
        return [[("generate_diagram", {"elements": naive((new[1:], chain(new[1:])))})],
                "Done: API → Cache → Database."]
    if era == "naive":                          # step 2: redraws it all, new ids
        return [[("generate_diagram", {"elements": naive((new, chain(new)))})],
                "Done: I added a Cache between the API and the Database."]
    if era == "context":                        # step 3: redraws, but keeps the ids
        return [[("generate_diagram", {"elements": context((new, [("arrow_user_api", "rect_user", "rect_api", None)] + arrows))})],
                "Done: User → API → Cache → Database. The ids are unchanged."]
    draw_in = runtime if era == "runtime" else skeleton
    added = draw_in(([CACHE], arrows), extra_shapes=new)
    return [[("query_canvas", {})],
            [("update_elements", {"updates": [{"id": "rect_db", "fields": {"x": 1060}}]}),
             ("remove_elements", {"ids": ["arrow_api_db"]})],
            [("add_elements", {"elements": added})],
            "Done: I moved the Database right and put the Cache between it and the API."]


MODIFY = {"modify-color": modify_color, "modify-add": modify_add}
