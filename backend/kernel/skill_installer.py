import os
import json
import zipfile
import io
import requests
import shutil
from typing import Optional, Dict, Any
from backend.kernel.agent_manager import CustomAgent, agent_manager

SKILLS_WORKSPACE_ROOT = os.path.join(os.getcwd(), "workspace")

class SkillInstallationError(Exception):
    pass

def download_and_install_skill(slug: str, version: Optional[str] = None) -> CustomAgent:
    """
    Downloads a skill package from ClawHub, extracts it to the workspace,
    and registers it as a CustomAgent.
    """
    # 1. Construct Download URL
    url = f"https://clawhub.ai/api/v1/download?slug={slug}"
    if version:
        url += f"&version={version}"

    # 2. Download the ZIP file
    print(f"Downloading skill package from {url}...")
    try:
        response = requests.get(url, timeout=30)
        # ClawHub API returns 429 if rate limited or other errors, check explicitly
        if response.status_code != 200:
            error_message = f"HTTP {response.status_code}"
            try:
                error_body = response.text
                if error_body:
                    error_message += f": {error_body}"
            except:
                pass
            raise SkillInstallationError(f"Failed to download skill '{slug}': {error_message}")
    except requests.exceptions.RequestException as e:
        raise SkillInstallationError(f"Network error while downloading skill '{slug}': {e}")

    # 3. Extract the ZIP file into a unique workspace directory
    skill_dir = os.path.join(SKILLS_WORKSPACE_ROOT, slug)
    
    # Clean up existing directory if it exists to ensure a fresh install
    if os.path.exists(skill_dir):
        shutil.rmtree(skill_dir)
        
    os.makedirs(skill_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(skill_dir)
    except zipfile.BadZipFile:
        raise SkillInstallationError(f"Downloaded file for skill '{slug}' is not a valid ZIP archive.")
        
    # 4. Parse SKILL.md to extract prompt and configuration
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    
    system_prompt = f"You are the {slug} agent." # Fallback
    agent_name = slug
    
    if os.path.exists(skill_md_path):
        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic parsing: extract YAML frontmatter if present
            if content.startswith('---'):
                end_frontmatter = content.find('---', 3)
                if end_frontmatter != -1:
                    frontmatter_str = content[3:end_frontmatter].strip()
                    # A very simple YAML parser just for Name/Description
                    for line in frontmatter_str.split('\n'):
                        if line.lower().startswith('name:'):
                            agent_name = line.split(':', 1)[1].strip().strip('"\'')
                    
                    # The rest is the system prompt
                    system_prompt = content[end_frontmatter+3:].strip()
                else:
                    system_prompt = content.strip()
            else:
                system_prompt = content.strip()
                
        except Exception as e:
            print(f"Warning: Failed to parse SKILL.md for {slug}: {e}")
            
    # 5. Create or update the CustomAgent definition
    # Relative path from project root to the workspace directory
    relative_working_dir = os.path.relpath(skill_dir, os.getcwd())
    # Normalize to forward slashes
    relative_working_dir = relative_working_dir.replace('\\', '/')
    
    new_agent_data = {
        "id": slug,
        "name": agent_name,
        "role": f"Skill Agent: {agent_name}",
        "goal": f"Execute the {agent_name} skill.",
        "backstory": "Installed via ClawHub Skills Store.",
        "system_prompt": system_prompt,
        "provider": "anthropic", # Default or configurable
        "model": "claude-3-7-sonnet-20250219", # Default capable model
        "temperature": 0.2,
        "static_tools": ["read_file", "write_file_safe", "list_directory", "shell_execute", "append_to_file", "delegate_to_agent"], # Standard agent tools
        "mcp_servers": [],
        "working_directory": relative_working_dir
    }
    
    # Create the agent object
    agent = CustomAgent(**new_agent_data)
    
    # Save it using the agent manager
    agent_manager.agents[slug] = agent
    agent_manager._save_agents()
    
    return agent
