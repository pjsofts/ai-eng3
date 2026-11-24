# models.py — the ladder of models we compare, and what each one costs.
#
# Prices are dollars per million tokens, input / output. They change: check
# your provider's pricing page and edit them here. Batch requests cost half.
import os
from dataclasses import dataclass


@dataclass
class Model:
    tier: str         # small, medium, large: what the slides call them
    id: str           # what the API calls them
    input_price: float
    output_price: float


LADDER = [
    Model("small", os.environ.get("SMALL_MODEL", "gpt-4.1-nano"), 0.10, 0.40),
    Model("medium", os.environ.get("MEDIUM_MODEL", "gpt-4.1-mini"), 0.40, 1.60),
    Model("large", os.environ.get("LARGE_MODEL", "gpt-4.1"), 2.00, 8.00),
]

# The judge should not be the model whose answers it grades (step 2).
JUDGE = os.environ.get("JUDGE_MODEL", LADDER[-1].id)

BATCH_DISCOUNT = 0.5


def by_tier(tier):
    return next(model for model in LADDER if model.tier == tier)


def cost(model, reply, batch=False):
    """Dollars for one call: tokens times the price per token."""
    dollars = (reply.input_tokens * model.input_price + reply.output_tokens * model.output_price) / 1_000_000
    return dollars * (BATCH_DISCOUNT if batch else 1)
