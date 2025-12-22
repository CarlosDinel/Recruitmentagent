from typing import  List, Annotated, Sequence, Dict, Any , Optional  
from langgraph.graph import START, END, StateGraph
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """A dictionary representing the state of an agent."""
    name: str
    description: str
    tools: List[str]
    tool_descriptions: List[str]
    tool_input_types: List[str]
    tool_output_types: List[str]
    input_type: str
    output_type: str
    intermediate_steps: List[Dict[str, Any]]
    max_iterations: int
    iteration_count: int
    stop: bool
    last_action: str
    last_observation: str
    last_input: str
    last_output: str
    graph: StateGraph
    memory: List[str]
    memory_limit: int
    verbose: bool
    temperature: float
    top_k: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    best_of: int
    n: int
    logit_bias: Dict[str, float]
    seed: int
    model: str
    api_key: str
    api_base: str
    api_version: str
    organization: str
    proxy: str
    request_timeout: int
    retries: int
    backoff_factor: float
    status: str
    error_message: str
    created_at: str
    updated_at: str

    #  recruitment specific
    candidate_id: Optional[str]
    candidate_profile: Optional[Dict[str, Any]]
    candidate_status: Optional[str] 
    motivation: Optional[str]
    reasoning: Optional[str]
    human_review_required: Optional[bool]
    human_review: Optional[str]
    outreach_history: Optional[List[Dict[str, Any]]]
    outreach_method: Optional[str]
    outreach_status: Optional[str]  
    outreach_response: Optional[str]
    last_step_at: Optional[str]
    