"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Plus, Trash2, GitBranch, Sparkles, Terminal, ChevronRight, Play, Edit2 } from "lucide-react";

interface WorkflowStep {
    agent_id: string;
    task_template: string;
    condition?: string;
}

interface Workflow {
    id: string;
    name: string;
    description: string;
    steps: WorkflowStep[];
    variables: string[];
}

interface CustomAgent {
    id: string;
    name: string;
}

interface WorkflowViewProps {
    onRunStarted?: (workflowId: string) => void;
}

export default function WorkflowView({ onRunStarted }: WorkflowViewProps) {
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [agents, setAgents] = useState<CustomAgent[]>([]);
    const [loading, setLoading] = useState(true);
    const [view, setView] = useState<'list' | 'create' | 'run'>('list');
    const [isEditing, setIsEditing] = useState(false);

    // Run state
    const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
    const [variableValues, setVariableValues] = useState<Record<string, string>>({});

    // Create state
    const [formData, setFormData] = useState({
        id: '',
        name: '',
        description: '',
        steps: [] as WorkflowStep[]
    });

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const urls = [
                `${apiUrl}/api/workflows`,
                `${apiUrl}/api/agents/custom`
            ];

            const [wfRes, agRes] = await Promise.all(urls.map(url =>
                fetch(url).catch(e => {
                    console.error(`Network error reaching ${url}:`, e);
                    throw new Error(`Failed to reach ${url}`);
                })
            ));

            if (!wfRes.ok) throw new Error(`Workflows API error: ${wfRes.status}`);
            if (!agRes.ok) throw new Error(`Agents API error: ${agRes.status}`);

            setWorkflows(await wfRes.json());
            setAgents(await agRes.json());
        } catch (err) {
            console.error("Workflow Pipeline Sync Failure:", err);
        } finally {
            setLoading(false);
        }
    }, [apiUrl]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleAddStep = () => {
        setFormData(prev => ({
            ...prev,
            steps: [...prev.steps, { agent_id: agents[0]?.id || 'kernel_agent', task_template: '' }]
        }));
    };

    const handleRemoveStep = (index: number) => {
        setFormData(prev => ({
            ...prev,
            steps: prev.steps.filter((_, i) => i !== index)
        }));
    };

    const handleStepChange = (index: number, field: keyof WorkflowStep, value: string) => {
        setFormData(prev => {
            const newSteps = [...prev.steps];
            newSteps[index] = { ...newSteps[index], [field]: value };
            return { ...prev, steps: newSteps };
        });
    };

    const extractVariables = (steps: WorkflowStep[]) => {
        const vars = new Set<string>();
        const regex = /\{\{(\w+)\}\}/g;
        steps.forEach(s => {
            let match;
            while ((match = regex.exec(s.task_template)) !== null) {
                vars.add(match[1]);
            }
        });
        return Array.from(vars);
    };

    const handleSave = async () => {
        if (!formData.id || !formData.name) return;

        const cleanedSteps = formData.steps.map(s => ({
            ...s,
            condition: s.condition?.trim() === '' ? undefined : s.condition
        }));

        const workflow: Workflow = {
            ...formData,
            steps: cleanedSteps,
            variables: extractVariables(cleanedSteps)
        };

        try {
            const method = isEditing ? 'PUT' : 'POST';
            const url = isEditing ? `${apiUrl}/api/workflows/${formData.id}` : `${apiUrl}/api/workflows`;

            await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(workflow)
            });
            setFormData({ id: '', name: '', description: '', steps: [] });
            setIsEditing(false);
            setView('list');
            fetchData();
        } catch (err) {
            console.error("Failed to save workflow:", err);
        }
    };

    const handleEdit = (wf: Workflow) => {
        setFormData({
            id: wf.id,
            name: wf.name,
            description: wf.description,
            steps: wf.steps
        });
        setIsEditing(true);
        setView('create');
    };

    const [isRunning, setIsRunning] = useState(false);

    const handleRun = () => {
        if (!selectedWorkflow) return;

        setIsRunning(true);
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/ws";
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("Sending spawn_workflow for:", selectedWorkflow.id);
            ws.send(JSON.stringify({
                action: "spawn_workflow",
                workflow_id: selectedWorkflow.id,
                variables: variableValues
            }));
            
            if (onRunStarted) onRunStarted(selectedWorkflow.id);

            setTimeout(() => {
                ws.close();
                setIsRunning(false);
                setView('list');
            }, 500);
        };

        ws.onerror = (err) => {
            console.error("WS Workflow Error:", err);
            setIsRunning(false);
            alert("Failed to connect to system kernel. Verify backend is running.");
        };
    };

    const handleDelete = async (id: string) => {
        if (!confirm(`Are you sure you want to delete workflow ${id}?`)) return;
        try {
            await fetch(`${apiUrl}/api/workflows/${id}`, { method: 'DELETE' });
            fetchData();
        } catch (err) {
            console.error("Failed to delete workflow:", err);
        }
    };

    return (
        <div className="flex-grow flex flex-col h-full bg-[#0a0a0b] p-10 overflow-y-auto custom-scrollbar">
            {/* Header */}
            <header className="mb-10 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20">
                        <GitBranch className="w-8 h-8 text-blue-400" />
                    </div>
                    <div>
                        <h2 className="text-4xl font-black tracking-tighter text-white">Neural Pipelines</h2>
                        <p className="text-neutral-500 text-sm mt-1 font-medium tracking-wide font-mono uppercase">Sequential Agent Orchestrator</p>
                    </div>
                </div>
                {view === 'list' && (
                    <button
                        onClick={() => { setView('create'); setIsEditing(false); setFormData({ id: '', name: '', description: '', steps: [] }); }}
                        className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold rounded-2xl transition-all shadow-xl shadow-blue-500/20"
                    >
                        <Plus size={18} /> Design Workflow
                    </button>
                )}
            </header>

            <div className="flex-grow">
                {view === 'list' ? (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        {loading ? (
                            <div className="py-20 text-center">
                                <div className="inline-block p-4 bg-neutral-900 border border-neutral-800 rounded-2xl mb-4 animate-bounce">
                                    <GitBranch className="w-8 h-8 text-neutral-600" />
                                </div>
                                <p className="text-neutral-600 font-mono text-xs uppercase tracking-widest">Retrieving Pipelines...</p>
                            </div>
                        ) : workflows.length === 0 ? (
                            <div className="py-20 text-center border-2 border-dashed border-neutral-800 rounded-[2.5rem] text-neutral-600 bg-neutral-900/20">
                                <GitBranch size={48} className="mx-auto mb-4 opacity-20" />
                                <p className="text-lg font-bold text-neutral-400">No automated flows defined</p>
                                <p className="text-xs uppercase mt-2 tracking-widest opacity-50 font-mono">Chain agents together for complex tasks</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6">
                                {workflows.map(w => (
                                    <div key={w.id} className="group p-8 bg-neutral-900/40 border border-neutral-800/80 rounded-[2rem] hover:border-blue-500/50 hover:bg-neutral-900/60 transition-all duration-500 relative overflow-hidden">
                                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/5 blur-[60px] rounded-full -mr-16 -mt-16 group-hover:bg-blue-600/10 transition-colors" />
                                        
                                        <div className="flex flex-col h-full relative z-10">
                                            <div className="flex items-start justify-between mb-6">
                                                <div className="w-14 h-14 rounded-2xl bg-neutral-950 flex items-center justify-center border border-neutral-800 group-hover:border-blue-500/30 transition-colors">
                                                    <GitBranch size={24} className="text-neutral-400 group-hover:text-blue-400 transition-colors" />
                                                </div>
                                                <div className="flex gap-2">
                                                    <button onClick={() => handleEdit(w)} className="p-2.5 text-neutral-500 hover:text-white hover:bg-neutral-800 rounded-xl transition-all">
                                                        <Edit2 size={16} />
                                                    </button>
                                                    <button onClick={() => handleDelete(w.id)} className="p-2.5 text-neutral-500 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all">
                                                        <Trash2 size={16} />
                                                    </button>
                                                </div>
                                            </div>

                                            <h3 className="text-2xl font-black text-white tracking-tight mb-2 group-hover:text-blue-400 transition-colors">{w.name}</h3>
                                            <p className="text-sm text-neutral-500 line-clamp-2 mb-6 font-medium leading-relaxed">{w.description}</p>
                                            
                                            <div className="mt-auto pt-6 border-t border-neutral-800/50 flex items-center justify-between">
                                                <div className="flex gap-2">
                                                    <span className="px-3 py-1 bg-neutral-950 border border-neutral-800 rounded-xl text-[10px] font-mono font-bold text-neutral-500 uppercase tracking-wider">{w.steps.length} Steps</span>
                                                    {w.variables.length > 0 && (
                                                        <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-xl text-[10px] font-mono font-bold text-blue-400 uppercase tracking-wider">{w.variables.length} Vars</span>
                                                    )}
                                                </div>
                                                <button
                                                    onClick={() => {
                                                        setSelectedWorkflow(w);
                                                        setVariableValues(w.variables.reduce((acc, v) => ({ ...acc, [v]: '' }), {}));
                                                        setView('run');
                                                    }}
                                                    className="flex items-center gap-2 px-5 py-2.5 bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-600/20 rounded-xl transition-all font-black text-[10px] uppercase tracking-widest active:scale-95"
                                                >
                                                    <Play size={14} fill="currentColor" /> Execute
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ) : view === 'run' && selectedWorkflow ? (
                    <div className="max-w-4xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-500">
                        <header className="flex items-center justify-between">
                            <button onClick={() => setView('list')} className="group flex items-center gap-3 text-xs font-black text-neutral-500 uppercase tracking-widest hover:text-white transition-all">
                                <div className="p-2 bg-neutral-900 border border-neutral-800 rounded-lg group-hover:border-neutral-600 transition-all">
                                    <ChevronRight size={14} className="rotate-180" />
                                </div>
                                Back to Registry
                            </button>
                            <span className="text-[10px] font-mono text-blue-500 font-black tracking-[0.3em] uppercase">Pipeline Execution Mode</span>
                        </header>

                        <div className="p-10 bg-neutral-900/40 border border-neutral-800/80 rounded-[2.5rem] relative overflow-hidden">
                             <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/5 blur-[100px] rounded-full -mr-32 -mt-32" />
                             <div className="relative z-10">
                                <h3 className="text-4xl font-black text-white tracking-tighter mb-4 italic uppercase">{selectedWorkflow.name}</h3>
                                <p className="text-lg text-neutral-400 leading-relaxed font-medium max-w-2xl">{selectedWorkflow.description}</p>
                             </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-[2rem] p-8">
                                <h4 className="text-xs font-black text-neutral-500 uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
                                    <Terminal size={14} className="text-blue-500" /> Input Parameters
                                </h4>
                                <div className="space-y-6">
                                    {selectedWorkflow.variables.length === 0 ? (
                                        <div className="py-12 text-center text-neutral-600 text-[10px] uppercase font-mono tracking-widest bg-neutral-950/20 rounded-2xl border border-neutral-800">
                                            No inputs required for this sequence
                                        </div>
                                    ) : selectedWorkflow.variables.map(v => (
                                        <div key={v} className="space-y-3">
                                            <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-2">
                                              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> {v}
                                            </label>
                                            <input
                                                className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-6 py-4 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800 shadow-inner"
                                                placeholder={`Enter value for ${v}...`}
                                                value={variableValues[v] || ''}
                                                onChange={e => setVariableValues({ ...variableValues, [v]: e.target.value })}
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-[2rem] p-8">
                                <h4 className="text-xs font-black text-neutral-500 uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
                                    <GitBranch size={14} className="text-blue-500" /> Pipeline Topology
                                </h4>
                                <div className="space-y-3">
                                    {selectedWorkflow.steps.map((s, i) => (
                                        <div key={i} className="flex items-center gap-4 p-4 bg-neutral-950/50 rounded-2xl border border-neutral-800/50 hover:border-neutral-700 transition-all">
                                            <div className="w-8 h-8 rounded-xl bg-neutral-900 border border-neutral-800 flex items-center justify-center text-[10px] font-mono font-black text-blue-500">
                                                {i + 1}
                                            </div>
                                            <div className="min-w-0 flex-grow">
                                                <div className="text-[10px] font-black uppercase text-neutral-400 mb-0.5">{s.agent_id}</div>
                                                <div className="text-xs text-neutral-500 truncate font-medium">{s.task_template}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="pt-8 border-t border-neutral-800/50 flex gap-6">
                            <button
                                onClick={() => setView('create')}
                                className="flex-grow py-5 rounded-2xl font-black uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 bg-blue-600 hover:bg-blue-500 text-white shadow-2xl shadow-blue-600/30 active:scale-95 disabled:opacity-50"
                                disabled={isRunning}
                                onClick={handleRun}
                            >
                                <Play size={20} fill="currentColor" className={isRunning ? "animate-pulse" : ""} />
                                {isRunning ? "Activating Neural Chain..." : "Launch Sequential Agents"}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="max-w-5xl mx-auto space-y-10 animate-in slide-in-from-right-4 duration-500">
                        <header className="flex items-center justify-between">
                            <button onClick={() => { setView('list'); setIsEditing(false); }} className="group flex items-center gap-3 text-xs font-black text-neutral-500 uppercase tracking-widest hover:text-white transition-all">
                                <div className="p-2 bg-neutral-900 border border-neutral-800 rounded-lg group-hover:border-neutral-600 transition-all">
                                    <ChevronRight size={14} className="rotate-180" />
                                </div>
                                Back to Registry
                            </button>
                            <span className="text-[10px] font-mono text-blue-500 font-black tracking-[0.3em] uppercase">{isEditing ? 'Architecture Redesign' : 'New Sequence Design'}</span>
                        </header>

                        <div className="bg-neutral-900/60 border border-neutral-800/80 rounded-[2.5rem] p-10 space-y-8">
                             <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-3">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-2">
                                      <Terminal size={14} className="text-blue-500" /> Pipeline Identifier
                                    </label>
                                    <input
                                        disabled={isEditing}
                                        className={`w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-6 py-4 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800 ${isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        placeholder="refactor-and-verify"
                                        value={formData.id}
                                        onChange={e => setFormData({ ...formData, id: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-3">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-2">
                                      <Sparkles size={14} className="text-blue-500" /> Human-Readable Name
                                    </label>
                                    <input
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-6 py-4 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800"
                                        placeholder="Refactor & Verify Cycle"
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-3">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1">Mission Executive Summary</label>
                                <input
                                    className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-6 py-4 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800"
                                    placeholder="Chain of agents to refactor code and run tests..."
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>
                        </div>

                         <div className="space-y-6">
                            <div className="flex items-center justify-between px-2">
                                <h4 className="text-xs font-black text-neutral-500 uppercase tracking-[0.2em] flex items-center gap-3">
                                    <Layers className="text-blue-500" size={16} /> Sequence Orchestration
                                </h4>
                                <button
                                    onClick={handleAddStep}
                                    className="px-4 py-2 bg-blue-500/10 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-500/20 rounded-xl transition-all font-black text-[10px] uppercase tracking-widest flex items-center gap-2"
                                >
                                    <Plus size={14} /> Add Agent Step
                                </button>
                            </div>

                            <div className="space-y-6">
                                {formData.steps.map((step, index) => (
                                    <div key={index} className="p-8 bg-neutral-900 border border-neutral-800 rounded-[2rem] relative group/step hover:border-neutral-700 transition-all shadow-xl">
                                        <div className="absolute -left-4 top-8 w-10 h-10 rounded-2xl bg-neutral-950 border border-neutral-800 flex items-center justify-center text-xs font-mono font-black text-blue-500 shadow-2xl">
                                            {index + 1}
                                        </div>
                                        <button
                                            onClick={() => handleRemoveStep(index)}
                                            className="absolute -right-3 -top-3 p-3 bg-red-500/10 text-red-500 rounded-2xl border border-red-500/20 opacity-0 group-hover/step:opacity-100 transition-all hover:bg-red-500/20 shadow-xl"
                                        >
                                            <Trash2 size={16} />
                                        </button>

                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                            <div className="space-y-6">
                                                <div className="space-y-3">
                                                    <label className="text-[10px] text-neutral-600 uppercase font-black ml-1 flex justify-between">
                                                        <span>Designated Persona ID</span>
                                                        <span className="text-[8px] opacity-40 lowercase">Type {"{{var}}"} for dynamic routing</span>
                                                    </label>
                                                    <input
                                                        type="text"
                                                        list="agent-suggestions"
                                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-6 py-3.5 text-sm text-white focus:border-blue-500/50 outline-none"
                                                        placeholder="kernel_agent OR {{next_agent}}"
                                                        value={step.agent_id}
                                                        onChange={e => handleStepChange(index, 'agent_id', e.target.value)}
                                                    />
                                                    <datalist id="agent-suggestions">
                                                        <option value="kernel_agent">Kernel Default</option>
                                                        {agents.map(a => (
                                                            <option key={a.id} value={a.id}>{a.name}</option>
                                                        ))}
                                                    </datalist>
                                                </div>
                                                <div className="space-y-3">
                                                    <label className="text-[10px] text-neutral-600 uppercase font-black ml-1 flex justify-between">
                                                        <span>Execute Condition (Optional)</span>
                                                        <span className="text-[8px] opacity-40 lowercase">e.g. {"{{file_type}} == pdf"}</span>
                                                    </label>
                                                    <input
                                                        type="text"
                                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-6 py-3.5 text-sm text-white focus:border-blue-500/50 outline-none placeholder:text-neutral-800"
                                                        placeholder="Always active if empty..."
                                                        value={step.condition || ''}
                                                        onChange={e => handleStepChange(index, 'condition', e.target.value)}
                                                    />
                                                </div>
                                            </div>
                                            <div className="space-y-3">
                                                <label className="text-[10px] text-neutral-600 uppercase font-black ml-1 flex items-center justify-between">
                                                    <span>Mission Instruction Template</span>
                                                    <span className="text-[8px] opacity-40 lowercase">Use {"{{var}}"} for injections</span>
                                                </label>
                                                <textarea
                                                    className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-6 py-4 text-sm text-white focus:border-blue-500/50 outline-none min-h-[148px] font-medium leading-relaxed resize-none shadow-inner"
                                                    placeholder="Review the code in {{folder}} and provide a detailed summary..."
                                                    value={step.task_template}
                                                    onChange={e => handleStepChange(index, 'task_template', e.target.value)}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                {formData.steps.length === 0 && (
                                    <div className="py-20 text-center bg-neutral-900/20 border-2 border-dashed border-neutral-800 rounded-[2.5rem] text-neutral-600 text-xs uppercase tracking-[0.2em] font-mono">
                                        No architecture steps defined
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="pt-10 border-t border-neutral-800/50 flex gap-6">
                             <button
                                onClick={() => setView('list')}
                                className="flex-1 py-5 px-8 border border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-400 font-bold rounded-2xl transition-all uppercase text-xs tracking-widest"
                            >
                                Discard Design
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={!formData.id || !formData.name || formData.steps.length === 0}
                                className="flex-[2] py-5 px-8 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white font-black rounded-2xl transition-all shadow-2xl shadow-blue-500/30 flex items-center justify-center gap-3 uppercase text-xs tracking-[0.2em] active:scale-95"
                            >
                                <Sparkles size={20} />
                                {isEditing ? 'Commit Architecture Upgrades' : 'Finalize Sequence Design'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

import { Layers } from "lucide-react";
