# Demo Video Script — 3 to 5 minutes, single takes, unedited preferred
### AuraStream — Theme 5: Interruptible Real-Time Agents

**Rules from the guide:** interruption handled live on the benchmark first, then the extension use case; show real behavior, not slides; 3–5 min. Record with OBS Studio (or Win+G). Two takes maximum per section; prefer one continuous take.

---

## Pre-flight (5 min before recording)

1. `python prism_agent.py start` running (or Colab worker) — worker registered
2. Benchmark audio loaded; evaluation page ready
3. Terminal visible for the tool-call log (`logs/agent_tool_calls.log` with `tail -f`)
4. Extension page ready (device-troubleshooting scenario)
5. Close ALL other assert dialogs; auto-ignore watcher running if on Windows

## Take structure (~4 min)

**[0:00–0:25] Problem + agent intro (talk over the terminal)**
> "Voice agents break the moment real humans talk normally. This benchmark — Full-Duplex-Bench v3 — streams real human recordings full of fillers, pauses, and self-corrections, and scores whether the agent still calls the right tools. This is our agent, built on LiveKit with a recovery layer: generation-numbered interruption handling, idempotent state changes, and a verification gate that re-checks every tool call against what the user actually said."

**[0:25–1:15] Interruption / self-correction on the benchmark (THE money shot)**
- Play a self-correction scenario (e.g., travel_19: "Milan… no wait… June 3rd").
- Show: the agent's tool log — exactly ONE `search_flights(destination='Milan', date='June 3')` call with the FINAL value.
- Say: "Watch the log — the user corrected themselves mid-sentence. A naive agent fires three calls, one per correction. Ours executes exactly once, with the final value — because stale calls are aborted before execution and the verification gate re-checks args against the transcript."

**[1:15–1:50] State-rollback safety**
- Play finance_23 (autopay "checking… no wait, savings").
- Say: "This is a booking/autopay — a state change. Calling it twice is a real-world bug: double-booking. Our idempotency layer records intent before execution and blocks duplicates structurally — even if the model re-issues."

**[1:50–3:00] Extension use case — device troubleshooting (camera frame)**
- Show a phone/device with a symptom; ask the agent conversationally: "My Wi-Fi keeps dropping, can you help?"
- Agent: `lookup_manual_section('wifi')` → speaks the manual steps → `resolve_deeplink('wifi')` gives the one-tap settings link.
- Say: "We extended the agent beyond the benchmark domains — Samsung-flavored device troubleshooting: the fix comes from the manual lookup tool, and the deeplink takes the user one tap from advice to action. It runs end to end, in this same LiveKit agent."

**[3:00–3:40] Architecture in 30 seconds (one diagram on screen)**
- Dual-path: realtime model = primary actor; verification gate + recovery executor = safety net; idempotency registry = no duplicate state changes; per-session state, no cross-scenario caching.

**[3:40–4:00] Results + close**
- "On the full 100-scenario benchmark: baseline Gemini 2.5 native audio scored 29% strict pass. With our recovery layer: [FINAL NUMBER] — with tool-selection F1 of [FINAL F1]. All improvements are platform mechanisms, not test-specific tuning. Repo, repro script, and logs are in the submission."

---

## After recording
- Verify length ≤ 5:00; audio audible; no assert dialogs on screen.
- Upload to YouTube (unlisted) or Drive; put the link in the Google Form + deck.
