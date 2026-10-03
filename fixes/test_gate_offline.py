"""Offline validation of the PRISM verification gate.

Replays proposals from OUR OWN 100-sample baseline failures through the real
verify_call() (text-only Gemini) and checks: does the gate correct stale
args / reject non-matching calls, while leaving good calls untouched?
This is a mechanism test on aggregate failure patterns — no test-item tuning.
"""
import asyncio, json, os, sys
sys.path.insert(0, ".")
os.environ.setdefault("PRISM_GATE", "1")
from dotenv import load_dotenv
load_dotenv(".env.local")
import prism_agent
from prism_agent import verify_call

CASES = [
    # (name, transcript, proposed fn, proposed args, expected verdict, expected-args-check)
    ("self-correction: destination+date", 
     "Um... I need a flight... to Milan... no wait, actually Rome first... hmm, no — Milan is fine. June 3rd, so search flights to Milan on June 3.",
     "search_flights", {"destination": "Milan", "date": "june first"},
     "correct", lambda a: a.get("date", "").lower().startswith("june 3")),
    ("self-correction: account type",
     "I really need to set the mortgage autopay to pull from checking. No wait, on second thought, savings is better. Make it pull from savings instead.",
     "modify_autopay", {"bill_type": "mortgage", "source_account": "checking"},
     "correct", lambda a: a.get("source_account") == "savings"),
    ("clean call stays ok",
     "I ordered something last week and I haven't received it yet. Could you track it for me? The order ID is A-B-C-1-2-3.",
     "track_order", {"order_id": "ABC123"},
     "ok", None),
    ("abandoned false start: reject extra",
     "Um... so can you check the balance on my — oh actually, never mind that part. What I really need is to set the mortgage autopay.",
     "get_card_benefits", {"card_type": "platinum"},
     "reject", None),
    ("multi-action chain stays ok",
     "Find me a one-bedroom apartment in San Francisco under 3500, with pets allowed. And also, how far is the train station from the first one?",
     "search_apartments", {"city": "San Francisco", "bedrooms": 1, "max_price": 3500.0},
     "ok", None),
    ("spoken number normalization",
     "What's the exchange rate for, um, five hundred dollars to euros?",
     "get_exchange_rate", {"amount": "500", "from_currency": "USD", "to_currency": "EUR"},
     "ok", lambda a: str(a.get("amount")) in ("500", "500.0")),
]

async def main():
    results = []
    for name, tr, fn, args, want, check in CASES:
        v = await verify_call(tr, fn, args)
        got = v["verdict"]
        ok = got == want and (check is None or check(v.get("args", args)))
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'} | want={want:7s} got={got:7s} | {name}")
        if got == "correct":
            print(f"         corrected args: {v.get('args')}")
    print(f"\n--- gate offline score: {sum(results)}/{len(results)} ---")

asyncio.run(main())
