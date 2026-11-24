# Evaluator-optimizer: two separate agents.
# A writer produces, an evaluator scores it against a rubric,
# and the writer improves it from the feedback, until it passes.
# Unlike reflection, the judge is a different agent with its own criteria.
#
# Who decides what happens next?  The evaluator's score decides,
# and the code sets the pass mark and the maximum rounds.
from agent import Agent
from llm import ask_json

PASS_SCORE = 8
MAX_ROUNDS = 3

RUBRIC = """- Under 8 words
- Mentions tea or tradition
- Easy to remember
- Not a cliché"""

writer = Agent("writer", "You write short marketing taglines. Reply with only the tagline.")


def evaluate(tagline):
    return ask_json(f"""You are a strict marketing judge. Score this tagline 1-10 against the rubric.

Rubric:
{RUBRIC}

Tagline: {tagline}

Reply as JSON: {{"score": 0, "feedback": "..."}}""")


def run(brief):
    tagline = writer.run(brief)

    for round in range(MAX_ROUNDS):
        review = evaluate(tagline)
        if review["score"] >= PASS_SCORE:
            break
        tagline = writer.run(f"{brief}\n\nYour last try: {tagline}\nFeedback: {review['feedback']}")

    return tagline


if __name__ == "__main__":
    print(run("A tagline for a family tea shop in Tehran that now sells online."))
