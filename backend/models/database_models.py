from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from backend.core.database import Base
import datetime
import uuid

class DbProcess(Base):
    __tablename__ = "processes"

    pid = Column(String, primary_key=True, index=True)
    agent_name = Column(String)
    task_description = Column(String)
    state = Column(String)
    working_directory = Column(String, nullable=True)
    workflow_id = Column(String, index=True, nullable=True)
    workflow_step = Column(Integer, nullable=True)
    proposed_plan = Column(JSON, nullable=True) # Metadata for the 'Proceed' UI button
    has_proceeded = Column(Integer, default=0) # 1 if Proceed button was clicked
    
    # resource limits
    resource_limits = Column(JSON)
    
    memory_context = Column(JSON, nullable=True) # Persistent meta-state
    original_request = Column(String, nullable=True) # Goal anchor
    
    # Metrics
    tokens_used = Column(Integer, default=0)
    tools_called = Column(Integer, default=0)
    start_time = Column(Float)
    end_time = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    messages = relationship("DbMessage", back_populates="process", cascade="all, delete-orphan")

class DbMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(String, ForeignKey("processes.pid"))
    role = Column(String) # system, user, assistant, tool
    content = Column(String)
    tool_calls = Column(JSON, nullable=True)
    tool_call_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    process = relationship("DbProcess", back_populates="messages")

class DbMCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    command = Column(String)
    args = Column(JSON) # List[str]
    env_encrypted = Column(String, nullable=True) # Encrypted JSON
    enabled = Column(Integer, default=1) # 1 for True, 0 for False (SQLite preference)
    transport = Column(String, default="stdio")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DbAllowedDirectory(Base):
    __tablename__ = "allowed_directories"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
