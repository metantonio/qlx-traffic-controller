import os
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.SkillInjector")

def inject_skills_into_prompt(base_prompt: str, working_directory: str = None, assigned_skills: list[str] = None, agent_id: str = None) -> str:
    """Scans for assigned skills and .cursorrules and appends them to the prompt."""
    if not working_directory:
        resolved_pwd = os.path.abspath("./workspace")
    else:
        resolved_pwd = os.path.abspath(working_directory)
            
    injected_prompt = base_prompt or ""
    skills_content = []
    
    # 1. Determine Skills Root based on agent_id (Home Directory vs. Generic Workspace)
    skills_root = None
    
    if agent_id:
        from backend.kernel.agent_manager import agent_manager
        agent = agent_manager.get_agent(agent_id)
        
        # Use configured working_directory as the "Home" for skills
        # This is where .agents/skills/ lives for that agent
        agent_home = None
        if agent and agent.working_directory:
            agent_home = os.path.abspath(agent.working_directory)
        else:
            # Fallback for built-in or legacy agents
            agent_home = os.path.abspath(os.path.join(".", "workspace", agent_id))
            
        potential_root = os.path.join(agent_home, ".agents", "skills")
        if os.path.exists(potential_root):
             skills_root = potential_root
             
    # Fallback to climbing from current working directory if not found in home
    if not skills_root:
        curr = resolved_pwd
        while curr and os.path.dirname(curr) != curr: # Stop at root
            potential_root = os.path.join(curr, ".agents", "skills")
            if os.path.exists(potential_root):
                skills_root = os.path.abspath(potential_root)
                break
            curr = os.path.dirname(curr)
    
    # Final fallback to absolute relative path (software_architect root)
    if not skills_root:
        potential_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".agents", "skills"))
        if os.path.exists(potential_root):
            skills_root = potential_root

    if skills_root and os.path.exists(skills_root):
        if assigned_skills is not None:
            # ISOLATION MODE: ONLY inject explicitly assigned skills (could be empty list)
            for skill_name in assigned_skills:
                skill_path = os.path.join(skills_root, skill_name)
                if os.path.exists(skill_path):
                    for root, _, files in os.walk(skill_path):
                        for file in files:
                            if file.endswith(".md"):
                                file_path = os.path.join(root, file)
                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        content = f.read()
                                        rel_path = os.path.relpath(file_path, resolved_pwd)
                                        skills_content.append(f"\n--- INJECTED KNOWLEDGE: {rel_path} ---\n{content}\n")
                                except Exception as e:
                                    logger.error(f"Failed to read skill file {file_path}: {e}")
                else:
                    logger.warning(f"Skill '{skill_name}' assigned to agent but not found at {skill_path}")
        else:
            # LEGACY/BROWSE MODE: No skills list provided, scan everything
            for root, _, files in os.walk(skills_root):
                for file in files:
                    if file.endswith(".md"):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                rel_path = os.path.relpath(file_path, resolved_pwd)
                                skills_content.append(f"\n--- INJECTED KNOWLEDGE: {rel_path} ---\n{content}\n")
                        except Exception as e:
                            logger.error(f"Failed to read skill file {file_path}: {e}")
    
    # 2. Check for standard .cursorrules file (always in the specific working directory)
    cursorrules_path = os.path.join(resolved_pwd, ".cursorrules")
    if os.path.exists(cursorrules_path):
        try:
             with open(cursorrules_path, "r", encoding="utf-8") as f:
                  skills_content.append(f"\n--- PROJECT RULES: .cursorrules ---\n{f.read()}\n")
        except Exception as e:
             logger.error(f"Failed to read .cursorrules at {cursorrules_path}: {e}")
             
    if skills_content:
        injected_prompt += "\n\n=== AUTOMATICALLY INJECTED WORKSPACE SKILLS & RULES ===\n"
        injected_prompt += "You MUST follow these rules and guidelines strictly during your execution:\n"
        injected_prompt += "".join(skills_content)
        logger.info(f"Injected {len(skills_content)} skill/rule files into prompt from {resolved_pwd} (Skills: {assigned_skills})")
        
    return injected_prompt
