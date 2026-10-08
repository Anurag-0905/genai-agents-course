# ⚙️ Enterprise LLM Infrastructure & Agentic Workflows

**Maintainer:** Anurag Sharma  
**Focus:** Process Optimization, LLM Deployment Economics, and Agentic Routing

## 📌 Executive Overview
This repository contains technical audits, benchmarks, and prototype deployments of Large Language Models (LLMs) and agentic frameworks. The objective is to bridge the gap between raw data science concepts and operational business strategy by evaluating model deployment costs, latency trade-offs, vector embeddings, and deterministic routing logic for enterprise use cases.

## 🛠️ Core Competencies & Tech Stack
* **LLM Orchestration & APIs:** Groq, Google Gemini, Ollama (Local open-weight models).
* **Process Analysis:** Evaluating Time to First Token (TTFT), Tokens per Second (TPS), and quantization hardware constraints.
* **Agentic Frameworks:** Intent classification, multi-provider routing, and deterministic tool calling.
* **Tech Stack:** Python, `uv` (dependency management), NumPy, Matplotlib, `tiktoken`.

---

## 📊 Analytical Deep Dives & Benchmarks

### 1. Tokenomics, Pricing Overheads, & Context Constraints (Session 09)
* **Objective:** Audit the hidden costs of LLM API usage and memory limitations.
* **Business Impact:** Identified a severe "Non-English Token Penalty"—regional languages (e.g., Telugu) consume exponentially more tokens than English, heavily inflating API costs. Proved via 20-turn conversation simulations that developers must actively build sliding memory windows to prevent breaking the 8,192-token context limit in production.
* **File:** `llm/s09_tokens.ipynb`

### 2. Deployment Landscape Matrix & Cost-Benefit Analysis (Session 10)
* **Objective:** Route LLMs based on hard constraints (data privacy, latency) and operational costs.
* **Business Impact:** Built a weighted selection matrix for three workloads (Public FAQ, PII Document Analysis, Live Agent Assist). Demonstrated that handling Customer PII requires sacrificing cloud API speed for localized, open-weight GPU deployments to maintain data sovereignty, while public FAQs can be routed to highly cost-efficient cloud models instead of overpriced flagship tiers.
* **File:** `llm/s10_model_matrix.ipynb`

### 3. Multi-Provider Routing & Stochastic Variance Control (Session 11)
* **Objective:** Evaluate the risk of stochastic sampling on deterministic business logic.
* **Business Impact:** Conducted a temperature sweep (0.0 to 1.0) on ambiguous support tickets. Proved that any LLM deployed for intent routing or structured data extraction must be strictly locked to `temperature=0.0` to prevent downstream pipeline failures caused by label drift.
* **File:** `llm/s11_providers.ipynb`

### 4. Local Compute Constraints & Quantization Economics (Session 12)
* **Objective:** Benchmark the feasibility of running open-weight LLMs on consumer hardware.
* **Business Impact:** Quantified the necessity of INT4 precision compression to fit 20B+ parameter models into standard VRAM budgets. Benchmarked local throughput against hosted APIs, concluding that local deployments are optimal for asynchronous data pipelines (like document reading) but introduce too much TTFT latency for live conversational UI.
* **File:** `llm/s12_local_models.ipynb`

### 5. Multimodal ETL & OCR Validation Routing (Session 13)
* **Objective:** Design a deterministic processing pipeline that ingests raw image scans (e.g., Identity Documents) using Vision models and extracts strictly validated JSON records.
* **Business Impact:** Demonstrated that multimodal image processing exponentially increases API token costs, necessitating batch-processing architectures for high-volume pipelines. Proved that while LLM JSON schemas guarantee syntactic structure, factual accuracy and conditional business rules (e.g., date logic, document types) must be enforced by deterministic code (Pydantic). Established the absolute necessity of Human-in-the-Loop exception routing for failed OCR reads rather than relying on endless, token-burning AI retries.
* **File:** `llm/s13_vision_structured.ipynb`

---

## ⚙️ Execution & Reproduction

This workspace relies on `uv` for lightning-fast dependency synchronization. 

```bash
# Clone the repository
git clone [https://github.com/Anurag-0905/genai-agents-course.git](https://github.com/Anurag-0905/genai-agents-course.git)
cd genai-agents-course

# Sync dependencies
uv sync

# Set up environment variables for API routing
cp .env.example .env
# Edit .env with your specific GROQ_API_KEY and GEMINI_API_KEY

# Launch the Jupyter Lab environment
uv run jupyter lab