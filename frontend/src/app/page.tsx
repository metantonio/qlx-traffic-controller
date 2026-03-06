"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import ProcessMonitor from "@/components/Kernel/ProcessMonitor";
import TaskSchedulerVisualizer from "@/components/Kernel/TaskSchedulerVisualizer";
import ToolManager from "@/components/Kernel/ToolManager";
import CommandMonitor, { CommandEvent } from "@/components/Monitoring/CommandMonitor";
import AgentConversationModal, { Message } from '@/components/Kernel/AgentConversationModal';
import KnowledgeGraphExplorer from "@/components/Kernel/KnowledgeGraphExplorer";
import ModelSelector from "@/components/Kernel/ModelSelector";
import AgentSelector from "@/components/Kernel/AgentSelector";
import WorkflowManagerModal from "@/components/Kernel/WorkflowManagerModal";
import HistoryView from "@/components/Kernel/HistoryView";
import { GitBranch, History, LayoutDashboard } from "lucide-react";

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
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [isWorkflowModalOpen, setIsWorkflowModalOpen] = useState(false);
  const [activeWorkflow, setActiveWorkflow] = useState<{
    id: string;
    name: string;
    stepIndex: number;
    totalSteps: number;
    status: string;
    currentPid?: string;
  } | null>(null);
  const [activeView, setActiveView] = useState<'dashboard' | 'history'>('dashboard');
  const [historyPid, setHistoryPid] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const handleSpawnAgent = useCallback((manualTask?: string, parent_pid?: string, initial_history?: Message[]) => {
    const finalTask = manualTask || taskText;
    if (!finalTask.trim() || !wsRef.current) return;

    const payload = {
      action: 'spawn',
      agent_name: selectedAgentId || 'kernel_agent',
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
  }, [taskText, enabledTools, llmProvider, llmModel, selectedAgentId]);

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
      } else if (data.type === "workflow_progress") {
        const payload = data.payload;
        setActiveWorkflow(prev => {
          if (payload.status === "completed") return null;
          return {
            id: payload.workflow_id,
            name: payload.workflow_name || prev?.name || "Pipeline",
            stepIndex: payload.step_index ?? prev?.stepIndex,
            totalSteps: payload.total_steps ?? prev?.totalSteps,
            status: payload.status,
            currentPid: payload.pid || prev?.currentPid
          };
        });
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
          <AgentSelector
            onSelect={(agent) => setSelectedAgentId(agent?.id || null)}
            currentAgentId={selectedAgentId}
          />
          <div className="h-10 w-px bg-neutral-800 hidden md:block" />
          <ModelSelector
            onSelect={(p, m) => {
              setLlmProvider(p);
              setLlmModel(m);
            }}
            currentProvider={llmProvider}
            currentModel={llmModel}
          />
          <div className="h-10 w-px bg-neutral-800 hidden md:block" />
          <button
            onClick={() => setIsWorkflowModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 rounded-2xl hover:border-blue-500/50 hover:bg-neutral-800 transition-all group"
          >
            <GitBranch size={16} className="text-neutral-500 group-hover:text-blue-400 transition-colors" />
            <span className="text-[10px] text-neutral-400 uppercase font-black tracking-widest">Pipelines</span>
          </button>
          <div className="h-10 w-px bg-neutral-800 hidden md:block" />
          <button
            onClick={() => setActiveView(activeView === 'dashboard' ? 'history' : 'dashboard')}
            className={`flex items-center gap-2 px-4 py-2 border rounded-2xl transition-all group ${activeView === 'history'
              ? 'bg-blue-600 border-blue-500 text-white'
              : 'bg-neutral-900 border-neutral-800 hover:border-blue-500/50 hover:bg-neutral-800'
              }`}
          >
            {activeView === 'dashboard' ? (
              <>
                <History size={16} className="text-neutral-500 group-hover:text-blue-400 transition-colors" />
                <span className="text-[10px] text-neutral-400 uppercase font-black tracking-widest">History</span>
              </>
            ) : (
              <>
                <LayoutDashboard size={16} className="text-white transition-colors" />
                <span className="text-[10px] text-white uppercase font-black tracking-widest">Dashboard</span>
              </>
            )}
          </button>
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
      {activeView === 'dashboard' ? (
        <>
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
        </>
      ) : (
        <div className="flex-grow overflow-hidden flex flex-col">
          <HistoryView onSelectPid={setHistoryPid} onBack={() => setActiveView('dashboard')} />
        </div>
      )}

      {/* Pipeline HUD */}
      {activeWorkflow && (
        <div className="fixed bottom-8 right-8 z-40 animate-in slide-in-from-bottom-10 fade-in duration-300">
          <div className="bg-neutral-900/90 backdrop-blur-xl border border-blue-500/30 p-6 rounded-3xl shadow-2xl shadow-blue-500/10 w-80 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="text-blue-400 rotate-90" size={18} />
                <span className="text-xs font-black uppercase tracking-widest text-blue-400">Neural Pipeline</span>
              </div>
              <div className="px-2 py-0.5 bg-blue-500/20 rounded text-[10px] font-bold text-blue-300">
                STEP {activeWorkflow.stepIndex + 1}/{activeWorkflow.totalSteps}
              </div>
            </div>

            <div>
              <h4 className="text-white font-bold truncate">{activeWorkflow.name}</h4>
              <p className="text-neutral-400 text-[10px] uppercase font-medium tracking-tight">Status: {activeWorkflow.status.replace('_', ' ')}</p>
            </div>

            <div className="relative h-1.5 w-full bg-neutral-800 rounded-full overflow-hidden">
              <div
                className="absolute top-0 left-0 h-full bg-blue-500 transition-all duration-1000 ease-out"
                style={{ width: `${((activeWorkflow.stepIndex + 1) / activeWorkflow.totalSteps) * 100}%` }}
              />
            </div>

            {activeWorkflow.currentPid && (
              <div className="flex items-center gap-2 bg-black/40 p-2 rounded-xl border border-white/5">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-[10px] font-mono text-neutral-400">ACTIVE PID: {activeWorkflow.currentPid}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedPid && (
        <AgentConversationModal
          pid={selectedPid}
          onClose={() => setSelectedPid(null)}
          onContinue={handleContinue}
        />
      )}
      {historyPid && (
        <AgentConversationModal
          pid={historyPid}
          onClose={() => setHistoryPid(null)}
          readOnly={true}
        />
      )}
      {isWorkflowModalOpen && (
        <WorkflowManagerModal
          isOpen={isWorkflowModalOpen}
          onClose={() => setIsWorkflowModalOpen(false)}
        />
      )}
    </div>
  );
}
