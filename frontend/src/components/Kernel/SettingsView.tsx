"use client";

import { useEffect, useState, useCallback } from "react";
import { Save, Settings as SettingsIcon, Shield, Zap, RefreshCw, ChevronDown, Cpu, Globe } from "lucide-react";

interface SystemSettings {
  VISION_MODEL: string;
}

interface AllowedDirectory {
  id: number;
  path: string;
  description: string;
}

interface LLMProviderInfo {
  provider: string;
  name: string;
  models: string[];
  configured: boolean;
  error?: string;
}

export default function SettingsView() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  
  // Directory management
  const [directories, setDirectories] = useState<AllowedDirectory[]>([]);
  const [newDirPath, setNewDirPath] = useState("");
  const [newDirDesc, setNewDirDesc] = useState("");

  const fetchSettings = useCallback(async () => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/settings`);
    if (!response.ok) throw new Error("Failed to fetch settings");
    const data = await response.json();
    setSettings(data);
  }, []);

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/llm/models`);
      const data = await res.json();
      setProviders(data);
    } catch (err) {
      console.error("Failed to fetch LLM models:", err);
    }
  }, []);

  const fetchDirectories = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/settings/directories`);
      if (res.ok) {
        setDirectories(await res.json());
      }
    } catch (err) {
      console.error("Failed to fetch directories:", err);
    }
  }, []);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      await Promise.all([fetchSettings(), fetchModels(), fetchDirectories()]);
    } catch {
      setError("Error loading initial data");
    } finally {
      setLoading(false);
    }
  }, [fetchSettings, fetchModels, fetchDirectories]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSave = async () => {
    if (!settings) return;
    try {
      setSaving(true);
      setError(null);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (!response.ok) throw new Error("Failed to update settings");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error saving settings");
    } finally {
      setSaving(false);
    }
  };

  const handleAddDirectory = async () => {
    if (!newDirPath) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/settings/directories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: newDirPath, description: newDirDesc })
      });
      if (res.ok) {
        setNewDirPath("");
        setNewDirDesc("");
        fetchDirectories();
      } else {
        const d = await res.json();
        alert(d.error || "Failed to add directory");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveDirectory = async (id: number) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/settings/directories/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchDirectories();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'ollama': return <Cpu className="w-4 h-4 text-emerald-400" />;
      case 'anthropic': return <Zap className="w-4 h-4 text-orange-400" />;
      default: return <Globe className="w-4 h-4 text-blue-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex-grow flex items-center justify-center">
        <RefreshCw className="text-blue-500 animate-spin" size={32} />
      </div>
    );
  }

  return (
    <div className="flex-grow overflow-y-auto p-8 custom-scrollbar relative">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12 border-b border-neutral-800/30 pb-8 relative">
          <div className="absolute -left-8 -top-8 w-64 h-64 bg-blue-600/5 blur-[100px] pointer-events-none" />
          <div className="relative z-10">
            <h2 className="text-5xl font-black tracking-tighter text-white text-glow-blue italic flex items-center gap-4">
              <SettingsIcon size={48} className="text-blue-500" />
              SETTINGS
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <div className="h-px w-8 bg-blue-500/50" />
              <p className="text-neutral-500 text-[10px] font-black uppercase tracking-[0.3em]">System Configuration & Preferences</p>
            </div>
          </div>
        </header>

        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* AI Engines Section */}
          <section className="bg-neutral-900/60 border border-neutral-800/80 rounded-3xl p-8 shadow-xl backdrop-blur-xl border-t-neutral-700/50">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-3 bg-blue-500/10 rounded-2xl">
                <Zap size={20} className="text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-black text-white tracking-tight">AI Engines</h3>
                <p className="text-xs text-neutral-500 font-medium">Configure primary LLM models for specialized tasks</p>
              </div>
            </div>

            <div className="space-y-6">
              <div className="group relative">
                <label className="block text-[10px] font-black text-neutral-500 uppercase tracking-[0.2em] mb-3 ml-1 group-focus-within:text-blue-400 transition-colors">
                  Vision / OCR Model
                </label>
                
                <div className="relative">
                  <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="w-full bg-neutral-950/50 border border-neutral-800 text-white rounded-2xl py-4 px-6 flex items-center justify-between hover:bg-neutral-900 group transition-all focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/5"
                  >
                    <div className="flex items-center gap-3">
                      <Cpu size={18} className="text-blue-400" />
                      <span className="font-mono text-sm tracking-tight">{settings?.VISION_MODEL || "Select a model..."}</span>
                    </div>
                    <ChevronDown size={20} className={`text-neutral-500 transition-transform duration-300 ${isDropdownOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {isDropdownOpen && (
                    <div className="absolute top-full left-0 w-full mt-2 bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl z-50 py-2 max-h-64 overflow-y-auto custom-scrollbar animate-in fade-in slide-in-from-top-2">
                      {providers.map((p) => (
                        <div key={p.provider}>
                          <div className="px-4 py-2 text-[10px] font-black text-neutral-500 uppercase tracking-[0.2em] bg-neutral-950/30 flex items-center gap-2">
                            {getProviderIcon(p.provider)}
                            {p.name}
                          </div>
                          {p.models.map((m) => (
                            <button
                              key={m}
                              onClick={() => {
                                setSettings(prev => prev ? { ...prev, VISION_MODEL: m } : null);
                                setIsDropdownOpen(false);
                              }}
                              className={`w-full text-left px-8 py-3 text-sm font-mono flex items-center justify-between transition-colors hover:bg-blue-600/10 hover:text-blue-400 ${settings?.VISION_MODEL === m ? 'text-blue-400 bg-blue-600/5' : 'text-neutral-400'}`}
                            >
                              {m}
                              {settings?.VISION_MODEL === m && <div className="w-1.5 h-1.5 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]" />}
                            </button>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <p className="mt-3 text-[10px] text-neutral-600 leading-relaxed ml-1 italic">
                  * Used for extracting text and code from images within Neural Pipelines.
                </p>
              </div>
            </div>
          </section>

          {/* Directory Management Section */}
          <section className="bg-neutral-900/60 border border-neutral-800/80 rounded-3xl p-8 shadow-xl backdrop-blur-xl border-t-neutral-700/50">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-3 bg-purple-500/10 rounded-2xl">
                <Globe size={20} className="text-purple-400" />
              </div>
              <div>
                <h3 className="text-lg font-black text-white tracking-tight">Security Boundary</h3>
                <p className="text-xs text-neutral-500 font-medium">Manage permitted directories for AI file operations</p>
              </div>
            </div>

            <div className="space-y-6">
              {/* List of Directories */}
              <div className="space-y-3">
                <label className="block text-[10px] font-black text-neutral-500 uppercase tracking-[0.2em] mb-4 ml-1">
                  Permitted Paths
                </label>
                <div className="grid grid-cols-1 gap-3">
                  {directories.length === 0 ? (
                    <div className="p-6 border-2 border-dashed border-neutral-800 rounded-2xl text-center">
                      <p className="text-xs text-neutral-600 font-mono italic">No exclusive boundaries defined. System currently utilizes global defaults.</p>
                    </div>
                  ) : (
                    directories.map((dir) => (
                      <div key={dir.id} className="group flex items-center justify-between p-4 bg-neutral-950/50 border border-neutral-800 rounded-2xl hover:border-purple-500/30 transition-all">
                        <div className="min-w-0">
                          <p className="text-sm font-mono text-white truncate">{dir.path}</p>
                          {dir.description && <p className="text-[10px] text-neutral-500 mt-0.5">{dir.description}</p>}
                        </div>
                        <button 
                          onClick={() => handleRemoveDirectory(dir.id)}
                          className="p-2 text-neutral-600 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all"
                        >
                          <RefreshCw size={14} className="rotate-45" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Add New Directory Form */}
              <div className="pt-6 border-t border-neutral-800/50 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[9px] text-neutral-600 font-black uppercase tracking-widest ml-1">Absolute Path</label>
                    <input 
                      className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl px-4 py-3 text-xs text-white focus:border-purple-500/50 outline-none transition-all"
                      placeholder="e.g. C:/Data/Projects"
                      value={newDirPath}
                      onChange={(e) => setNewDirPath(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] text-neutral-600 font-black uppercase tracking-widest ml-1">Description (Optional)</label>
                    <input 
                      className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl px-4 py-3 text-xs text-white focus:border-purple-500/50 outline-none transition-all"
                      placeholder="e.g. Workspace for R&D"
                      value={newDirDesc}
                      onChange={(e) => setNewDirDesc(e.target.value)}
                    />
                  </div>
                </div>
                <button 
                  onClick={handleAddDirectory}
                  disabled={!newDirPath}
                  className="w-full py-3 bg-purple-600/10 hover:bg-purple-600/20 text-purple-400 border border-purple-500/20 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Authorize New Boundary
                </button>
              </div>
            </div>
          </section>

          {/* Footer / Save Actions */}
          <footer className="flex items-center justify-between pt-4">
            <div className="flex items-center gap-4">
              {error && (
                <div className="flex items-center gap-2 text-red-400 text-xs font-bold animate-pulse">
                  <Shield size={14} />
                  {error}
                </div>
              )}
              {success && (
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold">
                  <Zap size={14} className="animate-bounce" />
                  Settings saved successfully
                </div>
              )}
            </div>

            <button
              onClick={handleSave}
              disabled={saving}
              className={`flex items-center gap-3 px-8 py-4 rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all transform active:scale-95 shadow-lg ${
                saving 
                ? 'bg-neutral-800 text-neutral-600 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/20 hover:shadow-blue-600/40 border border-blue-400/30'
              }`}
            >
              {saving ? <RefreshCw size={16} className="animate-spin" /> : <Save size={16} />}
              {saving ? 'Persisting...' : 'Save Configuration'}
            </button>
          </footer>
        </div>
      </div>
    </div>
  );
}
