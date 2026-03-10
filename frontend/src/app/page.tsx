"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import ProcessMonitor from "@/components/Kernel/ProcessMonitor";
import TaskSchedulerVisualizer from "@/components/Kernel/TaskSchedulerVisualizer";
import CommandMonitor, { CommandEvent } from "@/components/Monitoring/CommandMonitor";
import AgentConversationModal, { Message } from '@/components/Kernel/AgentConversationModal';
import KnowledgeGraphExplorer from "@/components/Kernel/KnowledgeGraphExplorer";
import ModelSelector from "@/components/Kernel/ModelSelector";
import AgentSelector from "@/components/Kernel/AgentSelector";
import WorkflowManagerModal from "@/components/Kernel/WorkflowManagerModal";
import HistoryView from "@/components/Kernel/HistoryView";
import BatchManagerModal from "@/components/Kernel/BatchManagerModal";
import ExtensionsView from "@/components/Kernel/ExtensionsView";
import { GitBranch, History, LayoutDashboard, Layers, Cpu, MessageSquare, WifiOff, RefreshCw } from "lucide-react";

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
  const [enabledTools] = useState<string[]>([]);
  const [selectedPid, setSelectedPid] = useState<string | null>(null);
  const [llmProvider, setLlmProvider] = useState<string>("");
  const [llmModel, setLlmModel] = useState<string>("");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [isWorkflowModalOpen, setIsWorkflowModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [activeWorkflow, setActiveWorkflow] = useState<{
    id: string;
    name: string;
    stepIndex: number;
    totalSteps: number;
    status: string;
    currentPid?: string;
  } | null>(null);
  const [activeView, setActiveView] = useState<'dashboard' | 'extensions' | 'history'>('dashboard');
  const [historyPid, setHistoryPid] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'connecting' | 'error'>('connecting');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  const handleSpawnAgent = useCallback((manualTask?: string, parent_pid?: string, initial_history?: Message[]) => {
    const finalTask = manualTask || taskText;
    if (!finalTask.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const payload = {
      action: 'spawn',
      agent_name: selectedAgentId || 'kernel',
      task: finalTask,
      allowed_tools: enabledTools,
      parent_pid: parent_pid,
      initial_history: initial_history,
      provider: llmProvider,
      model: llmModel
    };

    wsRef.current.send(JSON.stringify(payload));
    if (!manualTask) setTaskText('');
  }, [taskText, enabledTools, llmProvider, llmModel, selectedAgentId]);

  const handleContinue = useCallback((pid: string, followUp: string, history: Message[]) => {
    handleSpawnAgent(followUp, pid, history);
  }, [handleSpawnAgent]);

  const handleClearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const handleDismissProcess = useCallback(async (pid: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/processes/${pid}`, {
        method: 'DELETE'
      });
      if (!response.ok) {
        const err = await response.json();
        console.error("Failed to dismiss process:", err.error);
      }
    } catch (error) {
      console.error("Error dismissing process:", error);
    }
  }, []);

  const handleClearFinished = useCallback(async () => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/processes`, {
        method: 'DELETE'
      });
    } catch (error) {
      console.error("Error clearing finished processes:", error);
    }
  }, []);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/ws";
    Promise.resolve().then(() => setWsStatus('connecting'));
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('connected');
    };

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

    ws.onclose = () => {
      setWsStatus('disconnected');
      // Auto-reconnect after 3 seconds
      setTimeout(() => {
        setReconnectAttempts(prev => prev + 1);
      }, 3000);
    };

    ws.onerror = () => {
      setWsStatus('error');
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [reconnectAttempts]);

  return (
    <div className="h-screen bg-[#0a0a0b] text-neutral-100 font-sans antialiased selection:bg-blue-500/30 overflow-hidden flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-neutral-800/50 bg-neutral-900/20 backdrop-blur-xl flex flex-col shrink-0">
        <div className="p-6 border-b border-neutral-800/50">
          <div className="flex items-center gap-3 mb-1">
            <div className={`h-2.5 w-2.5 rounded-full ${wsStatus === 'connected' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.6)]' :
              wsStatus === 'connecting' ? 'bg-amber-500 animate-pulse' :
                'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.6)]'
              }`}></div>
            <span className={`text-[10px] font-black tracking-[0.2em] uppercase ${wsStatus === 'connected' ? 'text-emerald-500' :
              wsStatus === 'connecting' ? 'text-amber-500' :
                'text-red-500'
              }`}>
              {wsStatus === 'connected' ? 'Kernel Online' :
                wsStatus === 'connecting' ? 'Connecting...' :
                  'Kernel Offline'}
            </span>
          </div>
          <h1 className="text-xl font-black tracking-tighter text-white">QLX-Traffic-Controller</h1>
        </div>

        <nav className="flex-grow p-4 space-y-2">
          <button
            onClick={() => setActiveView('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all group ${activeView === 'dashboard' ? 'bg-blue-600 border border-blue-500 text-white shadow-lg shadow-blue-500/20' : 'text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/50'}`}
          >
            <LayoutDashboard size={18} />
            <span className="text-xs font-bold uppercase tracking-widest">Analytics</span>
          </button>

          <button
            onClick={() => setActiveView('history')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all group ${activeView === 'history' ? 'bg-blue-600 border border-blue-500 text-white shadow-lg shadow-blue-500/20' : 'text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/50'}`}
          >
            <History size={18} />
            <span className="text-xs font-bold uppercase tracking-widest">Logs</span>
          </button>

          <div className="py-4 px-4 text-[10px] font-black text-neutral-600 uppercase tracking-[0.2em]">Automation</div>

          <button
            onClick={() => setIsWorkflowModalOpen(true)}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/50"
          >
            <GitBranch size={18} />
            <span className="text-xs font-bold uppercase tracking-widest">Workflows</span>
          </button>

          <button
            onClick={() => setIsBatchModalOpen(true)}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/50"
          >
            <Layers size={18} />
            <span className="text-xs font-bold uppercase tracking-widest">Batches</span>
          </button>

          <div className="py-4 px-4 text-[10px] font-black text-neutral-600 uppercase tracking-[0.2em]">Extensions</div>

          <button
            onClick={() => setActiveView('extensions')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all group ${activeView === 'extensions' ? 'bg-orange-600 border border-orange-500 text-white shadow-lg shadow-orange-500/20' : 'text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/50'}`}
          >
            <Layers size={18} className={activeView === 'extensions' ? 'text-white' : 'group-hover:text-orange-400'} />
            <span className="text-xs font-bold uppercase tracking-widest">Skills</span>
          </button>
        </nav>

        <div className="p-6 border-t border-neutral-800/50">
          <div className="flex items-center gap-3 p-3 bg-neutral-900/50 border border-neutral-800 rounded-2xl">
            <div className="w-8 h-8 rounded-xl bg-neutral-800 flex items-center justify-center text-xs font-bold text-neutral-400">
              <Cpu size={14} />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] text-neutral-500 font-bold uppercase tracking-widest leading-none mb-1">Runtime</div>
              <div className="text-xs font-mono text-emerald-400 truncate tracking-tighter">stable_node_22</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-grow flex flex-col relative overflow-hidden">
        {/* Background elements */}
        <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden -z-10">
          <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full"></div>
          <div className="absolute bottom-[0%] -right-[5%] w-[30%] h-[50%] bg-purple-600/5 blur-[100px] rounded-full"></div>
        </div>

        {activeView === 'dashboard' ? (
          <div className="flex-grow flex flex-col overflow-hidden p-4 md:p-8">
            {/* Header - Fixed at top */}
            <header className="flex items-end justify-between mb-8 border-b border-neutral-800/50 pb-8 shrink-0">
              <div>
                <h2 className="text-4xl font-black tracking-tighter text-white">Dashboard</h2>
                <p className="text-neutral-500 text-sm mt-1 font-medium tracking-wide">Autonomous Neural-Process Orchestrator</p>
              </div>

              <div className="flex items-center gap-4">
                <AgentSelector
                  onSelect={(agent) => setSelectedAgentId(agent?.id || null)}
                  currentAgentId={selectedAgentId}
                  onViewChange={setActiveView}
                />
                <div className="h-10 w-px bg-neutral-800" />
                <ModelSelector
                  onSelect={(p, m) => {
                    setLlmProvider(p);
                    setLlmModel(m);
                  }}
                  currentProvider={llmProvider}
                  currentModel={llmModel}
                />
                <div className="h-10 w-px bg-neutral-800" />
                <div className="flex gap-4 p-1 bg-neutral-900 border border-neutral-800 rounded-2xl">
                  <div className="px-3 py-1 bg-neutral-800/50 rounded-xl border border-neutral-700/30">
                    <span className="text-[10px] text-neutral-500 font-bold uppercase tracking-widest block mb-0.5">Processes</span>
                    <span className="text-lg font-mono text-emerald-400 leading-none">{kernelMetrics?.active_count || 0}</span>
                  </div>
                </div>
              </div>
            </header>

            {/* Scrollable Center Content */}
            <div className="flex-grow overflow-y-auto custom-scrollbar pr-2 mb-8">
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                {/* TOP LEFT: Workers */}
                <div className="xl:col-span-4 space-y-8">
                  <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-3xl p-6 shadow-xl backdrop-blur-xl">
                    <div className="flex items-center gap-2 mb-6">
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.4)]" />
                      <h2 className="text-xs font-black text-neutral-400 uppercase tracking-[0.2em]">Active Threads</h2>
                    </div>
                    <ProcessMonitor
                      metrics={kernelMetrics}
                      onProcessClick={setSelectedPid}
                      onDismiss={handleDismissProcess}
                      onClearFinished={handleClearFinished}
                    />
                  </div>

                  <div className="bg-neutral-900/40 border border-neutral-800/50 rounded-3xl p-6 backdrop-blur-md">
                    <div className="flex items-center justify-between mb-6">
                      <h2 className="text-xs font-black text-neutral-500 uppercase tracking-[0.2em]">System State</h2>
                      <div className="px-2 py-0.5 bg-neutral-800 rounded text-[9px] font-mono text-neutral-500">LATEST_SYNC_2MS</div>
                    </div>
                    <div className="h-[300px]">
                      <KnowledgeGraphExplorer />
                    </div>
                  </div>
                </div>

                {/* TOP RIGHT / MIDDLE: Metrics & Vis */}
                <div className="xl:col-span-8 space-y-8">
                  <TaskSchedulerVisualizer metrics={kernelMetrics} />

                  <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-[2.5rem] p-8 shadow-xl backdrop-blur-xl shrink-0">
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-xl">
                          <MessageSquare size={16} className="text-blue-400" />
                        </div>
                        <h2 className="text-xs font-black text-neutral-400 uppercase tracking-[0.2em]">System Output</h2>
                      </div>
                    </div>
                    <div className="h-[400px]">
                      <CommandMonitor events={events} onClear={handleClearEvents} />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* BOTTOM CENTER: Chat Interface - Fixed at bottom */}
            <div className="max-w-4xl w-full mx-auto shrink-0">
              <section className="relative overflow-hidden group">
                <div className="p-6 bg-neutral-950/80 border border-neutral-800/80 rounded-[2.5rem] shadow-2xl backdrop-blur-2xl relative border-t-neutral-700/50 shadow-blue-500/5">
                  <div className="relative flex items-end gap-4">
                    <div className="flex-grow relative">
                      <textarea
                        value={taskText}
                        onChange={(e) => setTaskText(e.target.value)}
                        placeholder="Initiate a new autonomous thread..."
                        className="w-full bg-neutral-900/50 border border-neutral-800 text-white rounded-3xl py-5 px-8 outline-none focus:border-blue-500/50 transition-all min-h-[100px] text-lg placeholder:text-neutral-700 font-medium leading-relaxed resize-none"
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
                      disabled={wsStatus !== 'connected'}
                      className={`h-16 w-16 rounded-2xl font-bold shadow-lg transition-all transform active:scale-95 flex items-center justify-center group/btn shrink-0 ${wsStatus === 'connected'
                        ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/30'
                        : 'bg-neutral-800 text-neutral-600 cursor-not-allowed'
                        }`}
                    >
                      {wsStatus === 'connecting' ? (
                        <RefreshCw size={24} className="animate-spin" />
                      ) : wsStatus === 'connected' ? (
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="group-hover/btn:translate-x-0.5 group-hover/btn:-translate-y-0.5 transition-transform">
                          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                        </svg>
                      ) : (
                        <WifiOff size={24} />
                      )}
                    </button>
                  </div>
                  <div className="flex items-center gap-4 mt-4 px-6">
                    <span className="text-[10px] text-neutral-600 font-black tracking-widest uppercase">Kernel Ready</span>
                    <div className="h-px flex-grow bg-neutral-800/50" />
                    <span className="text-[10px] text-neutral-600 font-mono">{llmProvider}:{llmModel}</span>
                  </div>
                </div>
              </section>
            </div>
          </div>
        ) : activeView === 'extensions' ? (
          <ExtensionsView />
        ) : (
          <div className="flex-grow overflow-hidden flex flex-col">
            <HistoryView onSelectPid={setHistoryPid} onBack={() => setActiveView('dashboard')} />
          </div>
        )}
      </main>

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
      {isBatchModalOpen && (
        <BatchManagerModal
          isOpen={isBatchModalOpen}
          onClose={() => setIsBatchModalOpen(false)}
        />
      )}
    </div>
  );
}
