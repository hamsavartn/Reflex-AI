<div align="center">
  <h1>🎙️ AuraStream (formerly Reflex-AI)</h1>
  <p><b>Ultra-Low Latency, Context-Aware, Interruptible Voice Intelligence</b></p>
  <br />
</div>

## 🌌 Overview

**AuraStream** represents the next generation of voice-driven autonomous agents. Developed for the Samsung PRISM GenAI Hackathon 3.0, it overcomes traditional sequential conversational limits by offering **Native Interruptibility** and **Idempotent Tool Execution**. 

By utilizing Google's advanced Gemini multimodal architecture natively over WebRTC (LiveKit), AuraStream processes natural human speech, parses complex user intentions mid-sentence, and seamlessly halts or modifies its execution state without losing conversational context.

## 🚀 Key Innovations

1. **Sub-Second Native Latency (WebRTC)**
   - Bypasses traditional STT -> LLM -> TTS pipelines by streaming audio directly to and from Gemini 2.5/3.1 via LiveKit.
   - Intelligent thread-delegation ensures the event loop never stalls during synchronous I/O or background API tasks.

2. **Idempotent State Management & Interruption Rollbacks**
   - Automatically cancels out-of-date reasoning paths or superseded tool calls when the user interrupts the agent mid-sentence.
   - Prevents stale data fetches and duplicate transactional operations through a robust `generation` tracking registry.

3. **Multi-Domain Action Autonomy**
   - Seamlessly integrates with tools across E-commerce, Finance, Travel, and Housing.
   - Executes authorized changes in real-time, fetching live data (e.g., flight prices, live exchange rates) unconditionally.

## 🛠 Setup & Installation

1. Clone and construct the virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Configure your environment secrets in `.env.local` (Google AI Studio / LiveKit).
3. Initialize the AuraStream worker:
   ```bash
   python fdb3/v3/lk_agent_tool.py start
   ```

## 📊 Benchmarking & Evaluation

The system ships with a high-fidelity evaluation suite (`fdb3/` directory). Evaluate tool-call accuracy, latency profiles, and pass rates against standard baseline constraints via the automated `run_tool_benchmark_all_released.py` harness.
