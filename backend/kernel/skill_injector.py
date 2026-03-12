import os
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.SkillInjector")

def inject_skills_into_prompt(base_prompt: str, working_directory: str = None) -> str:
    """Scans for .agents/skills and .cursorrules in the working directory and appends them to the prompt."""
    if not working_directory:
        # Default to the centralized workspace if no specific working directory is set
        resolved_pwd = os.path.abspath("./workspace")
    else:
        resolved_pwd = os.path.abspath(working_directory)
            
    injected_prompt = base_prompt or ""
    skills_content = []
    
    # 1. Check for Vercel/Cursor skills in .agents/skills/**/*.md
    skills_path = os.path.join(resolved_pwd, ".agents", "skills")
    if os.path.exists(skills_path):
        for root, _, files in os.walk(skills_path):
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
    
    # 2. Check for standard .cursorrules file
    cursorrules_path = os.path.join(resolved_pwd, ".cursorrules")
    if os.path.exists(cursorrules_path):
        try:
             with open(cursorrules_path, "r", encoding="utf-8") as f:
                 skills_content.append(f"\n--- PROJECT RULES: .cursorrules ---\n{f.read()}\n")
        except Exception as e:
             logger.error(f"Failed to read .cursorrules: {e}")
             
    if skills_content:
        injected_prompt += "\n\n=== AUTOMATICALLY INJECTED WORKSPACE SKILLS & RULES ===\n"
        injected_prompt += "You MUST follow these rules and guidelines strictly during your execution:\n"
        injected_prompt += "".join(skills_content)
        logger.info(f"Injected {len(skills_content)} skill/rule files into prompt from {resolved_pwd}")
        
    return injected_prompt
