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
    <div className="min-h-screen bg-[#0a0a0b] text-neutral-100 p-8 font-sans antialiased selection:bg-blue-500/30 overflow-x-hidden">
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden -z-10">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[0%] -right-[5%] w-[30%] h-[50%] bg-purple-600/5 blur-[100px] rounded-full"></div>
      </div>

      <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-12 border-b border-neutral-800/50 pb-8">
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
            <div className="px-3 py-1 bg-neutral-800/50 rounded-xl border border-neutral-700/30">
              <span className="text-[10px] text-neutral-500 font-bold uppercase tracking-widest block mb-0.5">Uptime</span>
              <span className="text-lg font-mono text-blue-400 leading-none">04:12:01</span>
            </div>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
        <div className="xl:col-span-8 space-y-8 min-w-0">
          <section className="relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-8 opacity-5">
              <Cpu className="w-64 h-64 text-blue-400" />
            </div>
            <div className="p-8 bg-neutral-900/60 border border-neutral-800/80 rounded-[2rem] shadow-2xl backdrop-blur-xl relative">
              <div className="flex items-center gap-3 mb-6">
                <div className="flex items-center justify-center w-10 h-10 rounded-2xl bg-blue-600/10 text-blue-500 border border-blue-500/20">
                  <Zap size={20} />
                </div>
                <div>
                  <h2 className="text-xl font-bold tracking-tight">Main Command Interface</h2>
                  <p className="text-xs text-neutral-500 font-mono tracking-tighter">Enter task parameters for the neural scheduler</p>
                </div>
              </div>
              <div className="relative group">
                <textarea
                  value={taskText}
                  onChange={(e) => setTaskText(e.target.value)}
                  placeholder="Initiate a new autonomous thread (e.g. 'Analyze logs in current folder and summarize errors')"
                  className="w-full bg-neutral-950/50 border border-neutral-800 text-white rounded-3xl py-5 px-6 outline-none focus:border-blue-500/50 transition-all focus:ring-1 focus:ring-blue-500/10 min-h-[140px] text-lg placeholder:text-neutral-700 font-medium leading-relaxed group-hover:border-neutral-700"
                />
                <button
                  onClick={() => handleSpawnAgent()}
                  className="absolute bottom-4 right-4 bg-blue-600 hover:bg-blue-500 text-white px-8 py-3.5 rounded-2xl font-bold shadow-lg shadow-blue-600/20 transition-all transform active:scale-95 flex items-center gap-2 group/btn"
                >
                  <Cpu size={18} className="group-hover/btn:rotate-12 transition-transform" />
                  Initiate Sequence
                </button>
              </div>
            </div>
          </section>

          <TaskSchedulerVisualizer metrics={kernelMetrics} />
          <CommandMonitor events={events} />
        </div>

        <div className="xl:col-span-4 space-y-8">
          <ToolManager onToolsChange={handleToolsChange} />

          <div className="bg-neutral-900/40 border border-neutral-800/50 rounded-[2rem] p-6 backdrop-blur-md">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-md font-bold text-neutral-300">Knowledge Graph</h2>
                <p className="text-[10px] text-neutral-500 font-mono tracking-widest uppercase">Memory Context Layer</p>
              </div>
            </div>
            <div className="h-[400px]">
              <KnowledgeGraphExplorer />
            </div>
          </div>

          <ProcessMonitor processes={kernelMetrics?.processes || []} onSelect={setSelectedPid} />
        </div>
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

// Missing icons from view_file before update
function Zap(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 14.71 12 2.29l1 9.06L20 9.29l-8 12.42-1-9.06L4 14.71z" />
    </svg>
  );
}

function Cpu(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect width="16" height="16" x="4" y="4" rx="2" />
      <rect width="6" height="6" x="9" y="9" rx="1" />
      <path d="M15 2v2" />
      <path d="M15 20v2" />
      <path d="M2 15h2" />
      <path d="M2 9h2" />
      <path d="M20 15h2" />
      <path d="M20 9h2" />
      <path d="M9 2v2" />
      <path d="M9 20v2" />
    </svg>
  );
}
