"use client";

import { useEffect, useState, useRef } from "react";
import ProcessMonitor from "@/components/Kernel/ProcessMonitor";
import TaskSchedulerVisualizer from "@/components/Kernel/TaskSchedulerVisualizer";
import ToolManager from "@/components/Kernel/ToolManager";
import CommandMonitor, { CommandEvent } from "@/components/Monitoring/CommandMonitor";

// Define a basic Kernel Metrics type
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
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Scaffold standard WebSockets connection to Control Tower
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

  const handleSpawnAgent = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && taskText.trim() !== "") {
      wsRef.current.send(JSON.stringify({
        action: "spawn",
        agent_name: `worker_${Math.floor(Math.random() * 1000)}`,
        task: taskText,
        allowed_tools: enabledTools
      }));
      setTaskText(""); // Clear after sending
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-neutral-100 p-8 font-sans antialiased selection:bg-blue-500/30 overflow-x-hidden">
      {/* Dynamic Background elements */}
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
            AgentOS Kernel
          </h1>
          <p className="text-neutral-500 text-sm mt-1 font-medium tracking-wide">Autonomous Neural-Process Orchestrator</p>
        </div>

        <div className="flex flex-col sm:flex-row items-end sm:items-center gap-4 w-full md:w-auto">
          {/* Unified Request Container */}
          <div className="group relative flex items-center bg-neutral-900/40 border border-neutral-800 rounded-2xl overflow-hidden focus-within:border-blue-500/50 focus-within:ring-4 ring-blue-500/10 w-full max-w-md transition-all backdrop-blur-md shadow-2xl">
            <div className="pl-4 text-neutral-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <input
              type="text"
              value={taskText}
              onChange={(e) => setTaskText(e.target.value)}
              placeholder="What should the kernel execute?"
              className="bg-transparent border-none text-base px-3 py-4 w-full focus:outline-none text-white placeholder:text-neutral-600 font-medium"
              onKeyDown={(e) => e.key === 'Enter' && handleSpawnAgent()}
            />
            <button
              onClick={handleSpawnAgent}
              disabled={!taskText.trim()}
              className={`mr-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all active:scale-95 flex items-center gap-2 ${!taskText.trim()
                  ? "bg-neutral-800 text-neutral-600 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(37,99,235,0.35)]"
                }`}
            >
              <span>Spawn</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          <div className="flex items-center gap-3 bg-neutral-900/80 py-2.5 px-5 rounded-2xl border border-neutral-800/80 backdrop-blur-md">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] text-neutral-400 font-black tracking-widest uppercase font-mono">Kernel.Online</span>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Main Column */}
        <div className="lg:col-span-8 space-y-8">
          <section className="bg-neutral-900/30 border border-white/5 rounded-[2rem] p-8 backdrop-blur-3xl shadow-2xl overflow-hidden relative group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500/20 to-transparent"></div>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-white tracking-tight">Active Processes</h2>
                <p className="text-neutral-500 text-xs font-medium uppercase tracking-widest mt-1">Real-time Kernel htop</p>
              </div>
              <div className="flex gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-neutral-700"></div>
                <div className="h-1.5 w-1.5 rounded-full bg-neutral-700"></div>
                <div className="h-1.5 w-1.5 rounded-full bg-neutral-700"></div>
              </div>
            </div>
            <ProcessMonitor metrics={kernelMetrics} />
          </section>

          <section className="bg-neutral-900/30 border border-white/5 rounded-[2rem] p-8 backdrop-blur-3xl shadow-2xl relative">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-bold text-white tracking-tight">Memory Bus Explorer</h2>
              <span className="text-[10px] font-bold py-1 px-3 rounded-full bg-neutral-800 text-neutral-400 border border-neutral-700 uppercase">Latency: 2ms</span>
            </div>
            <div className="h-64 flex flex-col items-center justify-center text-neutral-600 border border-dashed border-neutral-800 rounded-3xl bg-neutral-950/20 group hover:border-blue-500/20 transition-all">
              <svg className="w-12 h-12 mb-4 opacity-10 group-hover:opacity-20 group-hover:text-blue-500 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span className="font-mono text-sm tracking-tighter opacity-40 capitalize">Awaiting high-load activity to map bus...</span>
            </div>
          </section>
        </div>

        {/* Sidebar Column */}
        <div className="lg:col-span-4 space-y-8">
          <section className="bg-neutral-900/30 border border-white/5 rounded-[2rem] p-8 backdrop-blur-3xl shadow-2xl">
            <h2 className="text-2xl font-bold text-white tracking-tight mb-6">Capabilities</h2>
            <ToolManager onToolsChange={(tools) => setEnabledTools(tools)} />
          </section>

          <section className="bg-neutral-900/30 border border-white/5 rounded-[2rem] p-8 backdrop-blur-3xl shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white tracking-tight">Queue</h2>
              <span className="animate-pulse flex h-2 w-2 rounded-full bg-amber-500/50"></span>
            </div>
            <TaskSchedulerVisualizer metrics={kernelMetrics} />
          </section>

          <section className="bg-neutral-900/30 border border-white/5 rounded-[2rem] p-8 backdrop-blur-3xl shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white tracking-tight">Router Logs</h2>
              <div className="flex items-center gap-2 group cursor-help">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500"></span>
                <span className="text-[10px] font-black tracking-widest text-red-500/70 border-b border-red-500/10">SECURE</span>
              </div>
            </div>
            <CommandMonitor events={events} />
          </section>
        </div>
      </main>
    </div>
  );
}
