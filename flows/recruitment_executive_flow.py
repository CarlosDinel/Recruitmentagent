"""
Recruitment Executive Workflow
Main orchestration flow for the recruitment process using LangGraph.
"""

from typing import Dict, Any, List, Sequence, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import os
from datetime import datetime
import logging

# Import agent state
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.recruitment_executive import RecruitmentExecutiveState
from tools.get_projects import get_all_projects, convert_project_to_json
from prompts.recruitment_executive_agent_prompts import RecruitmentPrompts

logger = logging.getLogger('RecruitmentFlow')

class RecruitmentExecutiveFlow:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        workflow = StateGraph(RecruitmentExecutiveState)

        # Voeg nodes toe met methoden van deze class (of importeer ze ergens)
        workflow.add_node("analyze_request", self.analyze_request_node)
        workflow.add_node("get_projects", self.get_projects_node)
        workflow.add_node("plan_strategy", self.plan_strategy_node)
        workflow.add_node("delegate_sourcing", self.delegate_sourcing_node)
        workflow.add_node("delegate_outreach", self.delegate_outreach_node)
        workflow.add_node("monitor_progress", self.monitor_progress_node)
        workflow.add_node("generate_report", self.generate_report_node)

        # Start van de flow
        workflow.add_edge(START, "analyze_request")
        workflow.add_edge("analyze_request", "get_projects")
        workflow.add_edge("get_projects", "plan_strategy")

        # Conditional routing afhankelijk van strategie of state
        workflow.add_conditional_edges(
            "plan_strategy",
            self.route_next_step,
            {
                "sourcing": "delegate_sourcing",
                "outreach": "delegate_outreach",
                "monitor": "monitor_progress",
                "complete": "generate_report"
            }
        )

        # Van sourcing en outreach altijd door naar monitor
        workflow.add_edge("delegate_sourcing", "monitor_progress")
        workflow.add_edge("delegate_outreach", "monitor_progress")

        # Loop & conditional edges monitor progress:
        workflow.add_conditional_edges(
            "monitor_progress",
            self.should_continue_monitoring,
            {
                "retry_sourcing": "delegate_sourcing",  # Herhaal sourcing poging
                "adjust_strategy": "plan_strategy",    # Pas strategie aan en probeer opnieuw
                "complete": "generate_report"           # Klaar, rapporteren
            }
        )

        workflow.add_edge("generate_report", END)

        return workflow.compile()

    # Voorbeeld methodes die beslissingen maken o.b.v. state
    def route_next_step(self, state):
        # Bepaal volgende stap op basis van strategie of state
        strategy = state.get("recruitment_strategy", "standard")
        if strategy == "bulk":
            return "sourcing"
        if state.get("candidate_pipeline", {}).get("sourced"):
            return "outreach"
        if state.get("next_action") == "monitor":
            return "monitor"
        return "complete"

    def should_continue_monitoring(self, state):
        # Conditie om te bepalen of opnieuw gepoogd wordt
        sourced = state.get("candidate_pipeline", {}).get("sourced", [])
        attempts = state.get("sourcing_attempts", 0)
        min_candidates = state.get("target_candidates", 1)

        if not sourced and attempts < 3:
            return "retry_sourcing"  # Loop weer terug naar sourcing
        if len(sourced) < min_candidates:
            return "adjust_strategy"  # Pas strategie aan en probeer opnieuw
        return "complete"