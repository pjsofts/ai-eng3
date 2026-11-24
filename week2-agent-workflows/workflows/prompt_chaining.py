# Prompt chaining: a fixed sequence of LLM calls.
# Each step's output becomes the next step's input.
#
# Who decides what happens next?  The code. The path never changes.
from llm import ask


def extract_features(product):
    return ask(f"List the 3 most important features of this product, one per line:\n\n{product}")


def write_announcement(features):
    return ask(f"Write an exciting launch announcement, under 50 words, from these features:\n\n{features}")


def is_short_enough(text):
    # A "gate" between steps can be plain code: fast, free and predictable
    return len(text.split()) <= 50


def shorten(text):
    return ask(f"Rewrite this in under 50 words:\n\n{text}")


def translate(text):
    return ask(f"Translate this into Persian. Reply with only the translation:\n\n{text}")


def run(product):
    features = extract_features(product)
    announcement = write_announcement(features)

    if not is_short_enough(announcement):
        announcement = shorten(announcement)

    return translate(announcement)


if __name__ == "__main__":
    print(run("Saffron: a note-taking app that turns voice memos into to-do lists, works offline and syncs across devices."))
