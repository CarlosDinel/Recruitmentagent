# Clean Architecture Refactoring Plan

## Executive Summary

This document outlines the complete refactoring plan to transform the Recruitment Agent system from its current structure to a Clean Architecture pattern while **preserving 100% of existing functionality**.

**Current State**: 95% production-ready multi-agent recruitment system with 14/14 passing tests
**Target State**: Clean Architecture compliant system with improved maintainability, testability, and scalability
**Guarantee**: All 14 tests will continue to pass throughout and after refactoring

---

## Clean Architecture Overview

Clean Architecture organizes code into concentric layers with strict dependency rules:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│              (CLI, API, Web Interface)                       │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                          │
│         (Use Cases, Orchestration, Workflows)                │
├─────────────────────────────────────────────────────────────┤
│                     Domain Layer                             │
│      (Business Logic, Entities, Value Objects)               │
├─────────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                         │
│  (External Services, Database, APIs, AI Models)              │
└─────────────────────────────────────────────────────────────┘
```

**Dependency Rule**: Inner layers never depend on outer layers
- Domain knows nothing about Infrastructure, Application, or Presentation
- Application depends on Domain but not on Infrastructure or Presentation
- Infrastructure and Presentation depend on Application and Domain

---

## New Directory Structure

```
recruitment-agent/
├── src/
│   ├── domain/                           # Core Business Logic (No External Dependencies)
│   │   ├── __init__.py
│   │   ├── entities/                     # Business entities
│   │   │   ├── __init__.py
│   │   │   ├── candidate.py              # Candidate entity
│   │   │   ├── project.py                # Project entity
│   │   │   ├── campaign.py               # Campaign entity
│   │   │   ├── outreach_message.py       # Message entity
│   │   │   └── recruitment_request.py    # Request entity
│   │   │
│   │   ├── value_objects/                # Immutable value objects
│   │   │   ├── __init__.py
│   │   │   ├── candidate_id.py
│   │   │   ├── project_id.py
│   │   │   ├── skill_set.py
│   │   │   ├── contact_info.py
│   │   │   └── evaluation_score.py
│   │   │
│   │   ├── enums/                        # Business enums
│   │   │   ├── __init__.py
│   │   │   ├── candidate_status.py
│   │   │   ├── outreach_channel.py
│   │   │   ├── evaluation_result.py
│   │   │   └── workflow_stage.py
│   │   │
│   │   ├── repositories/                 # Repository interfaces (abstract)
│   │   │   ├── __init__.py
│   │   │   ├── candidate_repository.py
│   │   │   ├── project_repository.py
│   │   │   └── campaign_repository.py
│   │   │
│   │   ├── services/                     # Domain services (business logic)
│   │   │   ├── __init__.py
│   │   │   ├── candidate_matching_service.py
│   │   │   ├── candidate_evaluation_service.py
│   │   │   └── deduplication_service.py
│   │   │
│   │   └── exceptions/                   # Domain exceptions
│   │       ├── __init__.py
│   │       ├── candidate_not_found.py
│   │       ├── invalid_project.py
│   │       └── validation_error.py
│   │
│   ├── application/                      # Application Business Rules
│   │   ├── __init__.py
│   │   ├── use_cases/                    # Use case implementations
│   │   │   ├── __init__.py
│   │   │   ├── recruitment/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── process_recruitment_request.py
│   │   │   │   ├── create_recruitment_project.py
│   │   │   │   └── monitor_recruitment_pipeline.py
│   │   │   │
│   │   │   ├── sourcing/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── search_candidates.py
│   │   │   │   ├── evaluate_candidates.py
│   │   │   │   ├── enrich_candidate_profiles.py
│   │   │   │   └── optimize_candidate_pool.py
│   │   │   │
│   │   │   └── outreach/
│   │   │       ├── __init__.py
│   │   │       ├── prioritize_candidates.py
│   │   │       ├── generate_personalized_message.py
│   │   │       ├── send_email_outreach.py
│   │   │       ├── send_linkedin_outreach.py
│   │   │       └── track_outreach_responses.py
│   │   │
│   │   ├── workflows/                    # Orchestrated workflows (formerly flows/)
│   │   │   ├── __init__.py
│   │   │   ├── recruitment_executive_workflow.py
│   │   │   ├── sourcing_manager_workflow.py
│   │   │   └── outreach_manager_workflow.py
│   │   │
│   │   ├── orchestrators/                # High-level orchestrators (formerly agents/)
│   │   │   ├── __init__.py
│   │   │   ├── recruitment_executive.py
│   │   │   ├── sourcing_manager.py
│   │   │   └── outreach_manager.py
│   │   │
│   │   ├── dtos/                         # Data Transfer Objects
│   │   │   ├── __init__.py
│   │   │   ├── recruitment_request_dto.py
│   │   │   ├── candidate_dto.py
│   │   │   ├── project_dto.py
│   │   │   └── outreach_dto.py
│   │   │
│   │   ├── interfaces/                   # Application interfaces (ports)
│   │   │   ├── __init__.py
│   │   │   ├── ai_service.py             # AI/LLM interface
│   │   │   ├── search_service.py         # Candidate search interface
│   │   │   ├── email_service.py          # Email interface
│   │   │   ├── linkedin_service.py       # LinkedIn interface
│   │   │   └── scraping_service.py       # Profile scraping interface
│   │   │
│   │   └── state/                        # Application state management
│   │       ├── __init__.py
│   │       ├── recruitment_state.py
│   │       ├── sourcing_state.py
│   │       └── outreach_state.py
│   │
│   ├── infrastructure/                   # External Concerns (Implementations)
│   │   ├── __init__.py
│   │   ├── persistence/                  # Database implementations
│   │   │   ├── __init__.py
│   │   │   ├── mongodb/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── mongodb_client.py
│   │   │   │   ├── mongodb_candidate_repository.py
│   │   │   │   ├── mongodb_project_repository.py
│   │   │   │   └── mongodb_campaign_repository.py
│   │   │   │
│   │   │   └── memory/                   # In-memory implementations (for testing)
│   │   │       ├── __init__.py
│   │   │       ├── memory_candidate_repository.py
│   │   │       └── memory_project_repository.py
│   │   │
│   │   ├── ai/                           # AI/LLM implementations
│   │   │   ├── __init__.py
│   │   │   ├── openai_service.py
│   │   │   ├── langchain_service.py
│   │   │   └── prompts/                  # Moved from root prompts/
│   │   │       ├── __init__.py
│   │   │       ├── recruitment_prompts.py
│   │   │       ├── sourcing_prompts.py
│   │   │       ├── evaluation_prompts.py
│   │   │       └── ghostwriter_prompts.py
│   │   │
│   │   ├── external_services/            # External API integrations
│   │   │   ├── __init__.py
│   │   │   ├── linkedin/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── linkedin_api_client.py
│   │   │   │   └── linkedin_service_impl.py
│   │   │   │
│   │   │   ├── email/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── smtp_client.py
│   │   │   │   └── email_service_impl.py
│   │   │   │
│   │   │   └── scraping/
│   │   │       ├── __init__.py
│   │   │       ├── profile_scraper.py
│   │   │       └── scraping_service_impl.py
│   │   │
│   │   ├── search/                       # Search implementations
│   │   │   ├── __init__.py
│   │   │   ├── linkedin_search.py
│   │   │   └── search_service_impl.py
│   │   │
│   │   └── config/                       # Configuration (moved from root config/)
│   │       ├── __init__.py
│   │       ├── settings.py
│   │       ├── environment.py
│   │       └── dependency_injection.py   # DI container
│   │
│   └── presentation/                     # User Interface Layer
│       ├── __init__.py
│       ├── cli/                          # Command-line interface
│       │   ├── __init__.py
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── test_command.py
│       │   │   ├── process_command.py
│       │   │   ├── interactive_command.py
│       │   │   ├── batch_command.py
│       │   │   └── api_command.py
│       │   │
│       │   └── main.py                   # CLI entry point (from root main.py)
│       │
│       ├── api/                          # REST API (FastAPI)
│       │   ├── __init__.py
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── recruitment.py
│       │   │   ├── candidates.py
│       │   │   ├── projects.py
│       │   │   └── health.py
│       │   │
│       │   ├── schemas/                  # API schemas (Pydantic)
│       │   │   ├── __init__.py
│       │   │   ├── recruitment_schemas.py
│       │   │   └── candidate_schemas.py
│       │   │
│       │   └── main.py                   # FastAPI app
│       │
│       └── web/                          # Future web interface (placeholder)
│           └── __init__.py
│
├── tests/                                # Tests mirror src/ structure
│   ├── __init__.py
│   ├── unit/                             # Unit tests
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   │
│   ├── integration/                      # Integration tests
│   │   ├── workflows/
│   │   └── repositories/
│   │
│   ├── e2e/                              # End-to-end tests
│   │   └── test_complete_flow.py         # Migrated from test/test_complete_mock.py
│   │
│   └── fixtures/                         # Test fixtures and mocks
│       ├── __init__.py
│       ├── mock_repositories.py
│       ├── mock_services.py
│       └── test_data.py
│
├── scripts/                              # Utility scripts
│   ├── migrate_data.py
│   └── run_tests.sh
│
├── docs/                                 # Documentation
│   ├── architecture.md
│   ├── api_documentation.md
│   └── deployment_guide.md
│
├── main.py                               # Backward compatibility entry point
├── requirements.txt
├── README.md
├── .env
├── .gitignore
└── pyproject.toml                        # New: Package configuration
```

---

## Migration Strategy

### Phase 1: Domain Layer (Week 1)
**Goal**: Extract pure business logic with zero external dependencies

#### 1.1 Create Domain Entities
- Extract candidate data structure → `domain/entities/candidate.py`
- Extract project data structure → `domain/entities/project.py`
- Extract campaign data structure → `domain/entities/campaign.py`
- Extract message data structure → `domain/entities/outreach_message.py`

#### 1.2 Create Value Objects
- Extract IDs → `domain/value_objects/candidate_id.py`, `project_id.py`
- Extract skill handling → `domain/value_objects/skill_set.py`
- Extract contact info → `domain/value_objects/contact_info.py`

#### 1.3 Create Domain Services
- Extract candidate matching logic from `sub_agents/candidate_evaluation_agent.py`
- Extract deduplication logic (LinkedIn URL uniqueness)

#### 1.4 Define Repository Interfaces
- Abstract repository for candidates
- Abstract repository for projects
- Abstract repository for campaigns

**Testing**: All existing tests continue to pass

---

### Phase 2: Infrastructure Layer (Week 2)
**Goal**: Implement concrete infrastructure adapters

#### 2.1 MongoDB Repository Implementations
- Implement `mongodb_candidate_repository.py` from `tools/database_agent_tools.py`
- Implement `mongodb_project_repository.py` from `tools/get_projects.py`
- Migrate MongoDB client setup from `agents/database_agent.py`

#### 2.2 AI Service Implementations
- Migrate OpenAI/LangChain setup from current agents
- Move all prompts from `prompts/` to `infrastructure/ai/prompts/`
- Create unified AI service interface

#### 2.3 External Service Implementations
- Migrate LinkedIn API client from `sub_agents/LinkedIn_outreach_agent.py`
- Migrate Email service from `sub_agents/email_outreach_agent.py`
- Migrate scraping logic from `sub_agents/profile_scraping_agent.py`

#### 2.4 Configuration Migration
- Move `config/config.py` to `infrastructure/config/settings.py`
- Create dependency injection container

**Testing**: All existing tests continue to pass with new repository implementations

---

### Phase 3: Application Layer (Week 3)
**Goal**: Implement use cases and orchestration workflows

#### 3.1 Create Use Cases
**Sourcing Use Cases**:
- `search_candidates.py` from `sub_agents/candidate_serching_agent.py`
- `evaluate_candidates.py` from `sub_agents/candidate_evaluation_agent.py`
- `enrich_candidate_profiles.py` from `sub_agents/profile_scraping_agent.py`

**Outreach Use Cases**:
- `generate_personalized_message.py` from `sub_agents/ghostwriter_agent.py`
- `send_email_outreach.py` from `sub_agents/email_outreach_agent.py`
- `send_linkedin_outreach.py` from `sub_agents/LinkedIn_outreach_agent.py`

**Recruitment Use Cases**:
- `process_recruitment_request.py` from `agents/recruitment_executive.py`
- `create_recruitment_project.py` from database agent logic

#### 3.2 Migrate Workflows
- Move `flows/recruitment_executive_flow.py` → `application/workflows/recruitment_executive_workflow.py`
- Move `flows/sourcing_manager_flow.py` → `application/workflows/sourcing_manager_workflow.py`
- Move `flows/outreach_manager_flow.py` → `application/workflows/outreach_manager_workflow.py`

#### 3.3 Create Orchestrators
- Refactor `agents/recruitment_executive.py` → `application/orchestrators/recruitment_executive.py`
- Refactor `agents/sourcing_manager_unified.py` → `application/orchestrators/sourcing_manager.py`

#### 3.4 Migrate State Management
- Move `state/agent_state.py` → `application/state/recruitment_state.py`
- Move `state/sourcing_manager_state.py` → `application/state/sourcing_state.py`

**Testing**: All existing tests continue to pass with refactored use cases

---

### Phase 4: Presentation Layer (Week 4)
**Goal**: Separate user interfaces from business logic

#### 4.1 CLI Refactoring
- Extract CLI commands from `main.py` to `presentation/cli/commands/`
- Create command pattern for each CLI mode (test, process, interactive, batch, api)
- Keep backward-compatible `main.py` in root

#### 4.2 API Development
- Extract FastAPI routes from `main.py` to `presentation/api/routes/`
- Create proper API schemas with Pydantic
- Implement proper error handling and validation

#### 4.3 Entry Points
- Create `src/presentation/cli/main.py` (new CLI entry)
- Create `src/presentation/api/main.py` (new API entry)
- Keep `main.py` in root as backward-compatible launcher

**Testing**: All existing tests continue to pass, CLI and API work identically

---

### Phase 5: Testing Refactoring (Week 5)
**Goal**: Restructure tests to match new architecture

#### 5.1 Test Organization
- Create `tests/unit/` for unit tests
- Create `tests/integration/` for integration tests
- Create `tests/e2e/` for end-to-end tests
- Migrate `test/test_complete_mock.py` → `tests/e2e/test_complete_flow.py`

#### 5.2 Test Utilities
- Create mock repositories in `tests/fixtures/mock_repositories.py`
- Create mock services in `tests/fixtures/mock_services.py`
- Create reusable test data in `tests/fixtures/test_data.py`

#### 5.3 Additional Test Coverage
- Add unit tests for domain entities
- Add unit tests for value objects
- Add unit tests for domain services
- Add integration tests for repositories
- Add integration tests for workflows

**Testing**: All 14 existing tests pass + new tests added

---

### Phase 6: Documentation & Cleanup (Week 6)
**Goal**: Complete documentation and remove legacy code

#### 6.1 Architecture Documentation
- Create `docs/architecture.md` with Clean Architecture diagrams
- Document dependency injection patterns
- Document workflow patterns

#### 6.2 Code Cleanup
- Remove old `agents/` directory (after migration)
- Remove old `sub_agents/` directory (after migration)
- Remove old `flows/` directory (after migration)
- Remove old `prompts/` directory (after migration)
- Remove old `tools/` directory (after migration)
- Update `.gitignore` for new structure

#### 6.3 Package Configuration
- Create `pyproject.toml` for modern Python packaging
- Configure package metadata
- Configure development dependencies

**Testing**: All tests pass, system operates identically

---

## Detailed File Mapping

### Current → New Architecture Mapping

| Current File | New Location | Layer |
|-------------|--------------|-------|
| `main.py` | `src/presentation/cli/main.py` + backward-compatible root `main.py` | Presentation |
| `agents/recruitment_executive.py` | `src/application/orchestrators/recruitment_executive.py` | Application |
| `agents/sourcing_manager_unified.py` | `src/application/orchestrators/sourcing_manager.py` | Application |
| `agents/database_agent.py` | Split: `src/domain/repositories/` + `src/infrastructure/persistence/mongodb/` | Domain + Infrastructure |
| `sub_agents/candidate_serching_agent.py` | `src/application/use_cases/sourcing/search_candidates.py` | Application |
| `sub_agents/candidate_evaluation_agent.py` | `src/application/use_cases/sourcing/evaluate_candidates.py` + `src/domain/services/candidate_evaluation_service.py` | Application + Domain |
| `sub_agents/profile_scraping_agent.py` | `src/application/use_cases/sourcing/enrich_candidate_profiles.py` | Application |
| `sub_agents/email_outreach_agent.py` | `src/application/use_cases/outreach/send_email_outreach.py` | Application |
| `sub_agents/LinkedIn_outreach_agent.py` | `src/application/use_cases/outreach/send_linkedin_outreach.py` | Application |
| `sub_agents/ghostwriter_agent.py` | `src/application/use_cases/outreach/generate_personalized_message.py` | Application |
| `flows/recruitment_executive_flow.py` | `src/application/workflows/recruitment_executive_workflow.py` | Application |
| `flows/sourcing_manager_flow.py` | `src/application/workflows/sourcing_manager_workflow.py` | Application |
| `flows/outreach_manager_flow.py` | `src/application/workflows/outreach_manager_workflow.py` | Application |
| `state/agent_state.py` | `src/application/state/recruitment_state.py` | Application |
| `state/sourcing_manager_state.py` | `src/application/state/sourcing_state.py` | Application |
| `tools/database_agent_tools.py` | `src/infrastructure/persistence/mongodb/mongodb_candidate_repository.py` | Infrastructure |
| `tools/get_projects.py` | `src/infrastructure/persistence/mongodb/mongodb_project_repository.py` | Infrastructure |
| `tools/outreach_tools.py` | Split into `src/infrastructure/external_services/email/` and `linkedin/` | Infrastructure |
| `tools/scourcing_tools.py` | `src/infrastructure/search/search_service_impl.py` | Infrastructure |
| `tools/search_tools.py` | `src/infrastructure/search/linkedin_search.py` | Infrastructure |
| `config/config.py` | `src/infrastructure/config/settings.py` | Infrastructure |
| `prompts/*.py` | `src/infrastructure/ai/prompts/*.py` | Infrastructure |
| `test/test_complete_mock.py` | `tests/e2e/test_complete_flow.py` | Tests |

---

## Key Design Patterns

### 1. Repository Pattern
**Purpose**: Abstract data access from business logic

```python
# Domain: Abstract interface
class CandidateRepository(ABC):
    @abstractmethod
    async def save(self, candidate: Candidate) -> CandidateId:
        pass
    
    @abstractmethod
    async def find_by_id(self, candidate_id: CandidateId) -> Optional[Candidate]:
        pass

# Infrastructure: Concrete implementation
class MongoDBCandidateRepository(CandidateRepository):
    async def save(self, candidate: Candidate) -> CandidateId:
        # MongoDB specific implementation
        pass
```

### 2. Use Case Pattern
**Purpose**: Encapsulate application-specific business rules

```python
class SearchCandidatesUseCase:
    def __init__(
        self,
        candidate_repo: CandidateRepository,
        search_service: SearchService,
        ai_service: AIService
    ):
        self.candidate_repo = candidate_repo
        self.search_service = search_service
        self.ai_service = ai_service
    
    async def execute(self, request: SearchCandidatesRequest) -> SearchCandidatesResponse:
        # Pure business logic, no infrastructure concerns
        pass
```

### 3. Dependency Injection
**Purpose**: Manage dependencies and enable testing

```python
# Infrastructure: DI Container
class DIContainer:
    @staticmethod
    def get_candidate_repository() -> CandidateRepository:
        if settings.USE_MONGODB:
            return MongoDBCandidateRepository()
        else:
            return MemoryCandidateRepository()  # For testing
```

### 4. Workflow Orchestration
**Purpose**: Coordinate multiple use cases

```python
class SourcingManagerWorkflow:
    def __init__(
        self,
        search_use_case: SearchCandidatesUseCase,
        evaluate_use_case: EvaluateCandidatesUseCase,
        enrich_use_case: EnrichCandidateProfilesUseCase
    ):
        self.search = search_use_case
        self.evaluate = evaluate_use_case
        self.enrich = enrich_use_case
    
    async def execute(self, request: SourcingRequest) -> SourcingResult:
        # Orchestrate multiple use cases
        candidates = await self.search.execute(request)
        evaluated = await self.evaluate.execute(candidates)
        enriched = await self.enrich.execute(evaluated)
        return enriched
```

---

## Benefits of Clean Architecture

### 1. **Testability**
- Pure business logic in Domain layer is easy to unit test
- Use case tests don't require database or external services
- Infrastructure can be easily mocked

### 2. **Maintainability**
- Clear separation of concerns
- Changes to infrastructure don't affect business logic
- Easier to understand and navigate codebase

### 3. **Flexibility**
- Easy to swap implementations (MongoDB → PostgreSQL)
- Easy to add new interfaces (Web UI, GraphQL API)
- Easy to add new features without breaking existing code

### 4. **Scalability**
- Each layer can be scaled independently
- Microservices architecture becomes straightforward
- Easy to parallelize development across teams

### 5. **Business Logic Protection**
- Core business rules are isolated and protected
- Framework changes don't cascade through codebase
- Upgrade path is clearer

---

## Testing Strategy During Migration

### Continuous Testing Guarantee
After each phase, ALL 14 existing tests must pass:

```bash
# Run after each phase
python -m pytest tests/e2e/test_complete_flow.py -v

# Expected output:
# 14 passed in X.XXs
```

### Test Types

1. **Unit Tests** (Fast, isolated)
   - Domain entities
   - Domain services
   - Value objects
   - Use cases (with mocked dependencies)

2. **Integration Tests** (Medium speed)
   - Repository implementations
   - Workflow orchestration
   - External service integrations

3. **End-to-End Tests** (Slower, comprehensive)
   - Complete recruitment workflow
   - All 14 current tests
   - New comprehensive scenarios

---

## Backward Compatibility

### Root `main.py` Compatibility Layer

```python
#!/usr/bin/env python3
"""
Backward Compatibility Entry Point
Delegates to new Clean Architecture structure
"""
import sys
from src.presentation.cli.main import main

if __name__ == '__main__':
    sys.exit(main())
```

This ensures existing scripts and documentation continue to work.

---

## Rollout Timeline

| Week | Phase | Deliverable | Risk Level |
|------|-------|-------------|------------|
| 1 | Domain Layer | Pure business entities & logic | Low |
| 2 | Infrastructure Layer | External service adapters | Medium |
| 3 | Application Layer | Use cases & workflows | Medium |
| 4 | Presentation Layer | CLI & API separation | Low |
| 5 | Testing Refactoring | Enhanced test coverage | Low |
| 6 | Documentation & Cleanup | Complete migration | Low |

**Total Duration**: 6 weeks
**Checkpoint**: End of each week - all tests must pass
**Rollback**: Git branch per phase for easy rollback

---

## Success Criteria

✅ **All 14 existing tests pass**
✅ **No functionality lost**
✅ **Improved test coverage (target: 80%)**
✅ **Clear separation of concerns**
✅ **Dependency injection working**
✅ **Documentation complete**
✅ **Backward compatibility maintained**

---

## Next Steps

1. **Review this plan** - Confirm approach and timeline
2. **Create feature branch** - `git checkout -b refactor/clean-architecture`
3. **Start Phase 1** - Begin with Domain Layer migration
4. **Daily commits** - Small, testable increments
5. **Weekly reviews** - Validate progress and adjust plan

---

## Questions to Answer Before Starting

1. Do you want to proceed with all 6 phases, or start with a subset?
2. Should we keep the old structure in parallel during migration?
3. Any specific areas you want to prioritize?
4. Do you want to add any new features during refactoring?
5. Should we set up CI/CD pipeline to automate testing during migration?

---

**Ready to begin?** Let me know and I'll start with Phase 1: Domain Layer creation.
