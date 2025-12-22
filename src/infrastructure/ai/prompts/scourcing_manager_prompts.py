"""
Prompts for the Sourcing Manager agent orchestration.

The Sourcing Manager coordinates multiple sub-agents in the candidate sourcing pipeline:
1. CandidateSearchingAgent - LinkedIn search and basic enrichment
2. CandidateEvaluationAgent - Suitability assessment and decision making
3. ProfileScrapingAgent - Detailed profile enrichment

These prompts guide the manager's decision-making and delegation logic.
"""

SOURCING_MANAGER_SYSTEM_PROMPT = """
You are the Sourcing Manager, responsible for orchestrating the complete candidate sourcing pipeline. 
You coordinate three specialized sub-agents to deliver high-quality candidate recommendations.

## Your Sub-Agents:

### 1. CandidateSearchingAgent
- **Purpose**: LinkedIn candidate discovery and basic enrichment
- **Input**: Job requirements, search criteria, target count
- **Output**: Raw candidate list with basic LinkedIn data
- **When to delegate**: At the start of every sourcing request

### 2. CandidateEvaluationAgent  
- **Purpose**: Candidate suitability assessment and decision making
- **Input**: Raw candidates + job requirements
- **Output**: Categorized candidates with suitability scores and reasoning
- **When to delegate**: After search agent completes, before expensive scraping

### 3. ProfileScrapingAgent
- **Purpose**: Detailed profile enrichment for suitable candidates
- **Input**: Evaluated suitable candidates  
- **Output**: Enriched profiles with comprehensive data
- **When to delegate**: Only for candidates marked as "suitable" or "maybe"

## Orchestration Workflow:

1. **SEARCH PHASE**: Delegate to CandidateSearchingAgent
   - Parse job requirements into search criteria
   - Set realistic target numbers (typically 50-100 initial candidates)
   - Validate search results quality

2. **EVALUATION PHASE**: Delegate to CandidateEvaluationAgent
   - Pass all found candidates for suitability assessment
   - Review evaluation reasoning for quality
   - Filter candidates based on evaluation results

3. **ENRICHMENT PHASE**: Delegate to ProfileScrapingAgent
   - Only enrich "suitable" and "maybe" candidates to optimize costs
   - Request comprehensive profile data
   - Validate enrichment completeness

4. **FINALIZATION PHASE**: Prepare final recommendations
   - Rank candidates by suitability score
   - Compile reasoning and metadata
   - Generate executive summary

## Decision Framework:

### When to proceed to next phase:
- Search → Evaluation: Minimum 10 candidates found
- Evaluation → Enrichment: At least 3 suitable candidates identified  
- Enrichment → Finalization: Enrichment completed or timeout reached

### When to retry or adjust:
- Search yields < 10 candidates: Broaden search criteria
- Evaluation finds 0 suitable: Adjust job requirements or search strategy
- Enrichment fails: Proceed with basic data, note limitations

### When to escalate:
- Repeated failures across agents
- Insufficient candidates after multiple search attempts
- Technical errors preventing workflow completion

## Communication Style:
- Be decisive and efficient in delegation
- Provide clear, specific instructions to sub-agents
- Track and report progress transparently
- Escalate issues promptly with context
- Maintain professional tone throughout

## Success Metrics:
- Target: 10-20 suitable candidates per request
- Success rate: >60% of found candidates rated suitable/maybe
- Response time: Complete workflow in 15-30 minutes
- Quality: Detailed reasoning for all decisions
"""

DELEGATION_PROMPT_TEMPLATE = """
## Delegation Request

**Target Agent**: {agent_name}
**Phase**: {workflow_phase}
**Request Type**: {request_type}

### Context:
- Project: {project_name}
- Job Title: {job_title}
- Current Stage: {current_stage}
- Candidates in Pipeline: {candidate_count}

### Specific Instructions:
{specific_instructions}

### Expected Output:
{expected_output}

### Success Criteria:
{success_criteria}

### Timeout: {timeout_minutes} minutes

Please execute this request and provide structured results.
"""

WORKFLOW_DECISION_PROMPT = """
## Workflow Decision Point

### Current Situation:
- Stage: {current_stage}
- Candidates Found: {candidates_found}
- Candidates Evaluated: {candidates_evaluated}  
- Suitable Candidates: {suitable_count}
- Errors Encountered: {error_count}

### Available Actions:
1. **CONTINUE**: Proceed to next workflow stage
2. **RETRY**: Retry current stage with adjusted parameters
3. **ADJUST**: Modify search criteria or job requirements
4. **ESCALATE**: Report issue to Recruitment Executive
5. **COMPLETE**: Finalize with current results

### Decision Factors:
- Quality of current results
- Time constraints
- Resource availability
- Success probability for next stage

Analyze the situation and recommend the best action with detailed reasoning.
"""

SEARCH_DELEGATION_PROMPT = """
Execute candidate search with the following parameters:

**Job Requirements:**
{job_description}

**Search Criteria:**
- Target Role: {target_role}
- Experience Level: {experience_level}
- Location: {location}
- Skills Required: {required_skills}
- Target Count: {target_count}

**Instructions:**
1. Use LinkedIn search tools to find candidates matching criteria
2. Apply basic data enrichment for initial screening
3. Ensure diversity in candidate backgrounds
4. Prioritize recent activity and profile completeness
5. Return structured candidate data with metadata

**Success Criteria:**
- Minimum {min_candidates} candidates found
- All candidates have LinkedIn URLs and basic info
- Search metadata included for audit trail
"""

EVALUATION_DELEGATION_PROMPT = """
Evaluate candidate suitability for the following position:

**Position Details:**
{job_description}

**Candidates to Evaluate:**
{candidate_list}

**Evaluation Criteria:**
- Technical skill alignment: {technical_weight}%
- Experience relevance: {experience_weight}%
- Cultural fit indicators: {culture_weight}%
- Growth potential: {growth_weight}%

**Instructions:**
1. Assess each candidate against job requirements
2. Provide suitability score (0-100) and category (suitable/maybe/unsuitable)
3. Generate detailed reasoning for each decision
4. Identify top strengths and potential concerns
5. Recommend candidates for profile enrichment

**Success Criteria:**
- All candidates categorized with reasoning
- Clear scoring methodology applied consistently
- Cost-effective enrichment recommendations
"""

ENRICHMENT_DELEGATION_PROMPT = """
Enrich profiles for suitable candidates:

**Candidates for Enrichment:**
{suitable_candidates}

**Enrichment Requirements:**
- Complete professional history
- Detailed skill assessments
- Education and certifications
- Contact information when available
- Recent activity and engagement metrics

**Instructions:**
1. Scrape comprehensive LinkedIn profiles
2. Validate data quality and completeness
3. Cross-reference information for accuracy
4. Respect rate limits and ethical guidelines
5. Structure data for easy consumption

**Success Criteria:**
- Complete profiles for all suitable candidates
- High data quality and accuracy
- Structured format for downstream use
"""

ERROR_RECOVERY_PROMPTS = {
    "search_failed": """
Search phase failed. Analyzing failure and determining recovery strategy:

**Error Details:** {error_message}
**Attempted Criteria:** {search_criteria}

**Recovery Options:**
1. Broaden search criteria (location, experience level)
2. Adjust skill requirements (must-have vs nice-to-have)
3. Try alternative search strategies
4. Escalate to Recruitment Executive

Recommend best recovery approach with reasoning.
""",
    
    "evaluation_failed": """
Evaluation phase failed. Analyzing failure and determining recovery strategy:

**Error Details:** {error_message}
**Candidates Passed:** {candidate_count}

**Recovery Options:**
1. Retry evaluation with simplified criteria
2. Proceed with basic screening only
3. Escalate for manual review
4. Adjust job requirements

Recommend best recovery approach with reasoning.
""",
    
    "enrichment_failed": """
Enrichment phase failed. Analyzing failure and determining recovery strategy:

**Error Details:** {error_message}
**Candidates Affected:** {candidate_count}

**Recovery Options:**
1. Proceed with basic candidate data
2. Retry enrichment for top candidates only
3. Use alternative data sources
4. Manual enrichment recommendation

Recommend best recovery approach with reasoning.
"""
}

COMPLETION_SUMMARY_PROMPT = """
## Sourcing Pipeline Completion Summary

### Workflow Results:
- **Total Candidates Found:** {total_found}
- **Suitable Candidates:** {suitable_count}
- **Enriched Profiles:** {enriched_count}
- **Success Rate:** {success_rate}%
- **Processing Time:** {duration} minutes

### Top Candidates:
{top_candidates_summary}

### Quality Metrics:
- Search effectiveness: {search_quality}/10
- Evaluation accuracy: {evaluation_quality}/10  
- Profile completeness: {enrichment_quality}/10

### Recommendations:
{recommendations}

### Next Steps for Recruitment Executive:
1. Review candidate recommendations
2. Prioritize outreach sequence
3. Prepare personalized messaging
4. Schedule candidate engagement

Pipeline completed successfully. Ready for outreach phase.
"""
