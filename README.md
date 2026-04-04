# ⬡ OffshoreIQ

> **Knowledge Graph + LLM Talent Matching for Moroccan Nearshore Offshoring**
> Multi-Agent System · Neo4j · LangGraph · FastAPI · Groq LLM

---

## 📸 Screenshots

### Main Interface
![Main UI](docs/screenshots/01-main-ui.png)

### RFP Analysis in Action
![Analysis Result](docs/screenshots/02-analysis-result.png)

### Live Knowledge Graph (D3.js + Neo4j)
![Knowledge Graph](docs/screenshots/03-knowledge-graph.png)

### Multi-Agent Pipeline Trace
![Agent Trace](docs/screenshots/04-agent-trace.png)

---

## 🎯 What is OffshoreIQ?

OffshoreIQ is a **Proof of Concept** that demonstrates how **structured graph retrieval** combined with a **Multi-Agent LLM System** can solve a real problem in Morocco's nearshore IT offshoring sector.

### The Problem

When a French bank sends an RFP to a Moroccan IT firm saying:

> *"We need a team with SAP S/4HANA expertise, GDPR compliance experience, French-speaking, for an 18-month banking modernization project"*

...the firm's business developer currently does this **manually**: searches spreadsheets, calls team leads, digs through old CVs, and pieces together a response over 2–4 weeks. There's no system that understands the relationships between engineers, their past projects, the clients those projects served, the compliance frameworks involved, and the certifications they hold — all at once.

### The Solution

OffshoreIQ models the entire talent ecosystem as a **knowledge graph in Neo4j** and uses a **4-agent LangGraph pipeline** to go from raw RFP text to a ranked team recommendation + written proposal in under 15 seconds.

### Honest Technical Note — Graph Retrieval vs. GraphRAG

This project uses **structured graph retrieval**, not GraphRAG in the strict sense. Here is the difference:

| | This project | True GraphRAG (e.g. Microsoft's definition) |
|---|---|---|
| **How retrieval works** | Cypher queries with typed relationships | Vector/cosine similarity search first, then graph traversal to enrich results |
| **Embeddings used?** | ❌ No | ✅ Yes — text is embedded and searched by semantic similarity |
| **Entry point into the graph** | Exact match on LLM-extracted keywords | Approximate match via embedding distance |
| **Strengths** | Precise, explainable, fast, no GPU needed | Handles fuzzy/natural language queries better |

**Why structured graph retrieval is still the right choice here:** Agent 1 uses an LLM to normalize free-text RFPs into clean structured terms before any graph query runs. Once you have `skills: ["SAP S/4HANA", "GDPR"]` as structured input, exact graph traversal is strictly more accurate than cosine similarity — you want the engineer who *actually worked* on a GDPR project, not the one whose CV *sounds most like* GDPR.

Adding true GraphRAG (embeddings + vector index on project descriptions) is listed in the roadmap below.

---

## 🏗️ Architecture — What Actually Happens

Here is the exact sequence of events when you click **Analyze**:

```
Browser → POST /api/v1/rfp/analyze (raw RFP text)
              │
              ▼
      ┌───────────────────────────────────────────────────────┐
      │            LangGraph StateGraph Pipeline              │
      │                                                       │
      │  State object flows through 5 nodes sequentially.    │
      │  Each node reads from state, writes back to state.   │
      │  The `agent_trace` key accumulates across all nodes. │
      └───────────────────────────────────────────────────────┘
              │
    ┌─────────▼──────────┐
    │  ① parse_rfp_node  │  RFPParserAgent
    │                    │  Sends the raw RFP to Groq LLM with a strict
    │                    │  system prompt that demands JSON-only output.
    │                    │  Extracts: skills[], compliance_frameworks[],
    │                    │  certifications[], sector, languages, seniority.
    │                    │  Falls back to safe defaults if JSON parsing fails.
    └─────────┬──────────┘
              │  state.requirements = { skills: [...], sector: "Banking", ... }
    ┌─────────▼──────────┐
    │  ② build_team_node │  TeamBuilderAgent  ← CORE GRAPH RETRIEVAL NODE
    │                    │
    │                    │  Runs 4 multi-hop Cypher queries against Neo4j:
    │                    │
    │                    │  Query A — Skill match (2 hops):
    │                    │  (Engineer)-[:HAS_SKILL {proficiency}]→(Skill)
    │                    │  Filter by proficiency rank
    │                    │
    │                    │  Query B — Compliance experience (3 hops):
    │                    │  (Engineer)-[:WORKED_ON]→(Project)
    │                    │             -[:REQUIRED_COMPLIANCE]→(ComplianceFramework)
    │                    │  Finds engineers with HANDS-ON compliance history
    │                    │  (not just self-declared on a CV)
    │                    │
    │                    │  Query C — Sector experience (4 hops):
    │                    │  (Engineer)-[:WORKED_ON]→(Project)
    │                    │             -[:FOR_CLIENT]→(Client)
    │                    │             -[:IN_SECTOR]→(Sector)
    │                    │
    │                    │  Query D — Certification match (2 hops):
    │                    │  (Engineer)-[:HOLDS_CERT]→(Certification)
    │                    │
    │                    │  Merges all candidate IDs, fetches full profiles,
    │                    │  then asks Groq LLM to score 0.0–1.0 based on fit.
    └─────────┬──────────┘
              │  state.team_engineers = [{ id, name, score, matching_skills, ... }]
    ┌─────────▼──────────┐
    │  ③ analyze_gaps_   │  GapAnalystAgent
    │    node            │
    │                    │  Graph query: which required skills has NO engineer
    │                    │  in the proposed team?
    │                    │  Cypher: UNWIND required_skills, LEFT JOIN against
    │                    │  team HAS_SKILL edges, return skills with 0 matches.
    │                    │
    │                    │  LLM generates Morocco-specific suggestions:
    │                    │  Simplon.co, UM6P, ENSIAS, partner ESN firms.
    └─────────┬──────────┘
              │  state.gaps = [{ skill, suggestion }]
    ┌─────────▼──────────┐
    │  ④ draft_proposal_ │  ProposalDrafterAgent
    │    node            │
    │                    │  Builds context block from all prior agent outputs
    │                    │  and sends to Groq LLM with a business development
    │                    │  persona. Output: 400-word proposal email.
    └─────────┬──────────┘
              │  state.proposal = "Dear Client, We are pleased to present..."
    ┌─────────▼──────────┐
    │  ⑤ build_graph_    │  GraphVisualizationAgent (pure Neo4j, no LLM)
    │    data_node       │
    │                    │  Returns all nodes + edges connected to matched
    │                    │  engineers as { nodes, edges } for D3.js rendering.
    └─────────┬──────────┘
              ▼
      FastAPI → JSON → Browser renders engineer cards, D3 graph, proposal
```

### The Graph Schema (Neo4j)

```
(Engineer)-[:HAS_SKILL {proficiency: "expert|advanced|intermediate"}]→(Skill)
(Engineer)-[:HOLDS_CERT]→(Certification)
(Engineer)-[:WORKED_ON]→(Project)
(Engineer)-[:WORKS_AT]→(ESNFirm)
(Project)-[:FOR_CLIENT]→(Client)
(Project)-[:REQUIRED_SKILL]→(Skill)
(Project)-[:REQUIRED_COMPLIANCE]→(ComplianceFramework)
(Project)-[:DELIVERED_BY]→(ESNFirm)
(Client)-[:IN_SECTOR]→(Sector)
```

---

## 🤖 The 4 Agents

### Agent 1 — RFPParserAgent
**Input:** Raw RFP text | **Output:** Structured JSON

Uses Groq LLM with a strict JSON-only system prompt. Strips markdown artifacts with regex before parsing. Falls back to safe defaults on parse failure so the pipeline never crashes.

**Why LLM here:** RFPs are multilingual and inconsistent. "RGPD" (French) and "GDPR" (English) are the same thing — the LLM normalizes this before any graph query runs.

### Agent 2 — TeamBuilderAgent *(graph retrieval core)*
**Input:** Structured requirements | **Output:** Ranked engineers with scores

Runs 4 Cypher queries traversing different relationship paths, merges candidates, fetches full profiles, then asks the LLM to score each 0.0–1.0. The LLM adds nuance (years of experience, language fit) that pure graph queries can't express.

**Why not just LLM for matching:** It has no knowledge of your database. Without graph retrieval feeding it real profiles, it hallucinates.

### Agent 3 — GapAnalystAgent
**Input:** Required skills + team engineer IDs | **Output:** Uncovered skills + suggestions

One Cypher set-difference query finds gaps. LLM generates Morocco-specific mitigation suggestions per gap.

### Agent 4 — ProposalDrafterAgent
**Input:** All prior agent outputs | **Output:** 400-word client proposal

Grounded in real graph data — no hallucinated engineers, no placeholder brackets.

---

## 🕸️ Why Graph Retrieval Beats Cosine Similarity Here

| Query | Cosine / Vector Search | Structured Graph Retrieval |
|---|---|---|
| "Find engineers who know SAP" | ✅ Finds CVs mentioning SAP | ✅ Same |
| "Find engineers with SAP **and** GDPR **hands-on** experience" | ⚠️ Approximate — depends on CV wording | ✅ Exact — traverses actual project records |
| "Find team whose **combined** skills cover all requirements" | ❌ Cannot reason about teams | ✅ Multi-node graph traversal |
| "Engineers who worked on banking projects **for French clients**" | ❌ Cannot follow 4-hop relationships | ✅ `(eng)→(proj)→(client)→(sector)` |
| "Which skills are **missing** from this specific team?" | ❌ Structurally impossible | ✅ Set difference in one Cypher query |

The signature 4-hop query:
```cypher
MATCH (eng:Engineer)-[:WORKED_ON]->(p:Project)
      -[:FOR_CLIENT]->(cl:Client)
      -[:IN_SECTOR]->(s:Sector {name: $sector})
WITH eng, collect(DISTINCT cl.name) AS clients, count(DISTINCT p) AS projectCount
RETURN eng.id, eng.name, clients, projectCount
ORDER BY projectCount DESC
```

No embedding model produces this. It requires following 4 typed edges and aggregating across the traversal.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Neo4j Desktop **or** Docker
- Free [Groq API key](https://console.groq.com) (30 seconds)

### Option A — Local (~5 min)

```bash
git clone https://github.com/Othamane/OffshoreIQ.git
cd offshoreiq
python -m venv venv
venv\Scripts\activate        # Windows: or source venv/bin/activate on Mac/Linux
pip install -r requirements.txt
cp .env.example .env         # fill in GROQ_API_KEY and NEO4J_PASSWORD
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` → click **⟳ Seed Database** → paste an RFP → **Analyze**.

### Option B — Docker Compose (~10 min, Neo4j included)

```bash
cp .env.example .env         # set GROQ_API_KEY
docker compose up --build
curl -X POST http://localhost:8000/api/v1/admin/seed
```

- App: `http://localhost:8000`
- Neo4j Browser: `http://localhost:7474` (neo4j / offshoreiq123)

---

## 🔑 Groq API Key (Free)

1. [console.groq.com](https://console.groq.com) → sign up → Create API Key
2. Paste into `.env` as `GROQ_API_KEY`
3. Set `LLM_MODEL=llama-3.3-70b-versatile`

| Model | Speed | Quality |
|---|---|---|
| `llama-3.3-70b-versatile` | Fast | ⭐⭐⭐⭐⭐ ← use this |
| `llama-3.1-8b-instant` | Fastest | ⭐⭐⭐ |
| `mixtral-8x7b-32768` | Medium | ⭐⭐⭐⭐ |

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/admin/seed` | Seed Neo4j with simulated data |
| `POST` | `/api/v1/rfp/analyze` | Run the full MAS pipeline |
| `GET` | `/docs` | Swagger UI |

---

## 🌍 Simulated Dataset

| Entity | Count | Examples |
|---|---|---|
| Engineers | 8 | Youssef El Amrani (Casablanca, 6y), Sara Benali (Rabat, 4y)... |
| ESN Firms | 5 | CGI Morocco, Capgemini Maroc, SQLI Maroc, Devoteam, NearShore Makers |
| Clients | 8 | BNP Paribas, AXA, Orange SA, Santander, TotalEnergies... |
| Projects | 8 | Core Banking Modernization (18m), Cyber Risk Platform (14m)... |
| Skills | 25 | Python, SAP S/4HANA, Kubernetes, GDPR Compliance, Salesforce... |
| Certifications | 8 | AWS Solutions Architect, SAP S/4HANA Certified, CISSP... |
| Compliance Frameworks | 5 | GDPR, ISO 27001, PCI-DSS, SOC 2, HDS |
| Relationships | 40+ | HAS_SKILL, WORKED_ON, FOR_CLIENT, IN_SECTOR, HOLDS_CERT... |

---

## 🧪 Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

No live Neo4j or Groq API needed — pipeline is mocked.

---

## 🔮 Roadmap

| Extension | Effort | What it adds |
|---|---|---|
| **True GraphRAG** — `sentence-transformers` on project descriptions + Neo4j vector index | Medium | Semantic search as graph entry point — makes this genuinely hybrid |
| Real LinkedIn data ingestion | Medium | Real engineer profiles instead of simulated data |
| JWT auth | Low | Multi-tenant access per ESN firm |
| PDF proposal export | Low | Download proposal as formatted PDF |
| Neo4j GDS centrality scoring | Medium | Rank by network influence, not just skill count |
| Availability nodes | Medium | `(Engineer)-[:AVAILABLE_FROM]→(Date)` |

---

## 🇲🇦 Moroccan Market Context

Morocco's nearshore IT sector serves 500+ ESN firms targeting French and Spanish multinationals, generating ~$2B/year with ~100,000 engineers. Key hubs: Casablanca (CFC, Casanearshore), Rabat (Technopolis), Marrakech.

The RFP-matching process this project automates currently takes 2–4 weeks manually at firms like SQLI Maroc, Devoteam Maroc, and Capgemini Maroc.

---

## 📄 License

MIT

---

*Stack: FastAPI · Neo4j · LangGraph · LangChain · Groq LLM · D3.js*
