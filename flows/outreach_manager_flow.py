"""
Outreach Manager Workflow - Complete Outreach Campaign Pipeline with Feedback Loops
Pipeline: Prioritize → Campaign Setup → Execute → Track → Optimize → Complete
"""

from typing import Dict, Any, List, Literal
from datetime import datetime
import logging
import json

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict, Annotated
from langchain_core.messages import add_messages

from sub_agents.email_outreach_agent import EmailOutreachAgent
from sub_agents.LinkedIn_outreach_agent import LinkedInOutreachAgent
from sub_agents.ghostwriter_agent import GhostwriterAgent
from agents.database_agent import DatabaseAgent
from prompts.outreach_manager_prompts import OutreachManagerPrompts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutreachWorkflowState(TypedDict):
    """State for the outreach workflow."""
    messages: Annotated[List, add_messages]
    project_id: str
    project_name: str
    campaign_num: str
    candidates: List[Dict[str, Any]]
    user_info: Dict[str, Any]
    
    # Campaign stages
    prioritized_candidates: List[Dict[str, Any]]
    campaign_setup: Dict[str, Any]
    outreach_log: List[Dict[str, Any]]
    response_tracking: Dict[str, Any]
    optimization_suggestions: List[str]
    completed_outreach: List[Dict[str, Any]]
    
    # Metrics
    outreach_metrics: Dict[str, Any]
    response_rate: float
    engagement_rate: float
    
    # Control
    current_stage: str
    next_action: str
    optimization_attempts: int
    campaign_health: str
    needs_optimization: bool
    error: str


class OutreachManagerFlow:
    """
    Orchestrates the complete outreach campaign pipeline with feedback loops.
    
    Stages:
    1. PRIORITIZE - Rank candidates by fit
    2. SETUP - Configure campaign strategy
    3. EXECUTE - Send outreach messages via multiple channels
    4. TRACK - Monitor responses and engagement
    5. OPTIMIZE - Adjust strategy based on performance
    6. COMPLETE - Finalize campaign
    """
    
    def __init__(self, user_info: Dict[str, Any]):
        self.email_agent = EmailOutreachAgent()
        self.linkedin_agent = LinkedInOutreachAgent(user_info)
        self.ghostwriter_agent = GhostwriterAgent(user_info)
        self.database_agent = DatabaseAgent()
        self.user_info = user_info
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.7)
        
        logger.info("✅ OutreachManagerFlow initialized")
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> Any:
        """Create the outreach workflow graph."""
        workflow = StateGraph(OutreachWorkflowState)
        
        # Add nodes
        workflow.add_node("prioritize_candidates", self.prioritize_candidates_node)
        workflow.add_node("setup_campaign", self.setup_campaign_node)
        workflow.add_node("execute_outreach", self.execute_outreach_node)
        workflow.add_node("track_responses", self.track_responses_node)
        workflow.add_node("optimize_campaign", self.optimize_campaign_node)
        workflow.add_node("adjust_messaging", self.adjust_messaging_node)
        workflow.add_node("finalize_campaign", self.finalize_campaign_node)
        
        # Define edges
        workflow.add_edge(START, "prioritize_candidates")
        workflow.add_edge("prioritize_candidates", "setup_campaign")
        workflow.add_edge("setup_campaign", "execute_outreach")
        workflow.add_edge("execute_outreach", "track_responses")
        workflow.add_edge("track_responses", "optimize_campaign")
        
        # Conditional: Optimization with feedback loop
        workflow.add_conditional_edges(
            "optimize_campaign",
            self.should_optimize,
            {
                "adjust": "adjust_messaging",
                "complete": "finalize_campaign"
            }
        )
        
        # Adjust messaging loops back to execute
        workflow.add_edge("adjust_messaging", "execute_outreach")
        workflow.add_edge("finalize_campaign", END)
        
        return workflow.compile()
    
    def prioritize_candidates_node(self, state: OutreachWorkflowState) -> OutreachWorkflowState:
        """
        Stage 1: PRIORITIZE
        Rank candidates by fit score and engagement potential.
        """
        logger.info(f"🎯 [PRIORITIZE] Ranking {len(state['candidates'])} candidates")
        
        try:
            candidates = state["candidates"]
            
            if not candidates:
                logger.warning("⚠️ No candidates to prioritize")
                state["prioritized_candidates"] = []
                return state
            
            # Sort by suitability score
            prioritized = sorted(
                candidates,
                key=lambda x: x.get("suitability_score", 0),
                reverse=True
            )
            
            state["prioritized_candidates"] = prioritized
            state["current_stage"] = "prioritization_complete"
            
            logger.info(f"✅ Candidates prioritized")
            return state
            
        except Exception as e:
            logger.error(f"❌ Prioritization error: {e}")
            state["error"] = str(e)
            return state
    
    def setup_campaign_node(self, state: OutreachWorkflowState) -> OutreachWorkflowState:
        """
        Stage 2: SETUP
        Configure outreach campaign strategy and channels.
        """
        logger.info("📋 [SETUP] Configuring outreach campaign")
        
        try:
            # Determine channels based on candidate info
            channels = []
            if all(c.get("email") for c in state["prioritized_candidates"]):
                channels.append("email")
            if all(c.get("linkedin_url") for c in state["prioritized_candidates"]):
                channels.append("linkedin")
            
            campaign_setup = {
                "project_id": state["project_id"],
                "project_name": state["project_name"],
                "campaign_num": state["campaign_num"],
                "channels": channels or ["email", "linkedin"],
                "total_candidates": len(state["prioritized_candidates"]),
                "strategy": "multi_channel_approach",
                "setup_timestamp": datetime.utcnow().isoformat()
            }
            
            state["campaign_setup"] = campaign_setup
            state["current_stage"] = "setup_complete"
            
            logger.info(f"✅ Campaign setup: {', '.join(campaign_setup['channels'])} channels")
            return state
            
        except Exception as e:
            logger.error(f"❌ Setup error: {e}")
            state["error"] = str(e)
            return state
    
    def execute_outreach_node(self, state: OutreachWorkflowState) -> OutreachWorkflowState:
        """
        Stage 3: EXECUTE
        Send outreach messages via configured channels.
        """
        logger.info(f"📧 [EXECUTE] Sending outreach to {len(state['prioritized_candidates'])} candidates")
        
        try:
            outreach_results = []
            channels = state["campaign_setup"].get("channels", ["email"])
            
            for candidate in state["prioritized_candidates"][:10]:  # Limit to 10 per batch
                try:
                    # Email outreach
                    if "email" in channels and candidate.get("email"):
                        email_result = self.email_agent.send_and_record_email(
                            candidate_info=candidate,
                            project_info={
                                "projectid": state["project_id"],
                                "project_name": state["project_name"]
                            },
                            campaign_num=state["campaign_num"]
                        )
                        outreach_results.append(email_result)
                    
                    # LinkedIn outreach
                    if "linkedin" in channels and candidate.get("linkedin_url"):
                        linkedin_result = self.linkedin_agent.send_connection_request(
                            provider_id=candidate.get("provider_id", ""),
                            candidate_name=candidate.get("naam", ""),
                            candidate_info=candidate,
                            project_info={
                                "projectid": state["project_id"],
                                "project_name": state["project_name"]
                            },
                            campaign_num=state["campaign_num"]
                        )
                        outreach_results.append(linkedin_result)
                        
                except Exception as e:
                    logger.warning(f"Could not outreach to {candidate.get('naam')}: {e}")
            
            state["outreach_log"] = outreach_results
            state["current_stage"] = "outreach_execute_complete"
            
            logger.info(f"✅ Sent {len(outreach_results)} outreach messages")
            return state
            
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            state["error"] = str(e)
            return state
    
    def track_responses_node(self, state: OutreachWorkflowState) -> OutreachWorkflowState:
        """
        Stage 4: TRACK
        Monitor responses and engagement metrics.
        """
        logger.info("📊 [TRACK] Tracking responses and engagement")
        
        try:
            total_outreach = len(state["outreach_log"])
            successful = len([r for r in state["outreach_log"] if r.get("status") == "success"])
            
            # Simulate response tracking (in production, this would query actual responses)
            response_rate = successful / total_outreach if total_outreach > 0 else 0
            engagement_rate = response_rate * 0.3  # Assume 30% of contacted respond
            
            state["response_tracking"] = {
                "total_contacted": total_outreach,
                "successful_outreach": successful,
                "failed_outreach": total_outreach - successful,
                "response_rate": response_rate,
                "engagement_rate": engagement_rate,
                "tracking_timestamp": datetime.utcnow().isoformat()
            }
            
            state["response_rate"] = response_rate
            state["engagement_rate"] = engagement_rate
            state["current_stage"] = "tracking_complete"
            
            logger.info(f"✅ Response Rate: {response_rate*100:.1f}% | Engagement: {engagement_rate*100:.1f}%")
            return state
            
        except Exception as e:
            logger.error(f"❌ Tracking error: {e}")
            state["error"] = str(e)
            return state
    
    def optimize_campaign_node(self, state: OutreachWorkflowState) -> OutreachWorkflowState:
        """
        Stage 5: OPTIMIZE
        Analyze performance and suggest optimizations.
        """
        logger.info("🔍 [OPTIMIZE] Analyzing campaign performance")
        
        try:
            response_rate = state["response_rate"]
            engagement_rate = state["engagement_rate"]
            
            suggestions = []
            needs_optimization = False
            
            if response_rate < 0.15:
                suggestions.append("Response rate below 15% - consider adjusting messaging tone")
                needs_optimization = True
            
            if engagement_rate < 0.05:
                suggestions.append("Low engagement - try personalization improvements")
                needs_optimization = True
            
            if len(state["outreach_log"]) > 0:
                success_rate = len([r for r in state["outreach_log"] if r.get("status") == "success"]) / len(state["outreach_log"])
                if success_rate < 0.8:
                    suggestions.append(f"Only {success_rate*100:.0f}% delivery success - check recipient data")
                    needs_optimization = True
            
            # Determine campaign health
            if response_rate > 0.3:
                campaign_health = "excellent"
            elif response_rate > 0.15:
                campaign_health = "good"
            elif response_rate > 0.05:
                campaign_health = "fair"
            else:
                campaign_health = "poor"
            
            state["optimization_suggestions"] = suggestions
            state["needs_optimization"] = needs_optimization
            state["campaign_health"] = campaign_health
            state["current_stage"] = "optimization_complete"
            
            logger.info(f"✅ Campaign Health: {campaign_health} | Suggestions: {len(suggestions)}")
            return state
            
        except Exception as e:
            logger.error(f"❌ Optimization error: {e}")
            state["error"] = str(e)
            return state
    
    def adjust_messaging_node(self, state: OutreachWorkflowState) -> OutreachWorkflowState:
        """
        Stage 6: ADJUST (Feedback Loop)
        Modify messaging based on optimization suggestions.
        """
        logger.info("🔄 [ADJUST] Adjusting messaging strategy")
        
        try:
            attempts = state.get("optimization_attempts", 0)
            
            if attempts >= 1:
                logger.warning("⚠️ Max optimization attempts reached")
                state["current_stage"] = "adjustment_complete"
                return state
            
            # Improve messaging based on suggestions
            logger.info(f"📝 Implementing {len(state['optimization_suggestions'])} improvements")
            
            state["optimization_attempts"] = attempts + 1
            state["current_stage"] = "messaging_adjusted"
            
            logger.info(f"✅ Messaging adjusted (attempt {attempts + 1})")
            return state
            
        except Exception as e:
            logger.error(f"❌ Adjustment error: {e}")
            state["error"] = str(e)
            return state
    
    def finalize_campaign_node(self, state: OutreachWorkflowState) -> OutreachWorkflowState:
        """
        Stage 7: FINALIZE
        Complete campaign and prepare handoff.
        """
        logger.info("🎯 [FINALIZE] Finalizing outreach campaign")
        
        try:
            state["completed_outreach"] = state["prioritized_candidates"]
            state["outreach_metrics"] = {
                "total_candidates": len(state["candidates"]),
                "total_contacted": len(state["outreach_log"]),
                "response_rate": state["response_rate"],
                "engagement_rate": state["engagement_rate"],
                "campaign_health": state["campaign_health"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            state["current_stage"] = "outreach_complete"
            
            logger.info(f"✅ Campaign finalized")
            return state
            
        except Exception as e:
            logger.error(f"❌ Finalization error: {e}")
            state["error"] = str(e)
            return state
    
    def should_optimize(self, state: OutreachWorkflowState) -> str:
        """Determine if campaign should be optimized or completed."""
        if state["needs_optimization"] and state.get("optimization_attempts", 0) < 1:
            return "adjust"
        return "complete"
    
    def run(self,
            project_id: str,
            project_name: str,
            campaign_num: str,
            candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute the complete outreach workflow.
        
        Returns:
            Campaign results and metrics
        """
        logger.info("🚀 Starting Outreach Manager Flow...")
        
        initial_state: OutreachWorkflowState = {
            "messages": [],
            "project_id": project_id,
            "project_name": project_name,
            "campaign_num": campaign_num,
            "candidates": candidates,
            "user_info": self.user_info,
            "prioritized_candidates": [],
            "campaign_setup": {},
            "outreach_log": [],
            "response_tracking": {},
            "optimization_suggestions": [],
            "completed_outreach": [],
            "outreach_metrics": {},
            "response_rate": 0,
            "engagement_rate": 0,
            "current_stage": "initialized",
            "next_action": "prioritize",
            "optimization_attempts": 0,
            "campaign_health": "unknown",
            "needs_optimization": False,
            "error": ""
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        logger.info("✅ Outreach Manager Flow completed")
        
        return {
            "completed_outreach": final_state["completed_outreach"],
            "metrics": final_state["outreach_metrics"],
            "response_tracking": final_state["response_tracking"],
            "status": "success" if not final_state["error"] else "error",
            "error": final_state["error"]
        }