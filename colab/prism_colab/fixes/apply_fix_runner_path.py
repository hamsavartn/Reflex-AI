# One-shot patcher: pins telemetry path in run_tool_benchmark.py (Fix 2 runner side)
p = "fdb3/v3/run_tool_benchmark.py"
s = open(p, encoding="utf-8").read()

old = '''            telemetry_path = Path(__file__).parent.parent.parent / "logs" / "agent_tool_calls.log"
            if not telemetry_path.exists():
                # Fallback in case logs is in fdb3/v3/logs
                telemetry_path = Path("logs/agent_tool_calls.log")'''
new = '''            # PRISM fix (Fix 2): single source of truth for the telemetry path.
            # PRISM_TOOL_LOG env if set, else <this script's dir>/logs/. This
            # matches prism_agent.py's TOOL_LOG_PATH exactly — no CWD drift.
            telemetry_path = Path(os.environ.get(
                "PRISM_TOOL_LOG",
                str(Path(__file__).resolve().parent / "logs" / "agent_tool_calls.log"),
            ))'''
assert old in s, "telemetry block not found"
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("OK  fix: runner telemetry path pinned to env/script-dir")
