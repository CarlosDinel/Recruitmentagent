# AIcruiter - AI-Powered Recruitment Platform

An intelligent multi-agent recruitment system that automates candidate discovery, evaluation, and outreach using AI.

## Features

- **Hybrid Candidate Search** - Combines LinkedIn API with MongoDB for efficient candidate discovery
- **AI Evaluation** - GPT-powered candidate scoring with relevance grading (A/B/C/D)
- **Smart Filtering** - Location-based and skill-based candidate relevance matching
- **Multi-Channel Outreach** - LinkedIn and email campaign management
- **REST API** - Full API for integration with external systems

## Quick Start

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd Recruitment-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Create a `.env` file with:

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# MongoDB
MONGO_URI=mongodb+srv://...
MONGO_DATABASE=AIcruiter

# LinkedIn (Unipile)
UNIPILE_API_KEY=...
UNIPILE_ACCOUNT_ID=...
```

### Running

**Start API Server:**
```bash
python main.py api --port 8000
```

**Access:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Usage

### Search Candidates

```bash
curl -X POST "http://localhost:8000/api/search/candidates" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "1234567890",
    "search_criteria": {
      "keywords": ["Developer", "Python"],
      "location": "Netherlands",
      "job_title": "Software Engineer"
    },
    "target_count": 50
  }'
```

### Get Project Candidates

```bash
curl "http://localhost:8000/api/search/candidates/{project_id}"
```

### Evaluate Candidates

```bash
curl -X POST "http://localhost:8000/api/evaluation/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "1234567890",
    "candidate_ids": ["candidate_1", "candidate_2"]
  }'
```

## Project Structure

```
Recruitment-agent/
├── main.py                 # Application entry point
├── agents/                 # Core agents
│   ├── database_agent.py   # Database operations
│   ├── recruitment_executive.py
│   └── sourcing_manager_unified.py
├── sub_agents/             # Specialized agents
│   ├── candidate_serching_agent.py
│   ├── candidate_evaluation_agent.py
│   └── profile_scraping_agent.py
├── src/
│   ├── application/        # Use cases & orchestrators
│   ├── domain/             # Domain models
│   ├── infrastructure/     # External services
│   └── presentation/       # API routes & CLI
├── tools/                  # LinkedIn & database tools
├── config/                 # Configuration
└── test/                   # Test suite
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              REST API / CLI                      │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│         RecruitmentExecutiveAgent               │
│         (Main Orchestrator)                      │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│ Sourcing  │  │Evaluation │  │ Outreach  │
│ Manager   │  │  Agent    │  │ Manager   │
└─────┬─────┘  └───────────┘  └───────────┘
      │
      ▼
┌───────────────────────────────────────────────┐
│         CandidateSearchingAgent               │
│   (Hybrid: MongoDB + LinkedIn Search)         │
└─────────────────────┬─────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌───────────────┐          ┌───────────────┐
│   MongoDB     │          │  LinkedIn API │
│  (prospects)  │          │   (Unipile)   │
└───────────────┘          └───────────────┘
```

## Relevance Scoring

Candidates are scored (0-100) based on:

| Factor | Points | Description |
|--------|--------|-------------|
| Location | 40 | Match with target location |
| Job Title | 30 | Keywords in title/headline |
| Skills | 20 | Matching required skills |
| Profile | 10 | Profile completeness |

**Grades:**
- **A** (90+): Excellent match
- **B** (70-89): Good match  
- **C** (50-69): Moderate match
- **D** (30-49): Low match
- **F** (<30): Filtered out

## Development

### Run Tests

```bash
pytest test/ -v
```

### Code Style

```bash
# Format
black .

# Lint
flake8 .
```

## Tech Stack

- **Python 3.11+**
- **FastAPI** - REST API framework
- **MongoDB** - Database
- **LangChain** - AI agent framework
- **OpenAI GPT** - Language model
- **Unipile** - LinkedIn API provider

## License

MIT
