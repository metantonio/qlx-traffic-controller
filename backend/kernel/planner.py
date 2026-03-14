import logging
import json
import re
from typing import List, Optional, Dict, Any
from backend.llm.provider import LLMProvider
from backend.kernel.agent_manager import agent_manager

logger = logging.getLogger("QLX-TC.Kernel.Planner")

class PlannerAgent:
    """
    Analyzes user requests to determine the required agent sequence.
    Mirrors OpenClaw's Request Analysis pattern.
    """
    
    def __init__(self):
        self._llm = None
        
    @property
    def llm(self):
        if self._llm is None:
            self._llm = LLMProvider()
        return self._llm
        
    def _get_specialist_definitions(self) -> str:
        """Fetch human-readable descriptions of all available specialists."""
        agents = agent_manager.list_agents()
        defs = []
        for agent in agents:
            defs.append(f"- {agent.id}: {agent.description}")
        return "\n".join(defs)

    def _apply_hardcoded_rules(self, request: str, sequence: List[str]) -> List[str]:
        """Apply business logic rules that override or augment LLM planning."""
        req_lower = request.lower()
        
        # Rule: If it's a "create" request for a full app/game, ensure architect is first
        if any(w in req_lower for w in ["create", "develop", "build", "game", "app"]):
            if "software_architect" not in sequence:
                sequence = ["software_architect"] + sequence
                
        # Rule: Ensure QA is at the end if any development happened
        needs_qa = any(s in sequence for s in ["frontend_developer", "backend_developer", "software_architect"])
        if needs_qa and sequence[-1] != "qa_tester":
             if "qa_tester" in sequence:
                 sequence.remove("qa_tester")
             sequence.append("qa_tester")
        
        return sequence

    async def analyze_request(self, request: str) -> Dict[str, Any]:
        """
        Analyzes a user request and returns a dict with 'sequence' and 'project_name'.
        """
        specialists = self._get_specialist_definitions()
        
        system_prompt = f"""You are the Lead Project Planner (Mission Control). 
Your job is to break down complex user requests into a sequence of specialist AI agents AND identify a logical project name.

AVAILABLE SPECIALISTS:
{specialists}

PLANNING STRATEGY:
1. For ANY new project or significant feature:
   - Identify a concise, descriptive project name (e.g., "space_invaders", "traffic_api").
   - Anchoring: You MUST assume the project will live in 'workspace/project_name'.
   - Start with 'software_architect' to define the plan and architecture.
   - Follow with the relevant developers ('frontend_developer', 'backend_developer').
   - Finish with 'qa_tester' for verification.

2. Norms:
   - Project name should be lowercase and use underscores (snake_case).
   - If no new project is needed (e.g., simple file edit), project_name can be null.

OUTPUT FORMAT:
Return ONLY a JSON object literal. No extra text.
Format:
{{
  "sequence": ["agent_id1", "agent_id2"],
  "project_name": "normalized_project_name"
}}
"""
        
        user_prompt = f"Analyze and plan for this request: {request}"
        
        try:
            response = await self.llm.agenerate(system_prompt, user_prompt)
            # Find the JSON block
            json_match = re.search(r"({.*})", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Fallback to loose parsing if LLM failed JSON literal
                logger.warning(f"Planner response was not a JSON literal: {response}")
                return {"sequence": ["software_architect"], "project_name": "default_project"}

            raw_sequence = data.get("sequence", [])
            project_name = data.get("project_name", "default_project")
            
            # Normalize sequence
            sequence = [s.strip().lower() for s in raw_sequence if isinstance(s, str)]
            
            # Filter against actual agent IDs
            all_agent_ids = {a.id for a in agent_manager.list_agents()}
            validated_sequence = [s for s in sequence if s in all_agent_ids]
            
            # Apply heuristic overrides
            final_sequence = self._apply_hardcoded_rules(request, validated_sequence)
            
            if not final_sequence:
                logger.warning(f"Planner failed to generate valid sequence for: {request}.")
                final_sequence = ["software_architect"]
                
            logger.info(f"Mission Plan for '{request[:30]}...': {final_sequence} -> Project: {project_name}")
            return {
                "sequence": final_sequence,
                "project_name": project_name
            }
            
        except Exception as e:
            logger.error(f"Planner error: {e}")
            return {"sequence": ["software_architect"], "project_name": "default_project"}

# Singleton instance
planner_agent = PlannerAgent()
