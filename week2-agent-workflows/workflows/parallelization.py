# Parallelization: independent LLM calls run at the same time,
# then one more call combines their results.
# (A variant, "voting", asks the same question several times and takes the majority.)
#
# Who decides what happens next?  The code. Everything runs, every time.
from concurrent.futures import ThreadPoolExecutor

from llm import ask

ASPECTS = ["security", "performance", "readability"]


def review(aspect, code):
    return ask(f"Review this code ONLY for {aspect}. At most 3 short bullet points.\n\n{code}")


def merge(reviews):
    sections = "\n\n".join(f"## {aspect}\n{text}" for aspect, text in reviews.items())
    return ask(f"Combine these code reviews into one prioritized list of fixes:\n\n{sections}")


def run(code):
    with ThreadPoolExecutor() as pool:
        futures = {aspect: pool.submit(review, aspect, code) for aspect in ASPECTS}
        reviews = {aspect: future.result() for aspect, future in futures.items()}

    return merge(reviews)


if __name__ == "__main__":
    print(run('def get_user(name):\n    rows = db.execute("SELECT * FROM users WHERE name = \'" + name + "\'")\n    for r in rows:\n        if r.name == name: return r'))
