"use client";

import React, { useState, useEffect, useCallback } from "react";
import { X, Plus, Trash2, GitBranch, Sparkles, Terminal, ChevronRight, Play, Edit2 } from "lucide-react";

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

interface WorkflowManagerModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function WorkflowManagerModal({ isOpen, onClose }: WorkflowManagerModalProps) {
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
        if (isOpen) fetchData();
    }, [isOpen, fetchData]);

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

        // Clean empty conditions before saving
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
            // Give it more time to ensure it arrives
            setTimeout(() => {
                ws.close();
                setIsRunning(false);
                onClose();
            }, 500);
        };

        ws.onerror = (err) => {
            console.error("WS Workflow Error:", err);
            setIsRunning(false);
            alert("Failed to connect to system kernel. Verify backend is running.");
        };
    };

    const handleDelete = async (id: string) => {
        try {
            await fetch(`${apiUrl}/api/workflows/${id}`, { method: 'DELETE' });
            fetchData();
        } catch (err) {
            console.error("Failed to delete workflow:", err);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" onClick={onClose}>
            <div className="bg-neutral-900 border border-neutral-800 w-full max-w-3xl rounded-[2.5rem] overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-300" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="p-8 border-b border-neutral-800 flex items-center justify-between bg-neutral-950/20">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-500/10 rounded-2xl">
                            <GitBranch className="w-6 h-6 text-blue-400" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-white">Neural Pipelines</h2>
                            <p className="text-[10px] text-neutral-500 uppercase tracking-widest font-mono">Sequential Agent Orchestrator</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-neutral-800 rounded-xl text-neutral-400 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-8 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    {view === 'list' ? (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest ml-1">Stored Sequences</h3>
                                <button
                                    onClick={() => { setView('create'); setIsEditing(false); setFormData({ id: '', name: '', description: '', steps: [] }); }}
                                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl transition-all shadow-lg shadow-blue-500/10"
                                >
                                    <Plus size={14} /> Design Workflow
                                </button>
                            </div>

                            {loading ? (
                                <div className="py-12 text-center text-neutral-600 animate-pulse font-mono text-[10px] uppercase tracking-[0.2em]">Retrieving Pipelines...</div>
                            ) : workflows.length === 0 ? (
                                <div className="py-12 text-center border-2 border-dashed border-neutral-800 rounded-3xl text-neutral-600 bg-neutral-900/20">
                                    <div className="mb-2 opacity-20"><GitBranch size={40} className="mx-auto" /></div>
                                    <p className="text-sm font-medium">No automated flows defined</p>
                                    <p className="text-[10px] uppercase mt-1 tracking-widest opacity-50 font-mono">Chain agents together for complex tasks</p>
                                </div>
                            ) : (
                                <div className="grid gap-4">
                                    {workflows.map(w => (
                                        <div key={w.id} className="group p-5 bg-neutral-800/20 border border-neutral-800/50 rounded-3xl flex items-center justify-between hover:border-neutral-700 hover:bg-neutral-800/40 transition-all duration-300">
                                            <div className="flex items-center gap-5">
                                                <div className="w-12 h-12 rounded-2xl bg-neutral-900 flex items-center justify-center text-neutral-400 group-hover:text-blue-400 transition-colors border border-neutral-800">
                                                    <GitBranch size={20} />
                                                </div>
                                                <div className="min-w-0">
                                                    <div className="font-black text-neutral-100 text-lg tracking-tight">{w.name}</div>
                                                    <div className="text-xs text-neutral-500 mt-0.5 font-medium line-clamp-1">{w.description}</div>
                                                    <div className="flex items-center gap-2 mt-2">
                                                        <span className="px-2 py-0.5 bg-neutral-900 border border-neutral-800 rounded-md text-[9px] font-mono text-neutral-500 uppercase tracking-wider">{w.steps.length} Steps</span>
                                                        <span className="px-2 py-0.5 bg-neutral-900 border border-neutral-800 rounded-md text-[9px] font-mono text-neutral-400 uppercase tracking-wider text-blue-400/80">{w.variables.length} Variables</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => {
                                                        setSelectedWorkflow(w);
                                                        setVariableValues(w.variables.reduce((acc, v) => ({ ...acc, [v]: '' }), {}));
                                                        setView('run');
                                                    }}
                                                    className="p-3 text-blue-400 hover:bg-blue-400/10 rounded-2xl transition-all"
                                                >
                                                    <Play size={18} />
                                                </button>
                                                <button
                                                    onClick={() => handleEdit(w)}
                                                    className="p-3 text-neutral-700 hover:text-blue-400 hover:bg-blue-400/10 rounded-2xl transition-all"
                                                >
                                                    <Edit2 size={18} />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(w.id)}
                                                    className="p-3 text-neutral-700 hover:text-red-400 hover:bg-red-400/10 rounded-2xl transition-all opacity-0 group-hover:opacity-100"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : view === 'run' && selectedWorkflow ? (
                        <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-300">
                            <div className="flex items-center gap-4 text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2 cursor-pointer hover:text-neutral-300 transition-colors" onClick={() => setView('list')}>
                                Pipeline Registry <ChevronRight size={14} /> <span className="text-blue-400">Execute Flow: {selectedWorkflow.name}</span>
                            </div>

                            <div className="p-6 bg-blue-500/5 border border-blue-500/10 rounded-3xl">
                                <p className="text-sm text-neutral-400 leading-relaxed font-medium">
                                    {selectedWorkflow.description}
                                </p>
                            </div>

                            <div className="space-y-6">
                                <h4 className="text-[10px] text-neutral-500 uppercase font-black ml-1">Input Parameters</h4>
                                <div className="grid gap-4">
                                    {selectedWorkflow.variables.length === 0 ? (
                                        <div className="py-4 text-center text-neutral-600 text-[10px] uppercase font-mono tracking-widest bg-neutral-950/20 rounded-2xl border border-neutral-900">
                                            No inputs required for this sequence
                                        </div>
                                    ) : selectedWorkflow.variables.map(v => (
                                        <div key={v} className="space-y-2">
                                            <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><Terminal size={10} /> {v}</label>
                                            <input
                                                className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800"
                                                placeholder={`Enter value for ${v}...`}
                                                value={variableValues[v] || ''}
                                                onChange={e => setVariableValues({ ...variableValues, [v]: e.target.value })}
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h4 className="text-[10px] text-neutral-500 uppercase font-black ml-1">Pipeline Preview</h4>
                                <div className="space-y-2 opacity-50">
                                    {selectedWorkflow.steps.map((s, i) => (
                                        <div key={i} className="flex items-center gap-3 p-3 bg-neutral-950/50 rounded-xl border border-neutral-800/50 text-[11px] text-neutral-500">
                                            <span className="font-mono text-blue-500 font-bold">{i + 1}</span>
                                            <span className="font-black uppercase">{s.agent_id}</span>
                                            <span className="truncate">{s.task_template}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="flex gap-4 pt-4">
                                <button
                                    onClick={() => setView('list')}
                                    className="flex-1 py-4 px-6 border border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-400 font-bold rounded-2xl transition-all"
                                >
                                    Back
                                </button>
                                <button
                                    onClick={handleRun}
                                    disabled={isRunning}
                                    className={`flex-grow py-4 rounded-2xl font-black uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 ${isRunning
                                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 cursor-wait"
                                        : "bg-blue-600 hover:bg-blue-500 text-white shadow-xl shadow-blue-600/20 active:scale-95"
                                        }`}
                                >
                                    <Play size={18} fill="currentColor" className={isRunning ? "animate-pulse" : ""} />
                                    {isRunning ? "Activating Pipeline..." : "Launch Sequential Agents"}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-8 animate-in slide-in-from-right-4 duration-300">
                            <div className="flex items-center gap-4 text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2 cursor-pointer hover:text-neutral-300 transition-colors" onClick={() => { setView('list'); setIsEditing(false); }}>
                                Pipeline Registry <ChevronRight size={14} /> <span className="text-blue-400">{isEditing ? 'Sequence Architect' : 'Workflow Designer'}</span>
                            </div>

                            <div className="grid grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><Terminal size={10} /> Sequence ID</label>
                                    <input
                                        disabled={isEditing}
                                        className={`w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800 ${isEditing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        placeholder="refactor-and-verify"
                                        value={formData.id}
                                        onChange={e => setFormData({ ...formData, id: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] text-neutral-500 uppercase font-black ml-1 flex items-center gap-1.5"><Sparkles size={10} /> Pipeline Name</label>
                                    <input
                                        className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-purple-500/50 outline-none transition-all placeholder:text-neutral-800"
                                        placeholder="Refactor & Verify Cycle"
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] text-neutral-500 uppercase font-black ml-1">Executive Summary</label>
                                <input
                                    className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl px-5 py-3 text-sm text-white focus:border-blue-500/50 outline-none transition-all placeholder:text-neutral-800"
                                    placeholder="Chain of agents to refactor code and run tests..."
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                />
                            </div>

                            {/* Advanced Features Help */}
                            <div className="bg-blue-500/10 border border-blue-500/20 p-5 rounded-2xl flex gap-4 text-sm text-neutral-300">
                                <GitBranch className="text-blue-400 shrink-0 mt-0.5" size={18} />
                                <div>
                                    <h4 className="font-bold text-blue-300 mb-1">Advanced Conditional Routing (Manual)</h4>
                                    <p className="mb-3 text-xs text-neutral-400 leading-relaxed">
                                        Pipelines can dynamically choose which agent handles a step, or skip steps entirely based on the decisions made by previous agents in the sequence.
                                    </p>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px] text-neutral-400">
                                        <div className="bg-neutral-900/50 p-3 rounded-xl border border-neutral-800">
                                            <strong className="text-blue-300 block mb-1">1. The Router Agent</strong>
                                            Instruct an agent to analyze data and define a variable using its tools (e.g. <i>&quot;If it&apos;s a PDF, set `next_agent` to `pdf_agent`&quot;</i>).
                                        </div>
                                        <div className="bg-neutral-900/50 p-3 rounded-xl border border-neutral-800">
                                            <strong className="text-blue-300 block mb-1">2. Dynamic Assignment</strong>
                                            Instead of selecting a specific Persona ID for the next step, type the variable name: <code className="text-blue-300 bg-blue-500/20 px-1 rounded">{"{{next_agent}}"}</code>.
                                        </div>
                                        <div className="bg-neutral-900/50 p-3 rounded-xl border border-neutral-800 md:col-span-2 mt-2">
                                            <strong className="text-yellow-400 block mb-1">3. Step Conditions</strong>
                                            Use the <b>Execute Condition</b> field to define when a step should run. If an agent previously set `file_type` to `image`, a step with condition <code className="text-yellow-400 bg-yellow-500/10 px-1 rounded">{"{{file_type}} == pdf"}</code> will be automatically skipped.
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Steps Editor */}
                            <div className="space-y-6">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-[10px] text-neutral-500 uppercase font-black ml-1">Sequence Orchestration</h4>
                                    <button
                                        onClick={handleAddStep}
                                        className="text-[10px] text-blue-400 font-bold flex items-center gap-1 hover:text-blue-300 transition-colors"
                                    >
                                        <Plus size={12} /> Add Agent Step
                                    </button>
                                </div>

                                <div className="space-y-4">
                                    {formData.steps.map((step, index) => (
                                        <div key={index} className="p-6 bg-neutral-950 border border-neutral-800 rounded-3xl relative group/step shadow-inner">
                                            <div className="absolute -left-3 top-6 w-6 h-6 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center text-[10px] font-bold text-neutral-400 shadow-xl">
                                                {index + 1}
                                            </div>
                                            <button
                                                onClick={() => handleRemoveStep(index)}
                                                className="absolute -right-2 -top-2 p-2 bg-red-400/10 text-red-400 rounded-xl border border-red-400/20 opacity-0 group-hover/step:opacity-100 transition-all hover:bg-red-400/20"
                                            >
                                                <Trash2 size={12} />
                                            </button>

                                            <div className="grid gap-4">
                                                <div className="space-y-2">
                                                    <label className="text-[9px] text-neutral-600 uppercase font-black ml-1 flex justify-between">
                                                        <span>Designated Persona ID</span>
                                                        <span className="text-[8px] opacity-40 lowercase">Type {"{{var}}"} for dynamic routing</span>
                                                    </label>
                                                    <input
                                                        type="text"
                                                        list="agent-suggestions"
                                                        className="w-full bg-neutral-900 border border-neutral-800/50 rounded-xl px-4 py-2 text-sm text-white focus:border-blue-500/50 outline-none"
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
                                                <div className="space-y-2">
                                                    <label className="text-[9px] text-neutral-600 uppercase font-black ml-1 flex justify-between">
                                                        <span>Execute Condition (Optional)</span>
                                                        <span className="text-[8px] opacity-40 lowercase">e.g. {"{{file_type}} == pdf"}</span>
                                                    </label>
                                                    <input
                                                        type="text"
                                                        className="w-full bg-neutral-900 border border-neutral-800/50 rounded-xl px-4 py-2 text-sm text-white focus:border-yellow-500/50 outline-none placeholder:text-neutral-700"
                                                        placeholder="Leave blank to always execute..."
                                                        value={step.condition || ''}
                                                        onChange={e => handleStepChange(index, 'condition', e.target.value)}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="text-[9px] text-neutral-600 uppercase font-black ml-1 flex items-center justify-between">
                                                        <span>Instruction Template</span>
                                                        <span className="text-[8px] opacity-40 lowercase">Use {"{{var}}"} for placeholders</span>
                                                    </label>
                                                    <textarea
                                                        className="w-full bg-neutral-900 border border-neutral-800/50 rounded-xl px-4 py-3 text-sm text-white focus:border-blue-500/50 outline-none min-h-[80px] font-medium leading-relaxed"
                                                        placeholder="Review the code in {{folder}}..."
                                                        value={step.task_template}
                                                        onChange={e => handleStepChange(index, 'task_template', e.target.value)}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    ))}

                                    {formData.steps.length === 0 && (
                                        <div className="py-8 text-center bg-neutral-950/20 border border-dashed border-neutral-800 rounded-3xl text-neutral-600 text-[10px] uppercase tracking-widest font-mono">
                                            No steps defined in pipeline
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex gap-4 pt-4">
                                <button
                                    onClick={() => setView('list')}
                                    className="flex-1 py-4 px-6 border border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-neutral-400 font-bold rounded-2xl transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={!formData.id || !formData.name || formData.steps.length === 0}
                                    className="flex-[2] py-4 px-6 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white font-black rounded-2xl transition-all shadow-xl shadow-blue-500/20 flex items-center justify-center gap-2"
                                >
                                    <Sparkles size={18} />
                                    {isEditing ? 'Update Pipeline' : 'Finalize Pipeline'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-4 border-t border-neutral-800 bg-neutral-950/50 flex justify-center">
                    <p className="text-[9px] text-neutral-600 uppercase tracking-[0.2em] font-mono">Neural Pipeline Interface // Automation Layer Active</p>
                </div>
            </div>
        </div>
    );
}
