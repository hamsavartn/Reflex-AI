# Generate the submission deck (<= 8 slides per the updated guide)
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

ACCENT = RGBColor(0x14, 0x28, 0x50)   # deep navy
HILITE = RGBColor(0x00, 0x84, 0x2F)   # prism green
GREY = RGBColor(0x44, 0x44, 0x44)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def add_slide(title, bullets, note=None, title_size=32):
    s = prs.slides.add_slide(BLANK)
    tb = s.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12.1), Inches(1.0))
    p = tb.text_frame.paragraphs[0]
    p.text = title
    p.font.size = Pt(title_size)
    p.font.bold = True
    p.font.color.rgb = ACCENT
    body = s.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.3))
    tf = body.text_frame
    tf.word_wrap = True
    first = True
    for item in bullets:
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        if isinstance(item, tuple):
            text, opts = item
        else:
            text, opts = item, {}
        para.text = ("• " if opts.get("bullet", True) else "") + text
        para.font.size = Pt(opts.get("size", 20))
        para.font.bold = opts.get("bold", False)
        para.font.color.rgb = opts.get("color", GREY)
        para.space_after = Pt(10)
    return s

# ---- 1 Title
s = prs.slides.add_slide(BLANK)
tb = s.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.7), Inches(2.5))
tf = tb.text_frame
p = tf.paragraphs[0]; p.text = "AuraStream"
p.font.size = Pt(54); p.font.bold = True; p.font.color.rgb = ACCENT
p2 = tf.add_paragraph(); p2.text = "An Interruptible Real-Time Voice Agent with a Session-Recovery Layer"
p2.font.size = Pt(26); p2.font.color.rgb = GREY
p3 = tf.add_paragraph(); p3.text = "Samsung PRISM GenAI Hackathon 3.0 — Theme 05 · Team [CollegeName_TeamName]"
p3.font.size = Pt(18); p3.font.color.rgb = HILITE; p3.font.bold = True

# ---- 2 Problem
add_slide("The problem: real speech breaks voice agents", [
    "Real users say 'um', restart sentences, and correct themselves mid-utterance",
    "Standard half-duplex agents mis-hear intent, fire premature tool calls, and double-execute state changes",
    "FDB-v3 (NTU + NVIDIA): 100 real human recordings, 5 disfluency types, chained calls on 12 mock tools, 4 domains",
    ("Published ceiling: best system Pass@1 = 0.600 (GPT-Realtime); self-corrections + hard chains are the universal failure mode", {"bold": True}),
])

# ---- 3 Architecture
s = add_slide("Architecture: primary actor + platform recovery", [
    "Gemini 2.5 native audio (LiveKit) — the primary actor, speaks and calls tools in real time",
    "Verification gate — every proposed call re-checked against the user's final transcript (stale args corrected pre-execution)",
    "Recovery executor — if the primary stays silent, a text model re-parses the final transcript (read-only) and acts",
    "Quiet-wait + deliberation windows — nothing executes while the user is mid-correction",
    "Session-scoped by construction — fresh state per scenario, nothing cached across runs",
])
# simple flow diagram
boxes = [("User audio", 0.8), ("LiveKit session", 2.9), ("Realtime model", 5.0), ("Verification gate", 7.3), ("Mock tools / log", 9.9)]
for i, (label, x) in enumerate(boxes):
    shp = s.shapes.add_shape(1, Inches(x), Inches(6.3), Inches(2.0), Inches(0.7))
    shp.text_frame.text = label
    shp.text_frame.paragraphs[0].font.size = Pt(12)
    shp.text_frame.paragraphs[0].font.bold = True
    shp.fill.solid(); shp.fill.fore_color.rgb = ACCENT if i in (2, 3) else HILITE
    shp.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)

# ---- 4 Mechanisms
add_slide("Three platform mechanisms (general, not scenario-tuned)", [
    ("1. Generation-numbered interruption", {"bold": True, "color": ACCENT}),
    "every user speech start bumps a generation; in-flight calls from older generations abort before execution — stale values never reach the log",
    ("2. Idempotent state changes", {"bold": True, "color": ACCENT}),
    "registry-before-yield: state-modifying tools record intent before executing; duplicates are structurally impossible; cancelled calls persist as PENDING_CONFIRMATION",
    ("3. Verification gate", {"bold": True, "color": ACCENT}),
    "a fast text model validates every call against the final transcript: auto-corrects self-corrected arguments, rejects calls that match no stated intent (fails open)",
])

# ---- 5 Results (placeholders)
add_slide("Benchmark results (100 scenarios)", [
    ("Baseline: Gemini 2.5 Flash native-audio template — strict pass 29%", {"bold": True}),
    "AuraStream (this submission): strict pass [FINAL_PASS]% · tool-selection F1 [FINAL_F1] · argument accuracy [FINAL_ARG]%",
    "Largest gains: self-correction scenarios and 2–3-call chains (the published universal failure modes)",
    "Latency: first speech ~[FINAL_LAT]s after user turn end (virtual-free, real-time capture)",
    "Numbers reproduced by the one-command script; logs, seeds and configs in the repo",
], note="fill from prism_results.zip")

# ---- 6 Failure-mode engineering
add_slide("How the gains were earned (root-caused, not tuned)", [
    "Mined all 100 baseline failures with the official matcher: 45 missing-action, 31 chain-broke, search_flights args wrong x15",
    "Fix 1 — final-transcript gate: interim transcripts no longer trigger actions (killed retracted-intent calls)",
    "Fix 2 — quiet-wait: nothing executes mid-correction; the FINAL value is the one that lands",
    "Fix 3 — read-tool idempotency: identical repeat calls served from cache, never re-logged",
    "Validated on the hardest torture set (rollback + self-correction + hard chains): the regression case passes 3/3 rounds; gate corrects stale args 5/6 offline",
])

# ---- 7 Extension
add_slide("Extension: hands-free device troubleshooting (Samsung-flavored)", [
    "Same LiveKit agent + 3 tools: lookup_manual_section, diagnose_from_frame, resolve_deeplink",
    "Flow: user describes (or shows) a symptom → agent grounds the fix in the manual → returns the exact settings deeplink — advice to action in one tap",
    "Runs end-to-end in the demo video; grounded in tool output, never from model memory",
    "Honest scope: deterministic mock manual (no external calls at evaluation time — per competition rules)",
])

# ---- 8 What's next
add_slide("What we would do next", [
    "Distil the recovery executor into a small on-device model (sub-100ms gate decisions)",
    "Learned deliberation: predict correction probability from prosody instead of a fixed quiet window",
    "Streaming frame grounding for the extension (per-frame intent confidence)",
    "Close the remaining strict-pass gap: ambiguous-slot clarification policies that stay inside the no-questions rule (ask only when the entity is genuinely unresolvable)",
    ("Repo, one-command reproduction, run logs and configs: in the submission", {"bold": True, "color": HILITE}),
])

prs.save("deliverables/AuraStream_Deck.pptx")
print("deck written: deliverables/AuraStream_Deck.pptx (8 slides)")
