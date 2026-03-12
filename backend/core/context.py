from contextvars import ContextVar

# System-wide context to track which AI process is currently executing a tool.
# 'kernel' is the default for system processes.
current_pid = ContextVar("current_pid", default="kernel")
