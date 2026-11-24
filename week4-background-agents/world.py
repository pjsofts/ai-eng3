"""You play the world around the agent: the alerting system, the on-call
engineer, the payments team. For the real Inngest demo (see app.py).

    python world.py alert feature                break checkout, send checkout/alert
    python world.py alert feature --lose-reply   ...and lose the reply to the next change
    python world.py alert feature --times 3      three alerts for the same incident
    python world.py state                        what checkout looks like now
    python world.py inbox                        open requests from the agent
    python world.py approve req-1                (or: deny req-1)
    python world.py answer req-1 "The payments team is on it"
    python world.py fix-gateway                  the payments team fixes it, and says so
    python world.py fix-gateway --quiet          ...fixes it, and says nothing
    python world.py deploy                       another engineer changes checkout
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "agent"))

import inngest  # noqa: E402

import checkout  # noqa: E402
import inbox  # noqa: E402
from client import client  # noqa: E402


def send(name, data):
    client.send_sync(inngest.Event(name=name, data=data))
    print(f"sent {name} {json.dumps(data)}")


def main(command, args):
    if command == "alert":
        checkout.start_incident(args[0], lose_next_reply="--lose-reply" in args)
        times = int(args[args.index("--times") + 1]) if "--times" in args else 1
        for _ in range(times):
            send("checkout/alert", {"service": "checkout", "summary": "checkout error rate is 42%"})
    elif command == "state":
        print(json.dumps(checkout.load(), indent=1))
    elif command == "inbox":
        for request_id, request in inbox.pending().items():
            print(f"{request_id}  [{request['kind']}]  {request['text']}")
    elif command in ("approve", "deny"):
        event = inbox.answer(args[0], approved=command == "approve")
        send(event["name"], event["data"])
    elif command == "answer":
        event = inbox.answer(args[0], approved=True, reply=args[1])
        send(event["name"], event["data"])
    elif command == "fix-gateway":
        checkout.fix_gateway()
        if "--quiet" not in args:
            send("checkout/recovered", {"service": "checkout"})
    elif command == "deploy":
        checkout.someone_deploys()
        print("checkout changed: version is now", checkout.load()["version"])
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "help", sys.argv[2:])
