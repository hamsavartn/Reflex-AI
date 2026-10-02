import json, glob, shutil, os
os.makedirs("fdb_v3_data_val", exist_ok=True)
picked = []
for f in glob.glob("fdb_v3_data_released/*/metadata.json"):
    m = json.load(open(f, encoding="utf-8"))
    d = os.path.dirname(f)
    tags = m.get("disfluency_features") or []
    kinds = {t if isinstance(t, str) else t.get("type", "") for t in tags}
    score = 0
    if "SELF_CORRECTION" in kinds: score += 4
    if m.get("state_rollback_test"): score += 4
    if m.get("difficulty") == "hard": score += 3
    if score >= 4:
        picked.append((score, d, m.get("id", os.path.basename(d))))
picked.sort(reverse=True)
seen, chosen = set(), []
for sc, d, eid in picked:
    if eid in seen: continue
    seen.add(eid); chosen.append(d)
    if len(chosen) == 5: break
good = "fdb_v3_data_released/ecommerce_01_65e8cf8f4c7424fa062e54a3"
if os.path.exists(good): chosen.append(good)
for d in chosen:
    dst = os.path.join("fdb_v3_data_val", os.path.basename(d))
    if not os.path.exists(dst):
        shutil.copytree(d, dst)
    m = json.load(open(os.path.join(d, "metadata.json"), encoding="utf-8"))
    tags = m.get("disfluency_features") or []
    kinds = {t if isinstance(t, str) else t.get("type", "") for t in tags}
    print(f"{os.path.basename(d)[:44]} | {m.get('difficulty')} | rb={bool(m.get('state_rollback_test'))} | {sorted(kinds)}")
print("val set:", len(os.listdir("fdb_v3_data_val")), "examples")
