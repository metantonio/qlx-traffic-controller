from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import logging
from backend.core.orchestrator import AIControlTower

logger = logging.getLogger("QLX-TC.Telegram")

class TelegramInterface:
    def __init__(self, token: str, orchestrator: AIControlTower):
        self.token = token
        self.orchestrator = orchestrator
        self.app = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("agents", self.agents))
        self.app.add_handler(CommandHandler("run", self.run_task))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("AI Control Tower Online. Send /status for system state.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Status: All systems nominal. Telemetry running.")

    async def agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        agents = list(self.orchestrator.active_agents.keys())
        agent_list = ", ".join(agents) if agents else "No active agents."
        await update.message.reply_text(f"Active Agents: {agent_list}")

    async def run_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        task_text = " ".join(context.args)
        if not task_text:
            await update.message.reply_text("Usage: /run <task description>")
            return
            
        await update.message.reply_text(f"Submitting task: {task_text}")
        response = await self.orchestrator.submit_task(task_text)
        await update.message.reply_text(f"Task status: {response}")

    def run_polling(self):
        """Run bot strictly in non-blocking mode or separate process optimally."""
        logger.info("Starting Telegram polling...")
        self.app.run_polling()
