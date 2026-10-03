import json, glob, sys, os
sys.path.insert(0, os.getcwd())
from collections import Counter
from evaluate_tool_calls import exact_match_args

def norm(v):
    if isinstance(v, str):
        return v.lower().strip().replace("_", " ")
    return v

def args_match(exp_args, act_args):
    """Mirror official exact_match_args (extra keys in actual ignored)."""
    for k, ev in exp_args.items():
        if isinstance(ev, str) and ev.startswith("$"):
            continue
        if k not in act_args:
            return False
        av = act_args[k]
        if isinstance(ev, str) and not isinstance(av, str):
            av2 = str(av)
        else:
            av2 = av
        if norm(ev) != norm(av2) and str(ev) != str(av):
            return False
    return True

fail_types = Counter()
extra_funcs = Counter()
missing_funcs = Counter()
wrong_arg_field = Counter()
domain_fail = Counter()
disf_fail = Counter()
tot = passed = 0

for f in glob.glob("fdb_v3_data_released/*/result_gemini2_5.json"):
    d = json.load(open(f, encoding="utf-8"))
    m = json.load(open(f.replace("result_gemini2_5.json", "metadata.json"), encoding="utf-8"))
    tot += 1
    exp_calls = m["expected_tool_calls"]
    act_calls = d.get("actual_tool_calls", [])
    used = [False] * len(act_calls)
    ok = True
    extras, missings, wrongargs = [], [], []
    for e in exp_calls:
        hit = False
        for i, a in enumerate(act_calls):
            if used[i] or a["function"] != e["function"]:
                continue
            if args_match(e["args"], a["args"]):
                used[i] = True
                hit = True
                break
        if not hit:
            # was it called at all with same function?
            fn_any = any(a["function"] == e["function"] for a in act_calls)
            (wrongargs if fn_any else missings).append(e)
            ok = False
    for i, a in enumerate(act_calls):
        if not used[i]:
            extras.append(a)
    if extras:
        ok = False
    if ok:
        passed += 1
        continue
    domain_fail[m["domain"]] += 1
    tags = m.get("disfluency_features") or []
    kinds = {t if isinstance(t, str) else t.get("type", "") for t in tags}
    for k in kinds:
        disf_fail[k] += 1
    if m.get("state_rollback_test"):
        disf_fail["STATE_ROLLBACK"] += 1
    if missings and not extras and not wrongargs:
        fail_types["MISSING_ONLY"] += 1
    elif wrongargs and not extras and not missings:
        fail_types["WRONG_ARGS_ONLY"] += 1
    elif extras and not missings and not wrongargs:
        fail_types["EXTRA_ONLY"] += 1
    elif extras and (missings or wrongargs):
        # extra call(s) consumed the slot of a missing/wrong expected call
        fail_types["EXTRA + missing/wrong (chain broke)"] += 1
    elif missings and wrongargs:
        fail_types["MISSING + WRONG_ARGS"] += 1
    for e in missings:
        missing_funcs[e["function"]] += 1
    for e in wrongargs:
        for k in e["args"]:
            if not k.startswith("$"):
                wrong_arg_field[f"{e['function']}.{k}"] += 1
    for a in extras:
        extra_funcs[a["function"]] += 1

print(f"total={tot} official-strict passed={passed} ({100*passed/tot:.0f}%)  failed={tot-passed}")
print("\nfailure types:")
for k, v in fail_types.most_common():
    print(f"  {v:3d}  {k}")
print("\nEXTRA-call functions (precision leaks):")
for k, v in extra_funcs.most_common(10):
    print(f"  {v:3d}  {k}")
print("\nMISSING-call functions (recall leaks):")
for k, v in missing_funcs.most_common(10):
    print(f"  {v:3d}  {k}")
print("\nWRONG-ARG fields:")
for k, v in wrong_arg_field.most_common(10):
    print(f"  {v:3d}  {k}")
print("\nfailure co-occurrence with disfluency:", dict(disf_fail.most_common()))
print("fails by domain:", dict(domain_fail))
