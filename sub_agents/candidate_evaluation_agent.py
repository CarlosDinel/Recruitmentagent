"""
Candidate Evaluation Agent - Makes suitability decisions with detailed reasoning.

This agent sits between the Candidate Searching Agent and Profile Scraping Agent,
evaluating candidates against job requirements and making informed decisions about
which candidates should proceed to the expensive profile scraping phase.
"""

#  ---- Package imports ----
from typing import List, Dict, Any, Optional
import logging 
import json
from datetime import datetime
import uuid

#  ---- Local imports ----
from tools.scourcing_tools import match_candidates_to_job

# Set up logging
logger = logging.getLogger(__name__)

class CandidateEvaluationAgent:
    """
    Candidate Evaluation Agent - Makes intelligent suitability decisions.
    
    Role: Candidate suitability evaluation and decision making
    Responsibilities:
    - Receive candidate lists from Candidate Searching Agent
    - Evaluate candidates against job requirements
    - Generate detailed reasoning for all decisions
    - Recommend candidates for Profile Scraping Agent
    - Store evaluation metadata for audit trails
    """
    
    def __init__(self):
        self.name = "Candidate Evaluation Agent"
        self.role = "Candidate suitability evaluation and decision making"
        
        # Evaluation criteria weights (configurable)
        self.default_weights = {
            "skills_match": 0.40,
            "experience_match": 0.30,
            "location_match": 0.20,
            "cultural_fit": 0.10
        }
        
        # Quality thresholds
        self.suitability_thresholds = {
            "high_priority": 80,      # Definitely suitable
            "medium_priority": 70,    # Suitable with minor concerns
            "low_priority": 50,       # Potentially suitable, needs review
            "not_suitable": 0         # Below 50 = not suitable
        }
    
    def evaluate_candidates(
        self,
        sourcing_manager_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point for candidate evaluation from Sourcing Manager.
        
        Args:
            sourcing_manager_request: Contains:
                - candidates: List from Candidate Searching Agent
                - job_requirements: Detailed job description
                - evaluation_criteria: Optional custom criteria
                - project_metadata: projectid, naam_project, campaign_num
                
        Returns:
            Evaluation results with categorized candidates and reasoning
        """
        logger.info(f"🎯 {self.name} evaluating candidates for project {sourcing_manager_request.get('projectid', 'unknown')}")
        
        try:
            # Extract input data
            candidates = sourcing_manager_request.get("candidates", [])
            job_requirements = sourcing_manager_request.get("job_requirements", "")
            project_metadata = self._extract_project_metadata(sourcing_manager_request)
            evaluation_criteria = sourcing_manager_request.get("evaluation_criteria", {})
            
            # Validate inputs
            if not candidates:
                raise ValueError("No candidates provided for evaluation")
            if not job_requirements:
                raise ValueError("Job requirements are required for evaluation")
            
            logger.info(f"📋 Evaluating {len(candidates)} candidates against job requirements")
            
            # Perform detailed evaluation
            evaluation_results = self._perform_candidate_evaluation(
                candidates=candidates,
                job_requirements=job_requirements,
                evaluation_criteria=evaluation_criteria,
                project_metadata=project_metadata
            )
            
            # Categorize results
            categorized_results = self._categorize_evaluation_results(evaluation_results)
            
            # Prepare final response
            response = self._prepare_evaluation_response(
                categorized_results=categorized_results,
                project_metadata=project_metadata,
                total_evaluated=len(candidates)
            )
            
            logger.info(f"✅ Evaluation completed: {len(response['suitable_candidates'])} suitable, {len(response['potentially_suitable'])} potential, {len(response['not_suitable_summary']['candidates'])} not suitable")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Candidate evaluation failed: {e}")
            return self._create_error_response(str(e), sourcing_manager_request)
    
    def _perform_candidate_evaluation(
        self,
        candidates: List[Dict[str, Any]],
        job_requirements: str,
        evaluation_criteria: Dict[str, Any],
        project_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Perform detailed evaluation of each candidate."""
        
        # Use the matching tool to get initial analysis
        candidates_json = json.dumps({"candidates": candidates})
        match_results_json = match_candidates_to_job.invoke({
            "candidates_json": candidates_json,
            "job_description": job_requirements
        })
        
        match_results = json.loads(match_results_json)
        
        # Enhance with detailed reasoning and decision making
        enhanced_evaluations = []
        for match_result in match_results:
            candidate = match_result["candidate"]
            match_analysis = match_result["match_analysis"]
            
            # Generate enhanced evaluation
            enhanced_evaluation = self._create_enhanced_evaluation(
                candidate=candidate,
                match_analysis=match_analysis,
                project_metadata=project_metadata,
                evaluation_criteria=evaluation_criteria
            )
            
            enhanced_evaluations.append(enhanced_evaluation)
        
        return enhanced_evaluations
    
    def _create_enhanced_evaluation(
        self,
        candidate: Dict[str, Any],
        match_analysis: Dict[str, Any],
        project_metadata: Dict[str, Any],
        evaluation_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create enhanced evaluation with detailed reasoning and decisions."""
        
        # Extract scores from match analysis
        overall_score = match_analysis.get("overall_score", 0)
        skills_score = match_analysis.get("skills_match", {}).get("score", 0)
        experience_score = match_analysis.get("experience_match", {}).get("score", 0)
        location_score = match_analysis.get("location_match", {}).get("score", 0)
        education_score = match_analysis.get("education_match", {}).get("score", 0)
        
        # Generate decision factors and risk assessment
        decision_factors = self._identify_decision_factors(match_analysis, overall_score)
        risk_factors = self._identify_risk_factors(match_analysis, overall_score)
        
        # Determine recommendation and next action
        recommendation, next_action, priority = self._make_suitability_decision(overall_score, decision_factors, risk_factors)
        
        # Generate detailed reasoning
        detailed_reasoning = self._generate_detailed_reasoning(
            match_analysis=match_analysis,
            decision_factors=decision_factors,
            risk_factors=risk_factors,
            recommendation=recommendation
        )
        
        # Create evaluation metadata
        evaluation_id = f"EVAL_{project_metadata.get('projectid', 'UNK')}_{candidate.get('provider_id', 'UNK')}_{int(datetime.now().timestamp())}"
        
        return {
            "candidate": candidate,
            "suitability_assessment": {
                "evaluation_id": evaluation_id,
                "overall_score": overall_score,
                "recommendation": recommendation,
                "next_action": next_action,
                "priority": priority,
                "score_breakdown": {
                    "skills_match": skills_score,
                    "experience_match": experience_score,
                    "location_match": location_score,
                    "education_match": education_score
                },
                "detailed_reasoning": detailed_reasoning,
                "decision_factors": decision_factors,
                "risk_factors": risk_factors,
                "evaluation_metadata": {
                    "evaluator": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "criteria_version": "v1.0",
                    "project_context": project_metadata
                }
            }
        }
    
    def _identify_decision_factors(self, match_analysis: Dict[str, Any], overall_score: float) -> List[str]:
        """Identify positive factors that support the candidate."""
        factors = []
        
        skills_score = match_analysis.get("skills_match", {}).get("score", 0)
        experience_score = match_analysis.get("experience_match", {}).get("score", 0)
        location_score = match_analysis.get("location_match", {}).get("score", 0)
        
        if skills_score >= 80:
            factors.append("excellent_technical_skills")
        elif skills_score >= 60:
            factors.append("good_technical_skills")
            
        if experience_score >= 80:
            factors.append("strong_relevant_experience")
        elif experience_score >= 60:
            factors.append("adequate_experience")
            
        if location_score >= 80:
            factors.append("perfect_location_match")
        elif location_score >= 60:
            factors.append("acceptable_location")
            
        if overall_score >= 85:
            factors.append("exceptional_overall_fit")
        elif overall_score >= 70:
            factors.append("strong_overall_fit")
            
        # Check for specific strengths
        matched_skills = match_analysis.get("skills_match", {}).get("matched_skills", [])
        if len(matched_skills) >= 4:
            factors.append("comprehensive_skill_coverage")
            
        return factors
    
    def _identify_risk_factors(self, match_analysis: Dict[str, Any], overall_score: float) -> List[str]:
        """Identify potential risks or concerns about the candidate."""
        risks = []
        
        skills_score = match_analysis.get("skills_match", {}).get("score", 0)
        experience_score = match_analysis.get("experience_match", {}).get("score", 0)
        location_score = match_analysis.get("location_match", {}).get("score", 0)
        
        if skills_score < 50:
            risks.append("significant_skill_gap")
        elif skills_score < 70:
            risks.append("moderate_skill_gap")
            
        if experience_score < 50:
            risks.append("insufficient_experience")
        elif experience_score < 70:
            risks.append("experience_concerns")
            
        if location_score < 50:
            risks.append("location_mismatch")
        elif location_score < 70:
            risks.append("location_considerations")
            
        # Check for missing critical skills
        missing_skills = match_analysis.get("skills_match", {}).get("missing_skills", [])
        if len(missing_skills) > 3:
            risks.append("multiple_missing_skills")
            
        if overall_score < 60:
            risks.append("overall_weak_match")
            
        return risks
    
    def _make_suitability_decision(
        self, 
        overall_score: float, 
        decision_factors: List[str], 
        risk_factors: List[str]
    ) -> tuple[str, str, str]:
        """Make the final suitability decision based on scores and factors."""
        
        # Base decision on score thresholds
        if overall_score >= self.suitability_thresholds["high_priority"]:
            recommendation = "HIGHLY_SUITABLE"
            next_action = "PROFILE_SCRAPING"
            priority = "HIGH"
        elif overall_score >= self.suitability_thresholds["medium_priority"]:
            recommendation = "SUITABLE"
            next_action = "PROFILE_SCRAPING"
            priority = "MEDIUM"
        elif overall_score >= self.suitability_thresholds["low_priority"]:
            recommendation = "POTENTIALLY_SUITABLE"
            next_action = "MANUAL_REVIEW"
            priority = "LOW"
        else:
            recommendation = "NOT_SUITABLE"
            next_action = "ARCHIVE"
            priority = "NONE"
        
        # Adjust based on critical factors
        if "excellent_technical_skills" in decision_factors and "strong_relevant_experience" in decision_factors:
            if recommendation == "SUITABLE":
                recommendation = "HIGHLY_SUITABLE"
                priority = "HIGH"
        
        if "significant_skill_gap" in risk_factors or "insufficient_experience" in risk_factors:
            if recommendation in ["HIGHLY_SUITABLE", "SUITABLE"]:
                recommendation = "POTENTIALLY_SUITABLE"
                next_action = "MANUAL_REVIEW"
                priority = "LOW"
        
        return recommendation, next_action, priority
    
    def _generate_detailed_reasoning(
        self,
        match_analysis: Dict[str, Any],
        decision_factors: List[str],
        risk_factors: List[str],
        recommendation: str
    ) -> Dict[str, Any]:
        """Generate comprehensive reasoning for the evaluation decision."""
        
        reasoning = {
            "skills_analysis": {
                "assessment": match_analysis.get("skills_match", {}),
                "interpretation": self._interpret_skills_match(match_analysis.get("skills_match", {}))
            },
            "experience_analysis": {
                "assessment": match_analysis.get("experience_match", {}),
                "interpretation": self._interpret_experience_match(match_analysis.get("experience_match", {}))
            },
            "location_analysis": {
                "assessment": match_analysis.get("location_match", {}),
                "interpretation": self._interpret_location_match(match_analysis.get("location_match", {}))
            },
            "overall_assessment": {
                "primary_strengths": [factor.replace("_", " ").title() for factor in decision_factors],
                "key_concerns": [risk.replace("_", " ").title() for risk in risk_factors],
                "recommendation_rationale": self._generate_recommendation_rationale(
                    recommendation, decision_factors, risk_factors
                )
            }
        }
        
        return reasoning
    
    def _interpret_skills_match(self, skills_match: Dict[str, Any]) -> str:
        """Generate human-readable interpretation of skills matching."""
        score = skills_match.get("score", 0)
        matched = skills_match.get("matched_skills", [])
        missing = skills_match.get("missing_skills", [])
        
        if score >= 90:
            return f"Exceptional skills alignment with {len(matched)} matched skills. {f'Missing: {missing}' if missing else 'Complete skill coverage.'}"
        elif score >= 70:
            return f"Strong skills match with {len(matched)} core skills covered. {f'Gaps in: {missing}' if missing else ''}"
        elif score >= 50:
            return f"Partial skills alignment. Has {len(matched)} relevant skills but missing {len(missing)} key requirements."
        else:
            return f"Significant skills gap. Only {len(matched)} skills matched, missing critical requirements: {missing}"
    
    def _interpret_experience_match(self, experience_match: Dict[str, Any]) -> str:
        """Generate human-readable interpretation of experience matching."""
        score = experience_match.get("score", 0)
        relevant_exp = experience_match.get("relevant_experience", "")
        gap = experience_match.get("experience_gap", "")
        
        if score >= 90:
            return f"Excellent experience fit: {relevant_exp}. {gap}"
        elif score >= 70:
            return f"Good experience match: {relevant_exp}. {gap}"
        elif score >= 50:
            return f"Adequate experience: {relevant_exp}. Concern: {gap}"
        else:
            return f"Experience concerns: {relevant_exp}. Issue: {gap}"
    
    def _interpret_location_match(self, location_match: Dict[str, Any]) -> str:
        """Generate human-readable interpretation of location matching."""
        score = location_match.get("score", 0)
        distance = location_match.get("distance", "")
        
        if score >= 90:
            return f"Perfect location alignment: {distance}"
        elif score >= 70:
            return f"Good location compatibility: {distance}"
        else:
            return f"Location considerations: {distance}"
    
    def _generate_recommendation_rationale(
        self, 
        recommendation: str, 
        decision_factors: List[str], 
        risk_factors: List[str]
    ) -> str:
        """Generate the overall rationale for the recommendation."""
        
        if recommendation == "HIGHLY_SUITABLE":
            return f"Exceptional candidate with {len(decision_factors)} strong factors. Recommended for immediate profile scraping and priority consideration."
        elif recommendation == "SUITABLE":
            return f"Strong candidate with {len(decision_factors)} positive factors. {f'Minor concerns: {len(risk_factors)} risk factors.' if risk_factors else 'No significant concerns.'} Recommended for profile scraping."
        elif recommendation == "POTENTIALLY_SUITABLE":
            return f"Candidate shows potential with {len(decision_factors)} positive aspects, but has {len(risk_factors)} concerns requiring manual review before proceeding."
        else:
            return f"Candidate does not meet requirements due to {len(risk_factors)} significant issues. Not recommended for further processing."
    
    def _categorize_evaluation_results(self, evaluation_results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize evaluation results by suitability level."""
        
        categorized = {
            "suitable": [],
            "potentially_suitable": [],
            "not_suitable": []
        }
        
        for result in evaluation_results:
            recommendation = result["suitability_assessment"]["recommendation"]
            
            if recommendation in ["HIGHLY_SUITABLE", "SUITABLE"]:
                categorized["suitable"].append(result)
            elif recommendation == "POTENTIALLY_SUITABLE":
                categorized["potentially_suitable"].append(result)
            else:
                categorized["not_suitable"].append(result)
        
        # Sort each category by score (descending)
        for category in categorized.values():
            category.sort(key=lambda x: x["suitability_assessment"]["overall_score"], reverse=True)
        
        return categorized
    
    def _prepare_evaluation_response(
        self,
        categorized_results: Dict[str, List[Dict[str, Any]]],
        project_metadata: Dict[str, Any],
        total_evaluated: int
    ) -> Dict[str, Any]:
        """Prepare the final evaluation response for Sourcing Manager."""
        
        suitable = categorized_results["suitable"]
        potentially_suitable = categorized_results["potentially_suitable"]
        not_suitable = categorized_results["not_suitable"]
        
        return {
            "success": True,
            "projectid": project_metadata.get("projectid"),
            "naam_project": project_metadata.get("naam_project"),
            "campaign_num": project_metadata.get("campaign_num"),
            "evaluation_summary": {
                "total_candidates_evaluated": total_evaluated,
                "suitable_candidates": len(suitable),
                "potentially_suitable": len(potentially_suitable),
                "not_suitable": len(not_suitable),
                "evaluation_timestamp": datetime.now().isoformat(),
                "evaluator": self.name
            },
            "suitable_candidates": [
                self._create_candidate_summary(result, "SUITABLE")
                for result in suitable
            ],
            "potentially_suitable": [
                self._create_candidate_summary(result, "POTENTIALLY_SUITABLE")
                for result in potentially_suitable
            ],
            "not_suitable_summary": {
                "count": len(not_suitable),
                "primary_reasons": self._analyze_rejection_reasons(not_suitable),
                "candidates": [
                    self._create_candidate_summary(result, "NOT_SUITABLE")
                    for result in not_suitable
                ],
                "stored_for_future": True
            },
            "recommended_for_scraping": [
                result["candidate"]["provider_id"]
                for result in suitable
                if result["suitability_assessment"]["next_action"] == "PROFILE_SCRAPING"
            ]
        }
    
    def _create_candidate_summary(self, evaluation_result: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Create a concise candidate summary for the response."""
        
        candidate = evaluation_result["candidate"]
        assessment = evaluation_result["suitability_assessment"]
        
        return {
            "provider_id": candidate.get("provider_id"),
            "naam": candidate.get("naam"),
            "positie": candidate.get("positie"),
            "suitability_score": assessment["overall_score"],
            "recommendation": assessment["recommendation"],
            "next_action": assessment["next_action"],
            "priority": assessment["priority"],
            "key_strengths": assessment["decision_factors"][:3],  # Top 3
            "main_concerns": assessment["risk_factors"][:2],     # Top 2
            "evaluation_id": assessment["evaluation_id"],
            "reasoning_summary": assessment["detailed_reasoning"]["overall_assessment"]["recommendation_rationale"]
        }
    
    def _analyze_rejection_reasons(self, not_suitable: List[Dict[str, Any]]) -> List[str]:
        """Analyze common reasons for candidate rejection."""
        
        all_risks = []
        for result in not_suitable:
            all_risks.extend(result["suitability_assessment"]["risk_factors"])
        
        # Count occurrences and return most common
        from collections import Counter
        risk_counts = Counter(all_risks)
        return [risk for risk, count in risk_counts.most_common(5)]
    
    def _extract_project_metadata(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract project metadata from the request."""
        return {
            "projectid": request.get("projectid"),
            "naam_project": request.get("naam_project"),
            "campaign_num": request.get("campaign_num")
        }
    
    def _create_error_response(self, error_message: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "success": False,
            "error": error_message,
            "projectid": request.get("projectid"),
            "naam_project": request.get("naam_project"),
            "campaign_num": request.get("campaign_num"),
            "evaluation_summary": {
                "total_candidates_evaluated": 0,
                "suitable_candidates": 0,
                "potentially_suitable": 0,
                "not_suitable": 0,
                "evaluation_timestamp": datetime.now().isoformat(),
                "evaluator": self.name
            },
            "suitable_candidates": [],
            "potentially_suitable": [],
            "not_suitable_summary": {"count": 0, "candidates": []},
            "recommended_for_scraping": []
        }

# Factory function for easy instantiation
def create_candidate_evaluation_agent() -> CandidateEvaluationAgent:
    """Create a new Candidate Evaluation Agent instance."""
    return CandidateEvaluationAgent()