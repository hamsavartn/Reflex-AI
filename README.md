# Reflex-AI

A real-time, interruptible conversational AI voice agent using LiveKit and the Gemini API.

## Overview
This repository contains the source code for an advanced Voice AI agent built for the Samsung PRISM GenAI Hackathon 3.0.

### Key Features
- **Real-Time Audio Processing:** Ultra-low latency voice streaming.
- **Native Interruptibility:** The agent can process user speech mid-sentence, halting its own output gracefully.
- **Contextual Rollback:** Accurate state management ensuring the agent retains context even when interrupted.

## Setup and Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your `.env` variables with your LiveKit and Gemini API keys.
3. Run the agent.

## Evaluation
The `fdb3` directory contains the evaluation suite to benchmark the agent against the baseline for Tool Call Accuracy, Pass Rate, and Tool Call Latency.
