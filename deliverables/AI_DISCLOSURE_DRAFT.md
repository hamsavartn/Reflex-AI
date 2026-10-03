# AI Usage Disclosure — DRAFT (fill team fields before submission)
### Pre-filled from the project's actual development history

## 1. Team Details
- **Team Name:** [CollegeName_TeamName] — FILL IN
- **Project / Product Name:** AuraStream — Interruptible Real-Time Voice Agent (Theme 5)
- **Organization / Institution:** [College] — FILL IN
- **Submission Date:** 2026-10-04 — adjust

## 2. AI Usage Declaration
**Did your team use AI in developing this project? YES**

## 3. Purpose of AI Usage
| Purpose | Used? | Notes |
|---|---|---|
| Idea generation / brainstorming | Yes | architecture options, failure-mode analysis |
| Code generation or assistance | Yes | primary development driver (see §4) |
| UI / UX design | No | no UI (voice agent + logs) |
| Content creation | Yes | README, deck text, this disclosure |
| Data analysis | Yes | failure mining of benchmark results |
| Testing / debugging | Yes | root-causing (soxr crash, telemetry paths) |

## 4. Feature Origin Classification
| # | Feature | Origin | Description (tools, prompts, output, modification) |
|---|---|---|---|
| 1 | Two-queue protocol & recovery layer (generation numbers, idempotency, deliberation windows) | Both | Designed and iterated with ZCode (LLM agent); every mechanism verified by unit tests and reviewed by an independent AI architectural review + human review. Team made all design decisions. |
| 2 | Verification gate (text-model arg verification) | Both | Prompt engineered via AI; decision procedure and few-shot examples written by AI, validated offline (5/6) by the team; integrated by AI, reviewed by team. |
| 3 | Failure mining of benchmark results | Both | AI-written analysis scripts; team-directed hypotheses; all conclusions human-verified. |
| 4 | Benchmark harness patches (Windows paths, CPU fallback, plugin registration, telemetry pinning) | Both | AI root-caused and patched; each patch verified by the team before adoption. |
| 5 | Colab evaluation notebook + repro script | Both | AI-authored; team executed and validated. |
| 6 | Mock tool payloads & extension tools (manual lookup, deeplink) | Both | AI-authored content grounded in public device-support knowledge; team reviewed. |

## 5. Ethical & Compliance Confirmation
- AI usage complies with hackathon guidelines and policies. **Yes**
- No proprietary or copyrighted data misused. **I Agree** (upstream benchmark is CC BY-NC — vendored with attribution and disclosed patches; no benchmark test items memorized or hardcoded — all improvements are general platform mechanisms).

## 6. Declaration & Sign-Off
- Name of Team Representative: FILL IN
- Role: FILL IN
- Signature: FILL IN
- Date: FILL IN
