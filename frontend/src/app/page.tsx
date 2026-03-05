"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import ProcessMonitor from "@/components/Kernel/ProcessMonitor";
import TaskSchedulerVisualizer from "@/components/Kernel/TaskSchedulerVisualizer";
import ToolManager from "@/components/Kernel/ToolManager";
import CommandMonitor, { CommandEvent } from "@/components/Monitoring/CommandMonitor";
import AgentConversationModal, { Message } from '@/components/Kernel/AgentConversationModal';
import KnowledgeGraphExplorer from "@/components/Kernel/KnowledgeGraphExplorer";
import ModelSelector from "@/components/Kernel/ModelSelector";

export interface ProcessData {
  pid: string;
  agent: string;
  state: string;
  mem: string;
  cpu: string;
}

export interface KernelMetrics {
  queues: { HIGH: number; MEDIUM: number; LOW: number };
  processes: ProcessData[];
  active_count: number;
}

export default function Dashboard() {
  const [events, setEvents] = useState<CommandEvent[]>([]);
  const [kernelMetrics, setKernelMetrics] = useState<KernelMetrics | null>(null);
  const [taskText, setTaskText] = useState("");
  const [enabledTools, setEnabledTools] = useState<string[]>([]);
  const [selectedPid, setSelectedPid] = useState<string | null>(null);
  const [llmProvider, setLlmProvider] = useState<string>("");
  const [llmModel, setLlmModel] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);

  const handleSpawnAgent = useCallback((manualTask?: string, parent_pid?: string, initial_history?: Message[]) => {
    const finalTask = manualTask || taskText;
    if (!finalTask.trim() || !wsRef.current) return;

    const payload = {
      action: 'spawn',
      agent_name: 'kernel_agent',
      task: finalTask,
      allowed_tools: enabledTools,
      parent_pid: parent_pid,
      initial_history: initial_history,
      provider: llmProvider,
      model: llmModel
    };

    if (wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      if (!manualTask) setTaskText('');
    }
  }, [taskText, enabledTools, llmProvider, llmModel]);

  const handleContinue = useCallback((pid: string, followUp: string, history: Message[]) => {
    handleSpawnAgent(followUp, pid, history);
  }, [handleSpawnAgent]);

  const handleToolsChange = useCallback((tools: string[]) => {
    setEnabledTools(tools);
  }, []);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/ws";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "system_metrics") {
        setKernelMetrics(data.payload);
      } else {
        setEvents((prev) => [data, ...prev].slice(0, 50));
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-neutral-100 p-8 font-sans antialiased selection:bg-blue-500/30 overflow-x-hidden flex flex-col">
      {/* Background elements */}
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden -z-10">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[0%] -right-[5%] w-[30%] h-[50%] bg-purple-600/5 blur-[100px] rounded-full"></div>
      </div>

      {/* Header */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-8 border-b border-neutral-800/50 pb-6 shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="h-2 w-2 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.6)]"></div>
            <span className="text-xs font-bold text-blue-500 tracking-[0.2em] uppercase">System v0.1.0</span>
          </div>
          <h1 className="text-4xl font-black tracking-tight bg-gradient-to-br from-white via-neutral-200 to-neutral-500 bg-clip-text text-transparent">
            QLX Traffic Controller
          </h1>
          <p className="text-neutral-500 text-sm mt-1 font-medium tracking-wide">Autonomous Neural-Process Orchestrator</p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <ModelSelector
            onSelect={(p, m) => {
              setLlmProvider(p);
              setLlmModel(m);
            }}
            currentProvider={llmProvider}
            currentModel={llmModel}
          />
          <div className="h-10 w-px bg-neutral-800 hidden md:block" />
          <div className="flex gap-4 p-1 bg-neutral-900 border border-neutral-800 rounded-2xl">
            <div className="px-3 py-1 bg-neutral-800/50 rounded-xl border border-neutral-700/30">
              <span className="text-[10px] text-neutral-500 font-bold uppercase tracking-widest block mb-0.5">Processes</span>
              <span className="text-lg font-mono text-emerald-400 leading-none">{kernelMetrics?.active_count || 0}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 flex-grow overflow-hidden mb-8">
        {/* TOP LEFT: Workers (Process Monitor) */}
        <div className="xl:col-span-4 space-y-6 overflow-y-auto custom-scrollbar pr-2">
          <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-3xl p-6 shadow-xl backdrop-blur-xl">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <h2 className="text-sm font-bold text-neutral-400 uppercase tracking-widest">Active Workers</h2>
            </div>
            <ProcessMonitor metrics={kernelMetrics} onProcessClick={setSelectedPid} />
          </div>

          <ToolManager onToolsChange={handleToolsChange} />
        </div>

        {/* TOP RIGHT / MIDDLE: Metrics & Vis */}
        <div className="xl:col-span-8 space-y-6 overflow-y-auto custom-scrollbar pr-2">
          <TaskSchedulerVisualizer metrics={kernelMetrics} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-neutral-900/40 border border-neutral-800/50 rounded-[2rem] p-6 backdrop-blur-md">
              <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">Knowledge Graph</h2>
              <div className="h-[300px]">
                <KnowledgeGraphExplorer />
              </div>
            </div>
            <div className="bg-neutral-900/40 border border-neutral-800/50 rounded-[2rem] p-6 backdrop-blur-md overflow-hidden">
              <h2 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-4">System Events</h2>
              <div className="h-[300px]">
                <CommandMonitor events={events} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM CENTER: Chat / Command Interface */}
      <div className="max-w-4xl w-full mx-auto shrink-0 pb-4">
        <section className="relative overflow-hidden group">
          <div className="p-6 bg-neutral-900/80 border border-neutral-800/80 rounded-[2.5rem] shadow-2xl backdrop-blur-2xl relative border-t-neutral-700/50 shadow-blue-500/5">
            <div className="relative flex items-end gap-4">
              <div className="flex-grow relative">
                <textarea
                  value={taskText}
                  onChange={(e) => setTaskText(e.target.value)}
                  placeholder="Initiate a new autonomous thread..."
                  className="w-full bg-neutral-950/80 border border-neutral-800 text-white rounded-3xl py-4 px-6 outline-none focus:border-blue-500/50 transition-all min-h-[80px] text-md placeholder:text-neutral-700 font-medium leading-relaxed resize-none"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSpawnAgent();
                    }
                  }}
                />
              </div>
              <button
                onClick={() => handleSpawnAgent()}
                className="h-14 w-14 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-bold shadow-lg shadow-blue-600/20 transition-all transform active:scale-95 flex items-center justify-center group/btn shrink-0"
                title="Initiate Sequence"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="group-hover/btn:translate-x-0.5 group-hover/btn:-translate-y-0.5 transition-transform">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              </button>
            </div>
            <div className="flex items-center gap-4 mt-3 px-4">
              <span className="text-[10px] text-neutral-600 font-mono">READY // {llmProvider}:{llmModel}</span>
              <div className="h-px flex-grow bg-neutral-800/50" />
              <span className="text-[10px] text-neutral-600 font-mono capitalize">{enabledTools.length} Tools Enabled</span>
            </div>
          </div>
        </section>
      </div>

      {selectedPid && (
        <AgentConversationModal
          pid={selectedPid}
          onClose={() => setSelectedPid(null)}
          onContinue={handleContinue}
        />
      )}
    </div>
  );
}
