"""Recorded LLM replies for replay mode, so the demo runs offline.

For each workflow, a list of (match, reply) rules. The first rule whose `match`
text appears in the request wins (for ask/ask_json the request is the system
prompt plus the prompt, for chat it is the system prompt). A reply can be:

- a str: the text answer
- a dict: a JSON answer (ask_json), or {"say": ..., "call": [(tool, args), ...]} (chat)
- a list: replies handed out in order, one per call (the last one repeats)
- a callable: called with the request text, returns one of the above
"""
import itertools
import threading

from llm import Reply, ToolCall

NO_RECORDING = "(Replay mode has no recorded answer for this input. Switch to Live to use the model.)"


def classify_by_keywords(text):
    ticket = text.split("Ticket:", 1)[-1].lower()
    for category, words in {
        "billing": ["charge", "refund", "invoice", "price", "pay", "bill"],
        "technical": ["error", "api", "bug", "crash", "403", "500", "slow"],
        "account": ["login", "log in", "password", "account", "2fa", "email"],
    }.items():
        if any(word in ticket for word in words):
            return {"category": category, "reason": f"The ticket mentions {category} keywords."}
    return {"category": "other", "reason": "This is not a support question we handle."}


SCRIPTS = {
    "prompt_chaining": [
        ("most important features", "1. Turns voice memos into to-do lists automatically\n"
                                    "2. Works fully offline\n3. Syncs across all your devices"),
        ("launch announcement", "Meet Saffron, the note-taking app that finally keeps up with your brain! "
                                "Just talk: Saffron listens to your voice memos and instantly turns them into "
                                "clear, organized to-do lists. No signal on the metro? No problem, it works "
                                "completely offline. Then it quietly syncs everything across your phone, tablet "
                                "and laptop, so your ideas are always waiting wherever you are. Try it today!"),
        ("under 50 words", "Meet Saffron: just talk, and your voice memos become clear to-do lists. "
                           "It works fully offline and syncs across all your devices, so your ideas are "
                           "always with you. Try it today!"),
        ("into Persian", "با زعفران آشنا شوید: فقط حرف بزنید تا یادداشت‌های صوتی‌تان به فهرست کارهای مرتب "
                         "تبدیل شوند. کاملاً آفلاین کار می‌کند و روی همهٔ دستگاه‌هایتان همگام می‌شود، "
                         "تا ایده‌هایتان همیشه همراهتان باشند. همین امروز امتحانش کنید!"),
    ],
    "routing": [
        ("Classify this support ticket", classify_by_keywords),
        ("billing specialist", "Sorry about the double charge! I can see two payments for this month. "
                               "The second one is a duplicate, so I've flagged it for a full refund. "
                               "It will be back on your card within 5-7 business days."),
        ("support engineer", "Let's debug it: 1) check the exact status code and response body, "
                             "2) confirm your API key is still valid, 3) retry with verbose logging on."),
        ("logins and account", "You can reset your password from the login page with 'Forgot password'. "
                               "If 2FA is the problem, I can send a recovery link to your email."),
    ],
    "parallelization": [
        ("ONLY for security", "- SQL injection: `name` is concatenated into the query. Use parameters.\n"
                              "- SELECT * may expose sensitive columns such as password hashes."),
        ("ONLY for performance", "- Filter in SQL with LIMIT 1 instead of looping in Python.\n"
                                 "- Make sure `users.name` has an index."),
        ("ONLY for readability", "- `r` is a vague name; use `row` or `user`.\n"
                                 "- Put the `return` on its own line.\n- Returns None implicitly; make it explicit."),
        ("Combine these code reviews", "1. **Fix the SQL injection**: use a parameterized query (critical).\n"
                                       "2. Select only the columns you need instead of `*`.\n"
                                       "3. Let the database do the filtering: `WHERE name = ? LIMIT 1`, with an index.\n"
                                       "4. Rename `r` to `user` and return `None` explicitly."),
    ],
    "react": [
        ("Answer the user's question using the tools", [
            {"say": "First I need to know when the Eiffel Tower opened and who built it.",
             "call": [("search", {"query": "Eiffel Tower"})]},
            {"say": "It opened in 1889 and was built by Gustave Eiffel's company. Now I need his birth year.",
             "call": [("search", {"query": "Gustave Eiffel"})]},
            {"say": "He was born in 1832, so I'll subtract.",
             "call": [("calculate", {"expression": "1889 - 1832"})]},
            "Gustave Eiffel was about **57 years old** when the Eiffel Tower opened in 1889 (he was born in 1832).",
        ]),
    ],
    "plan_and_execute": [
        ("Break this goal into", {"steps": [
            "Find the height and opening year of Milad Tower",
            "Find the height and opening year of the Eiffel Tower",
            "Calculate the height difference and the years between the openings",
        ]}),
        ("Answer the user's question using the tools", [
            {"say": "Searching for Milad Tower.", "call": [("search", {"query": "Milad Tower"})]},
            "Milad Tower is 435 m tall and opened in 2007.",
            {"say": "Searching for the Eiffel Tower.", "call": [("search", {"query": "Eiffel Tower"})]},
            "The Eiffel Tower is 330 m tall and opened in 1889.",
            {"say": "I'll compute both differences at once.",
             "call": [("calculate", {"expression": "435 - 330"}),
                      ("calculate", {"expression": "2007 - 1889"})]},
            "Milad Tower is 105 m taller, and the two towers opened 118 years apart.",
        ]),
        ("Write the final answer", "Milad Tower (435 m, 2007) is 105 m taller than the Eiffel Tower "
                                   "(330 m, 1889), and it opened 118 years later."),
    ],
    "reflection": [
        ("Critique this answer", [
            "1. \"Autonomous system\" and \"environment\" are jargon for a high-school student.\n"
            "2. There is no concrete example.\n3. It is 4 sentences, not 3.",
            "LGTM",
        ]),
        ("Rewrite the answer", "An AI agent is a program that uses an AI model to reach a goal on its own, "
                               "step by step. For example, if you ask it to plan a trip, it can search for "
                               "flights, compare hotels and check the weather without you telling it each step. "
                               "It keeps going, looking at the result of each action, until the job is done."),
        ("", "An AI agent is an autonomous system that perceives its environment and takes actions. "
             "It uses a large language model to reason. It can use tools such as search engines and APIs. "
             "It works towards a goal over multiple steps."),
    ],
    "codeact": [
        ("Solve the task by writing Python code", [
            "I'll use a sieve of Eratosthenes.\n```python\nlimit = 10_000\nis_prime = [True] * limit\n"
            "is_prime[0] = is_prime[1] = False\nfor n in range(2, math.isqrt(limit) + 1):\n"
            "    if is_prime[n]:\n        for multiple in range(n * n, limit, n):\n"
            "            is_prime[multiple] = False\nprimes = [n for n in range(limit) if is_prime[n]]\n"
            "print(len(primes), sum(primes))\n```",
            "I forgot to import `math`. Fixed:\n```python\nimport math\n\nlimit = 10_000\n"
            "is_prime = [True] * limit\nis_prime[0] = is_prime[1] = False\n"
            "for n in range(2, math.isqrt(limit) + 1):\n    if is_prime[n]:\n"
            "        for multiple in range(n * n, limit, n):\n            is_prime[multiple] = False\n"
            "primes = [n for n in range(limit) if is_prime[n]]\nprint(len(primes), sum(primes))\n```",
            "ANSWER: There are 1229 primes below 10,000, and their sum is 5,736,396.",
        ]),
    ],
    "sequential_agents": [
        ("Find the facts with the search tool", [
            {"say": "Searching both towers.",
             "call": [("search", {"query": "Milad Tower"}), ("search", {"query": "Eiffel Tower"})]},
            "- Milad Tower: Tehran, opened 2007, 435 m tall\n"
            "- Eiffel Tower: Paris, opened 1889, 330 m tall, built by Gustave Eiffel's company",
        ]),
        ("engaging paragraph", "Two cities, two icons. Paris's Effiel Tower rose in 1889, a 330-metre "
                               "iron marvel from Gustave Eiffel's company. More then a century later, in 2007, "
                               "Tehran answered with Milad Tower, which soars to 435 metres, over 100 metres "
                               "taller. One is a symbol of the industrial age, the other of a modern capital."),
        ("Fix any errors", "Two cities, two icons. Paris's Eiffel Tower rose in 1889, a 330-metre iron marvel "
                           "from Gustave Eiffel's company. More than a century later, in 2007, Tehran answered "
                           "with Milad Tower: 435 metres tall, over 100 metres higher. One symbolizes the "
                           "industrial age; the other, a modern capital."),
    ],
    "parallel_agents": [
        ("best way to get there", [
            {"say": "", "call": [("search_flights", {"destination": "Isfahan"})]},
            "The bus is the budget pick: about 6 hours and 0.6M toman each. A 1-hour flight costs 2.1M.",
        ]),
        ("place to stay", [
            {"say": "", "call": [("search_hotels", {"city": "Isfahan"})]},
            "Saraye Ameri: a traditional house hotel at 1.8M toman a night.",
        ]),
        ("places to eat", [
            {"say": "", "call": [("find_restaurants", {"city": "Isfahan"})]},
            "Try Azam Beryani for cheap local beryani, and Shahrzad for a classic Persian dinner.",
        ]),
        ("Write a short weekend plan", "**Friday**: take the morning bus from Tehran (6h, 0.6M each), check "
                                       "in to Saraye Ameri (1.8M/night) and have beryani at Azam Beryani.\n"
                                       "**Saturday**: walk Naqsh-e Jahan Square and Si-o-se Pol, then dinner "
                                       "at Shahrzad.\n**Sunday**: bus back. Rough total for two: about 7M toman."),
    ],
    "supervisor": [
        ("You manage a team", [
            {"say": "First I need both populations.",
             "call": [("ask_researcher", {"task": "What are the populations of Istanbul and Tehran?"})]},
            {"say": "Now the ratio.",
             "call": [("ask_analyst", {"task": "Divide Istanbul's population (15.7 million) by Tehran's (9.5 million)."})]},
            {"say": "Time for the final answer.",
             "call": [("ask_writer", {"notes": "Istanbul about 15.7M, Tehran about 9.5M, ratio about 1.65."})]},
            "Istanbul has about 15.7 million people and Tehran about 9.5 million, "
            "so Istanbul is roughly 1.65 times bigger.",
        ]),
        ("Find facts with the search tool", [
            {"say": "", "call": [("search", {"query": "Istanbul population"}),
                                 ("search", {"query": "Tehran population"})]},
            "Istanbul: about 15.7 million people. Tehran: about 9.5 million people.",
        ]),
        ("Do the math", [
            {"say": "", "call": [("calculate", {"expression": "15.7 / 9.5"})]},
            "15.7 / 9.5 = 1.65",
        ]),
        ("Write a clear, short answer", "Istanbul has about 15.7 million people and Tehran about 9.5 million, "
                                        "so Istanbul is roughly 1.65 times bigger."),
    ],
    "dispatcher": [
        ("Split this customer request", {"tasks": [
            {"specialist": "billing", "task": "Customer 4521 says they were charged twice in September. Check and refund the duplicate."},
            {"specialist": "technical", "task": "Customer 4521's API has returned 403 since Oct 1. Find the cause."},
        ]}),
        ("billing specialist", [
            {"say": "", "call": [("lookup_invoice", {"customer_id": "4521"})]},
            {"say": "The September charge was duplicated, so I'll refund one.",
             "call": [("issue_refund", {"customer_id": "4521", "amount": "$49"})]},
            "Billing: you were charged $49 twice in September. I've refunded the duplicate $49.",
        ]),
        ("support engineer", [
            {"say": "", "call": [("check_api_logs", {"customer_id": "4521"})]},
            "Technical: your API calls fail with 403 'plan does not include API access' since Oct 1. "
            "Your plan no longer includes the API.",
        ]),
    ],
    "evaluator_optimizer": [
        ("short marketing taglines", [
            "Steeped in family tradition, delivered from our Tehran shop straight to your door",
            "Tehran's family tea, now at your door",
            "Three generations of tea, one click away",
        ]),
        ("strict marketing judge", [
            {"score": 5, "feedback": "Too long (13 words) and generic. Cut it under 8 words."},
            {"score": 7, "feedback": "Short and clear, but 'at your door' is a cliché. Make it more memorable."},
            {"score": 9, "feedback": "Short, memorable, and the family tradition comes through."},
        ]),
    ],
    "peer_to_peer": [
        ("You are the first contact", "HANDOFF: technical | Customer 4521's API stopped working right after renewal."),
        ("You are a support engineer", [
            {"say": "", "call": [("check_api_logs", {"customer_id": "4521"})]},
            "HANDOFF: billing | API returns 403 'plan does not include API access' since Oct 1. "
            "The plan looks downgraded. Please check the renewal.",
        ]),
        ("You are a billing specialist", [
            {"say": "", "call": [("lookup_invoice", {"customer_id": "4521"})]},
            "Thanks for your patience! Your Oct 1 renewal failed because the card on file had expired, so "
            "the account moved to the Free plan, which has no API access. Update your card under "
            "Settings → Billing and your Pro plan and API will come back right away.",
        ]),
    ],
}


class Replay:
    def __init__(self, workflow):
        self.rules = SCRIPTS.get(workflow, [])
        self.counts = {}
        self.ids = itertools.count(1)
        self.lock = threading.Lock()

    def respond(self, kind, request):
        reply = self.pick(request)
        if callable(reply):
            reply = reply(request)
        if kind == "ask":
            return reply if isinstance(reply, str) else str(reply)
        if kind == "ask_json":
            return reply if isinstance(reply, dict) else {"answer": reply}
        if isinstance(reply, dict):
            calls = [ToolCall(f"call_{next(self.ids)}", name, args) for name, args in reply.get("call", [])]
            return Reply(reply.get("say", ""), calls)
        return Reply(str(reply))

    def pick(self, request):
        with self.lock:
            for index, (match, reply) in enumerate(self.rules):
                if match in request:
                    if isinstance(reply, list):
                        count = self.counts.get(index, 0)
                        self.counts[index] = count + 1
                        return reply[min(count, len(reply) - 1)]
                    return reply
        return NO_RECORDING
