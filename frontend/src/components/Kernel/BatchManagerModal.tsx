"use client";

import React, { useState, useEffect, useCallback } from "react";
import { X, Play, FolderTree, Database, Terminal, GitBranch, RefreshCw, Layers } from "lucide-react";

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

interface BatchManagerModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function BatchManagerModal({ isOpen, onClose }: BatchManagerModalProps) {
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
        if (isOpen) {
            loadData();
            // Poll for batch updates every 2 seconds if modal is open
            const interval = setInterval(() => {
                fetchBatches();
            }, 2000);
            return () => clearInterval(interval);
        }
    }, [isOpen, loadData, fetchBatches]);

    const handleWorkflowChange = (wfId: string) => {
        setSelectedWorkflowId(wfId);
        const wf = workflows.find(w => w.id === wfId);
        if (wf) {
            // Initialize variable values, ignoring file_path and filename as they are handled by the backend
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

    if (!isOpen) return null;

    const selectedWfObj = workflows.find(w => w.id === selectedWorkflowId);

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" onClick={onClose}>
            <div className="bg-neutral-900 border border-neutral-800 w-full max-w-3xl rounded-[2.5rem] overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-300" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="p-8 border-b border-neutral-800 flex items-center justify-between bg-neutral-950/20">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-purple-500/10 rounded-2xl">
                            <Layers className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-white">Batch Terminal</h2>
                            <p className="text-[10px] text-neutral-500 uppercase tracking-widest font-mono">Mass Workflow Processor</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-8 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    {view === 'list' && (
                        <div className="mb-6 bg-purple-500/10 border border-purple-500/20 p-4 rounded-2xl flex gap-3 text-sm text-neutral-300">
                            <Layers className="text-purple-400 shrink-0 mt-0.5" size={18} />
                            <div>
                                <h4 className="font-bold text-purple-300 mb-1">How Batch Processing Works</h4>
                                <p className="mb-2 text-xs">
                                    A Batch Job allows you to run a <strong>Pipeline (Workflow)</strong> across multiple files automatically. Instead of processing 1000 files in a single chat—which causes agents to lose context—the batch orchestrator isolates each file.
                                </p>
                                <ul className="list-disc pl-4 space-y-1 text-[11px] text-neutral-400">
                                    <li>Create a Pipeline where the task uses <code className="text-purple-300 bg-purple-500/20 px-1 rounded">{"{{file_path}}"}</code> and <code className="text-purple-300 bg-purple-500/20 px-1 rounded">{"{{filename}}"}</code> variables.</li>
                                    <li>Start a new Batch Job here, pointing to an absolute directory path on your computer.</li>
                                    <li>The system will spawn an independent, isolated agent process for <strong>every single file</strong> in that folder.</li>
                                </ul>
                            </div>
                        </div>
                    )}
                    {view === 'list' ? (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest ml-1">Active Batch Jobs</h3>
                                <button
                                    onClick={() => setView('create')}
                                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold rounded-xl transition-all shadow-lg shadow-purple-500/10"
                                >
                                    <Play size={14} /> Start New Batch
                                </button>
                            </div>

                            {loading ? (
                                <div className="py-12 text-center text-neutral-600 animate-pulse font-mono text-[10px] uppercase tracking-[0.2em]">Syncing Batches...</div>
                            ) : activeBatches.length === 0 ? (
                                <div className="py-12 text-center border-2 border-dashed border-neutral-800 rounded-3xl text-neutral-600 bg-neutral-900/20">
                                    <div className="mb-2 opacity-20"><Database size={40} className="mx-auto" /></div>
                                    <p className="text-sm font-medium">No active batch jobs</p>
                                    <p className="text-[10px] uppercase mt-1 tracking-widest opacity-50 font-mono">Process entire directories with workflows</p>
                                </div>
                            ) : (
                                <div className="grid gap-4">
                                    {activeBatches.map(job => {
                                        const progress = job.total_files > 0 ? (job.processed_files / job.total_files) * 100 : 0;
                                        const isCompleted = job.status === 'completed';
                                        return (
                                            <div key={job.id} className="p-5 bg-neutral-800/20 border border-neutral-800/50 rounded-3xl transition-all duration-300 space-y-3">
                                                <div className="flex items-center justify-between">
                                                    <div>
                                                        <div className="font-mono text-[10px] text-neutral-500 mb-1">JOB ID: {job.id.split('-')[0]}...</div>
                                                        <div className="font-black text-neutral-200 text-sm tracking-tight flex items-center gap-2">
                                                            <FolderTree size={14} className="text-purple-400" />
                                                            <span className="truncate max-w-[300px]" title={job.folder}>{job.folder.split(/[\\/]/).pop()}</span>
                                                        </div>
                                                    </div>
                                                    <div className={`px-3 py-1 text-[10px] font-bold uppercase rounded-xl border ${isCompleted ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse'}`}>
                                                        {job.status}
                                                    </div>
                                                </div>

                                                <div>
                                                    <div className="flex justify-between text-[10px] font-mono text-neutral-400 mb-1">
                                                        <span>Processing {job.processed_files} / {job.total_files} files</span>
                                                        <span>{Math.round(progress)}%</span>
                                                    </div>
                                                    <div className="h-1.5 w-full bg-neutral-800 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full transition-all duration-500 ${isCompleted ? 'bg-emerald-500' : 'bg-blue-500'}`}
                                                            style={{ width: `${progress}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-8 animate-in slide-in-from-right-4 duration-300">
                            <div className="flex items-center gap-4 text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2 cursor-pointer hover:text-neutral-300 transition-colors" onClick={() => setView('list')}>
                                Batch Jobs <RefreshCw size={14} className="rotate-90" /> <span className="text-purple-400">Initialize Execution</span>
                            </div>

                            <div className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><FolderTree size={10} /> Target Directory Path</label>
                                    <input
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-purple-500/50 outline-none transition-all placeholder:text-neutral-800"
                                        placeholder="C:/path/to/my/folder"
                                        value={folderPath}
                                        onChange={e => setFolderPath(e.target.value)}
                                    />
                                    <p className="text-[10px] text-neutral-600 px-2 font-mono">Absolute path to the directory containing files to process</p>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><GitBranch size={10} /> Select Workflow</label>
                                    <select
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-purple-500/50 outline-none appearance-none cursor-pointer"
                                        value={selectedWorkflowId}
                                        onChange={e => handleWorkflowChange(e.target.value)}
                                    >
                                        <option value="" disabled>-- Choose a Pipeline --</option>
                                        {workflows.map(w => (
                                            <option key={w.id} value={w.id}>{w.name}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Dynamic Variables Input */}
                                {selectedWfObj && Object.keys(variableValues).length > 0 && (
                                    <div className="p-5 bg-neutral-950/50 border border-neutral-800/50 rounded-2xl space-y-4">
                                        <h4 className="text-[10px] text-neutral-500 uppercase font-black">Additional Pipeline Variables</h4>
                                        {Object.keys(variableValues).map(v => (
                                            <div key={v} className="space-y-2">
                                                <label className="text-[10px] text-neutral-400 font-mono ml-1"><Terminal size={10} className="inline mr-1" />{v}</label>
                                                <input
                                                    className="w-full bg-neutral-900 border border-neutral-800 rounded-xl px-4 py-2 text-sm text-white focus:border-purple-500/50 outline-none transition-all"
                                                    placeholder={`Value for ${v}...`}
                                                    value={variableValues[v]}
                                                    onChange={e => setVariableValues({ ...variableValues, [v]: e.target.value })}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-4 pt-4">
                                <button
                                    onClick={() => setView('list')}
                                    className="flex-1 py-4 px-6 border border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-400 font-bold rounded-2xl transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleStartBatch}
                                    disabled={!folderPath || !selectedWorkflowId || isSubmitting}
                                    className="flex-[2] py-4 px-6 bg-purple-600 hover:bg-purple-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white font-black rounded-2xl transition-all shadow-xl shadow-purple-500/20 flex items-center justify-center gap-2"
                                >
                                    {isSubmitting ? <RefreshCw size={18} className="animate-spin" /> : <Play size={18} fill="currentColor" />}
                                    {isSubmitting ? "Starting..." : "Dispatch Batch Job"}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
