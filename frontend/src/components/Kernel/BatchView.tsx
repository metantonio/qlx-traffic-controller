"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Play, FolderTree, Database, Terminal, GitBranch, RefreshCw, Layers, Trash2, ChevronRight, Plus } from "lucide-react";

interface Workflow {
    id: string;
    name: string;
    variables: string[];
}

interface BatchJob {
    id: string;
    folder: string;
    workflow_id: string;
    total_files: number;
    processed_files: number;
    status: string;
}

export default function BatchView() {
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [activeBatches, setActiveBatches] = useState<BatchJob[]>([]);
    const [loading, setLoading] = useState(true);
    const [view, setView] = useState<'list' | 'create'>('list');

    // Create state
    const [selectedWorkflowId, setSelectedWorkflowId] = useState('');
    const [folderPath, setFolderPath] = useState('');
    const [variableValues, setVariableValues] = useState<Record<string, string>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchWorkflows = useCallback(async () => {
        try {
            const res = await fetch(`${apiUrl}/api/workflows`);
            if (res.ok) {
                setWorkflows(await res.json());
            }
        } catch (err) {
            console.error("Failed to fetch workflows:", err);
        }
    }, [apiUrl]);

    const fetchBatches = useCallback(async () => {
        try {
            const res = await fetch(`${apiUrl}/api/batch`);
            if (res.ok) {
                setActiveBatches(await res.json());
            }
        } catch (err) {
            console.error("Failed to fetch batches:", err);
        }
    }, [apiUrl]);

    const loadData = useCallback(async () => {
        setLoading(true);
        await Promise.all([fetchWorkflows(), fetchBatches()]);
        setLoading(false);
    }, [fetchWorkflows, fetchBatches]);

    useEffect(() => {
        loadData();
        const interval = setInterval(() => {
            fetchBatches();
        }, 3000);
        return () => clearInterval(interval);
    }, [loadData, fetchBatches]);

    const handleWorkflowChange = (wfId: string) => {
        setSelectedWorkflowId(wfId);
        const wf = workflows.find(w => w.id === wfId);
        if (wf) {
            const initialVars = wf.variables.reduce((acc, v) => {
                if (v !== 'file_path' && v !== 'filename') {
                    acc[v] = '';
                }
                return acc;
            }, {} as Record<string, string>);
            setVariableValues(initialVars);
        } else {
            setVariableValues({});
        }
    };

    const handleStartBatch = async () => {
        if (!folderPath || !selectedWorkflowId) return;
        setIsSubmitting(true);
        try {
            const res = await fetch(`${apiUrl}/api/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_path: folderPath,
                    workflow_id: selectedWorkflowId,
                    variables: variableValues
                })
            });
            if (res.ok) {
                setFolderPath('');
                setSelectedWorkflowId('');
                setVariableValues({});
                setView('list');
                fetchBatches();
            } else {
                const data = await res.json();
                alert(`Error: ${data.error}`);
            }
        } catch (err) {
            console.error("Failed to start batch:", err);
            alert("Network error starting batch.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleStopBatch = async (jobId: string) => {
        if (!confirm(`Are you sure you want to stop and delete batch job ${jobId}?`)) return;
        try {
            const res = await fetch(`${apiUrl}/api/batch/${jobId}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                fetchBatches();
            }
        } catch (err) {
            console.error("Failed to stop batch:", err);
        }
    };

    const handleRepeatBatch = (job: BatchJob) => {
        setFolderPath(job.folder);
        setSelectedWorkflowId(job.workflow_id);
        // job handles variables, but interface says it might be missing if it's an old job
        // @ts-expect-error - variables might be present in the status response but not in the type definition yet
        setVariableValues(job.variables || {});
        setView('create');
    };

    const selectedWfObj = workflows.find(w => w.id === selectedWorkflowId);

    return (
        <div className="flex-grow flex flex-col h-full bg-[#0a0a0b] p-10 overflow-y-auto custom-scrollbar">
            {/* Header */}
            <header className="mb-10 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-4 bg-purple-500/10 rounded-2xl border border-purple-500/20">
                        <Layers className="w-8 h-8 text-purple-400" />
                    </div>
                    <div>
                        <h2 className="text-4xl font-black tracking-tighter text-white">Batch Terminal</h2>
                        <p className="text-neutral-500 text-sm mt-1 font-medium tracking-wide font-mono uppercase">Mass Workflow Processor</p>
                    </div>
                </div>
                {view === 'list' && (
                    <button
                        onClick={() => setView('create')}
                        className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white text-sm font-bold rounded-2xl transition-all shadow-xl shadow-purple-500/20"
                    >
                        <Plus size={18} /> New Batch Job
                    </button>
                )}
            </header>

            <div className="flex-grow">
                {view === 'list' ? (
                    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        {/* Info Banner */}
                        <div className="bg-purple-600/5 border border-purple-500/10 p-8 rounded-[2.5rem] relative overflow-hidden group">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/5 blur-[80px] rounded-full -mr-16 -mt-16 group-hover:bg-purple-600/10 transition-colors" />
                            <div className="flex items-start gap-6 relative z-10">
                                <div className="p-4 bg-purple-500/10 rounded-2xl border border-purple-500/20">
                                    <Layers className="w-6 h-6 text-purple-500" />
                                </div>
                                <div className="max-w-3xl">
                                    <h3 className="text-xl font-black text-white tracking-tight mb-2 uppercase italic">Recursive Processing Layer</h3>
                                    <p className="text-sm text-neutral-400 leading-relaxed font-medium">
                                        Batch Jobs recursively execute <span className="text-purple-400 font-bold">Neural Pipelines</span> across entire directories. 
                                        Each file is processed in an isolated environment, preventing context drift while enabling massive throughput.
                                    </p>
                                    <div className="mt-4 flex gap-4 text-[10px] font-mono font-bold uppercase tracking-widest text-neutral-500">
                                        <span className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-purple-500" /> Isolation mode</span>
                                        <span className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-purple-500" /> Vector injection</span>
                                        <span className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-purple-500" /> Auto-scaling</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <h3 className="text-xs font-black text-neutral-500 uppercase tracking-[0.2em] ml-2 flex items-center gap-3">
                                <Database size={14} className="text-purple-500" /> Active Executions
                            </h3>

                            {loading ? (
                                <div className="py-20 text-center">
                                    <RefreshCw className="w-8 h-8 text-neutral-800 animate-spin mx-auto mb-4" />
                                    <p className="text-neutral-600 font-mono text-xs uppercase tracking-widest">Master Synchronizing...</p>
                                </div>
                            ) : activeBatches.length === 0 ? (
                                <div className="py-20 text-center border-2 border-dashed border-neutral-800 rounded-[2.5rem] text-neutral-600 bg-neutral-900/20">
                                    <Layers size={48} className="mx-auto mb-4 opacity-10" />
                                    <p className="text-lg font-bold text-neutral-400">No active batch registers</p>
                                    <p className="text-xs uppercase mt-2 tracking-widest opacity-50 font-mono">Select a folder and pipeline to begin orchestration</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {activeBatches.map(job => {
                                        const progress = job.total_files > 0 ? (job.processed_files / job.total_files) * 100 : 0;
                                        const isCompleted = job.status === 'completed';
                                        return (
                                            <div key={job.id} className="p-8 bg-neutral-900/40 border border-neutral-800/80 rounded-[2rem] hover:border-purple-500/50 hover:bg-neutral-900/60 transition-all duration-500">
                                                <div className="flex items-start justify-between mb-8">
                                                    <div className="min-w-0">
                                                        <div className="font-mono text-[9px] text-neutral-600 mb-2 font-bold tracking-tighter uppercase">ENV_JOB::{job.id.split('-')[0]}</div>
                                                        <h4 className="font-black text-white text-xl tracking-tighter flex items-center gap-2 truncate" title={job.folder}>
                                                            <FolderTree size={20} className="text-purple-500 shrink-0" />
                                                            {job.folder.split(/[\\/]/).pop() || "Root"}
                                                        </h4>
                                                    </div>
                                                    <div className="flex gap-2">
                                                        <button 
                                                            onClick={() => handleRepeatBatch(job)} 
                                                            className="p-2.5 text-neutral-600 hover:text-purple-400 hover:bg-purple-400/10 rounded-xl transition-all"
                                                            title="Repeat Batch"
                                                        >
                                                            <RefreshCw size={18} />
                                                        </button>
                                                        <button 
                                                            onClick={() => handleStopBatch(job.id)} 
                                                            className="p-2.5 text-neutral-600 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all"
                                                            title="Stop/Delete Batch"
                                                        >
                                                            <Trash2 size={18} />
                                                        </button>
                                                    </div>
                                                </div>

                                                <div className="space-y-6">
                                                    <div className="flex items-center justify-between">
                                                        <div className={`px-4 py-1.5 text-[9px] font-black uppercase rounded-full border tracking-widest ${
                                                            isCompleted ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                                                            job.status === 'stopped' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 
                                                            'bg-blue-500/20 text-blue-400 border-blue-500/30'
                                                        }`}>
                                                            {job.status}
                                                        </div>
                                                        <div className="text-[11px] font-mono font-bold text-neutral-500 tracking-tighter">
                                                            {job.processed_files} / {job.total_files} NODES
                                                        </div>
                                                    </div>

                                                    <div className="relative">
                                                        <div className="h-2 w-full bg-neutral-950 rounded-full overflow-hidden shadow-inner flex items-center px-0.5">
                                                            <div
                                                                className={`h-1 rounded-full transition-all duration-1000 ease-out ${
                                                                    isCompleted ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 
                                                                    job.status === 'stopped' ? 'bg-red-500' : 
                                                                    'bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.6)]'
                                                                }`}
                                                                style={{ width: `${progress}%` }}
                                                            />
                                                        </div>
                                                        <div className="absolute right-0 -top-6">
                                                          <span className="text-xs font-black font-mono text-neutral-400">{Math.round(progress)}%</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="max-w-4xl mx-auto space-y-10 animate-in slide-in-from-right-4 duration-500">
                        <header className="flex items-center justify-between">
                            <button onClick={() => setView('list')} className="group flex items-center gap-3 text-xs font-black text-neutral-500 uppercase tracking-widest hover:text-white transition-all">
                                <div className="p-2 bg-neutral-900 border border-neutral-800 rounded-lg group-hover:border-neutral-600 transition-all">
                                    <ChevronRight size={14} className="rotate-180" />
                                </div>
                                Back to Terminal
                            </button>
                            <span className="text-[10px] font-mono text-purple-500 font-black tracking-[0.3em] uppercase">Batch Initialization Sequence</span>
                        </header>

                        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-[2.5rem] p-10 space-y-10 shadow-2xl">
                             <div className="space-y-8">
                                <div className="space-y-3">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-2">
                                      <FolderTree size={16} className="text-purple-500" /> Target Directory Context
                                    </label>
                                    <input
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-[1.5rem] px-8 py-5 text-sm text-white focus:border-purple-500/50 outline-none transition-all placeholder:text-neutral-800 shadow-inner"
                                        placeholder="C:/Repos/enterprise-scale-logic"
                                        value={folderPath}
                                        onChange={(e) => setFolderPath(e.target.value)}
                                    />
                                    <p className="text-[10px] text-neutral-600 px-4 font-mono font-medium leading-relaxed">
                                      Specify the absolute absolute file-system path. The scheduler will iterate over all detectable assets in this scope.
                                    </p>
                                </div>

                                <div className="space-y-3">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-2">
                                      <GitBranch size={16} className="text-purple-500" /> Executive Neural Pipeline
                                    </label>
                                    <div className="relative group/sel">
                                      <select
                                          className="w-full bg-neutral-950 border border-neutral-800 rounded-[1.5rem] px-8 py-5 text-sm text-white focus:border-purple-500/50 outline-none appearance-none cursor-pointer shadow-inner"
                                          value={selectedWorkflowId}
                                          onChange={(e) => handleWorkflowChange(e.target.value)}
                                      >
                                          <option value="" disabled>-- Load Deployment Sequence --</option>
                                          {workflows.map(w => (
                                              <option key={w.id} value={w.id}>{w.name}</option>
                                          ))}
                                      </select>
                                      <div className="absolute right-8 top-1/2 -translate-y-1/2 pointer-events-none text-neutral-600">
                                        <ChevronRight size={18} className="rotate-90" />
                                      </div>
                                    </div>
                                </div>

                                {selectedWfObj && Object.keys(variableValues).length > 0 && (
                                    <div className="p-8 bg-neutral-950/50 border border-neutral-800/80 rounded-[2rem] space-y-6 animate-in slide-in-from-top-4 duration-500">
                                        <h4 className="text-[10px] text-neutral-500 uppercase font-black flex items-center gap-2">
                                          <Terminal size={14} className="text-purple-500" /> Local Vector Overrides
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                          {Object.keys(variableValues).map(v => (
                                              <div key={v} className="space-y-2">
                                                  <label className="text-[9px] text-neutral-500 font-mono font-bold uppercase ml-1 opacity-50">{v}</label>
                                                  <input
                                                      className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-5 py-3 text-sm text-white focus:border-purple-500/50 outline-none transition-all shadow-inner"
                                                      placeholder={`Set vector ${v}...`}
                                                      value={variableValues[v]}
                                                      onChange={e => setVariableValues({ ...variableValues, [v]: e.target.value })}
                                                  />
                                              </div>
                                          ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="pt-8 border-t border-neutral-800 flex gap-6">
                                <button
                                    onClick={() => setView('list')}
                                    className="flex-1 py-5 px-8 border border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-400 font-bold rounded-2xl transition-all uppercase text-[10px] tracking-widest"
                                >
                                    Cancel Session
                                </button>
                                <button
                                    onClick={handleStartBatch}
                                    disabled={!folderPath || !selectedWorkflowId || isSubmitting}
                                    className="flex-[2] py-5 px-8 bg-purple-600 hover:bg-purple-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white font-black rounded-2xl transition-all shadow-2xl shadow-purple-600/30 flex items-center justify-center gap-3 uppercase text-[10px] tracking-[0.2em] active:scale-95"
                                >
                                    {isSubmitting ? <RefreshCw size={20} className="animate-spin text-white/50" /> : <Play size={20} fill="currentColor" />}
                                    {isSubmitting ? "DISPATCHING NODES..." : "Initiate Full Batch Dispatch"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
