"""
Flows package for the Recruitment Agent System.
Contains all workflow definitions and orchestration logic.
"""

from .recruitment_executive_flow import RecruitmentExecutiveFlow, create_recruitment_flow

__all__ = [
    'RecruitmentExecutiveFlow',
    'create_recruitment_flow'
]

# Available flow types
FLOW_TYPES = {
    'recruitment_executive': RecruitmentExecutiveFlow,
    'standard': RecruitmentExecutiveFlow,  # Alias
    'default': RecruitmentExecutiveFlow    # Alias
}

def get_flow(flow_type: str = 'recruitment_executive', config: dict = None):
    """
    Factory function to get a flow instance by type.
    
    Args:
        flow_type (str): Type of flow to create
        config (dict): Configuration for the flow
        
    Returns:
        Flow instance
    """
    if flow_type not in FLOW_TYPES:
        raise ValueError(f"Unknown flow type: {flow_type}. Available: {list(FLOW_TYPES.keys())}")
    
    flow_class = FLOW_TYPES[flow_type]
    return flow_class(config or {})