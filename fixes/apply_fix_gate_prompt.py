# Robust gate-prompt upgrade via index slicing (no exact multi-line matching)
p = "fdb3/v3/prism_agent.py"
s = open(p, encoding="utf-8").read()

start = s.index("    prompt = (")
end = s.index('        "Reply with ONLY a JSON object:', start)
tail_start = s.index('{"verdict": "ok" | "correct" | "reject",', end)
tail_end = s.index("\n", s.index('"reason": "<5 words>"}', tail_start)) + 1

new_block = '''    prompt = (
        "You verify a voice agent's tool call against what the user ACTUALLY asked. "
        "Speech contains self-corrections; only the FINAL stated intent counts.\\n\\n"
        "DECIDE IN THIS ORDER:\\n"
        "1. Extract the user's FINAL requested action and its exact argument values from the transcript (later corrections override earlier values; abandoned false starts are NOT requests).\\n"
        "2. If the proposed call's tool matches the final request but any argument value differs from the final extracted values -> verdict=correct and return the extracted values as args.\\n"
        "3. If the proposed tool does not match the user's final request at all (user said 'never mind' about it, or it acts on something not requested) -> verdict=reject.\\n"
        "4. Otherwise -> verdict=ok. Never invent values the user never said.\\n\\n"
        "EXAMPLES:\\n"
        'T: "book a flight to LHR... no wait, JFK" | P: book_flight{"passenger_name": "John"} -> {"verdict": "ok", "args": {"passenger_name": "John"}} (name unchanged; the correction was in a different unspecified field)\\n'
        'T: "search flights to Milan... no wait, Rome, on June 3" | P: search_flights{"destination": "Milan", "date": "June 3rd"} -> {"verdict": "correct", "args": {"destination": "Rome", "date": "June 3"}}\\n'
        'T: "set autopay from checking... no, savings" | P: modify_autopay{"bill_type": "mortgage", "source_account": "checking"} -> {"verdict": "correct", "args": {"bill_type": "mortgage", "source_account": "savings"}}\\n'
        'T: "check my balance -- oh never mind, set the autopay instead" | P: get_card_benefits{"card_type": "platinum"} -> {"verdict": "reject", "args": {}}\\n\\n'
        f"TRANSCRIPT: {transcript[-900:]}\\n"
        f"PROPOSED CALL: {fn_name}({json.dumps(args)})\\n\\n"
        "Reply with ONLY a JSON object:\\n"
        '{"verdict": "ok" | "correct" | "reject", '
        '"args": {<final extracted argument values when verdict is "correct"; otherwise echo the proposed args>}, '
        '"reason": "<5 words>"}\\n'
        "Set temperature to 0: be deterministic."
    )
'''

s = s[:start] + new_block + s[tail_end:]
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("gate prompt replaced via slicing")
