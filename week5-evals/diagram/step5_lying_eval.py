# Step 5 — Is the eval lying?
# Step 4 scores 100% on bound labels and bound arrows. Open the app and ask for
# the same diagram: the boxes are empty and the arrows float. Both can't be true.
#
# The eval scored what the model SAID it drew: the elements it sent.
# The user sees what Excalidraw DREW from them: draw() reads label and start/end,
# and drops containerId and startBinding without a word.
# Run step 4's agent once. Score both. When the eval and the product disagree,
# the eval is wrong first.
from agent import run_agent
from canvas import draw
from prompts import TOOLS as SYSTEM
from scorers import bound_arrows, bound_labels, connectivity
from step4_tools import TOOLS
from tools import CANVAS, new_canvas

SCORERS = [bound_labels, bound_arrows, connectivity]


def run(task):
    new_canvas()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    run_agent(messages, TOOLS)

    claims = list(CANVAS)        # what the step 4 eval scored
    drawn = draw(claims)         # what the user sees
    return score("The eval scored", claims, task) + "\n" + score("The user sees  ", drawn, task)


def score(who, elements, task):
    """Every scorer on one list of elements, as one line."""
    case = {"input": task, "category": "create"}
    output = {"text": "", "elements": elements, "tool_calls": []}
    results = [(scorer.__name__, scorer(case, output)) for scorer in SCORERS]
    return f"{who}:  " + "   ".join(f"{name} {value:.0%}" for name, value in results if value is not None)


if __name__ == "__main__":
    print(run("Draw a flow from User to API to Database"))
