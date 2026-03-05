"use client";

import { useEffect, useState, useRef } from "react";
import ProcessMonitor from "@/components/Kernel/ProcessMonitor";
import TaskSchedulerVisualizer from "@/components/Kernel/TaskSchedulerVisualizer";
import CommandMonitor from "@/components/Monitoring/CommandMonitor";

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
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [kernelMetrics, setKernelMetrics] = useState<KernelMetrics | null>(null);
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
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "spawn", agent_name: `worker_${Math.floor(Math.random() * 1000)}` }));
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-6 font-sans antialiased selection:bg-blue-500/30">
      <header className="flex items-center justify-between border-b border-neutral-800 pb-6 mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
            AgentOS Kernel Dashboard
          </h1>
          <p className="text-neutral-400 mt-1">Autonomous Multi-Process Automation</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={handleSpawnAgent}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-sm font-semibold rounded-lg shadow-lg border border-blue-500/50 transition-all active:scale-95"
          >
            + Spawn process
          </button>
          <div className="flex items-center gap-3 bg-neutral-900/50 py-2 px-4 rounded-full border border-neutral-800">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className="text-sm text-neutral-300 font-medium tracking-wide font-mono">KERNEL ONLINE</span>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 backdrop-blur-xl shadow-2xl">
            <h2 className="text-xl font-semibold mb-4 text-neutral-200">Process Monitor (htop)</h2>
            <ProcessMonitor metrics={kernelMetrics} />
          </div>

          <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 backdrop-blur-xl shadow-2xl">
            <h2 className="text-xl font-semibold mb-4 text-neutral-200">Workflow & Task Pipelines</h2>
            <div className="h-48 flex items-center justify-center text-neutral-500 border border-dashed border-neutral-700/50 rounded-xl bg-neutral-950/50 font-mono">
              [Pipeline Memory Bus Graph]
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 backdrop-blur-xl shadow-2xl">
            <h2 className="text-xl font-semibold mb-4 text-neutral-200 flex items-center justify-between">
              <span>Task Scheduler</span>
              <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded border border-emerald-500/20 font-mono">SYNCED</span>
            </h2>
            <TaskSchedulerVisualizer metrics={kernelMetrics} />
          </div>

          <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 backdrop-blur-xl shadow-2xl h-full">
            <h2 className="text-xl font-semibold mb-4 text-neutral-200 flex items-center justify-between">
              <span>Tool Router log</span>
              <span className="text-xs bg-red-500/10 text-red-400 px-2 py-1 rounded border border-red-500/20 font-mono">SECURE</span>
            </h2>
            <CommandMonitor events={events} />
          </div>
        </div>
      </main>
    </div>
  );
}
