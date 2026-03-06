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
    workflow_id = Column(String, index=True, nullable=True)
    workflow_step = Column(Integer, nullable=True)
    
    # Resource Limits stored as JSON
    resource_limits = Column(JSON)
    
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
