import { useState, useEffect, useRef } from 'react';
import { Terminal, X, Play, Folder, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

interface BuildLog {
  type: string;
  build_id: string;
  status: string;
  message: string;
  progress: number;
  timestamp: string;
}

interface Project {
  name: string;
  path: string;
  created: string;
  can_start: boolean;
}

export function AntigravityWorkspace() {
  const [isOpen, setIsOpen] = useState(true);
  const [prompt, setPrompt] = useState('');
  const [isBuilding, setIsBuilding] = useState(false);
  const [logs, setLogs] = useState<BuildLog[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentBuildId, setCurrentBuildId] = useState<string | null>(null);
  const [buildStatus, setBuildStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Fetch existing projects on mount
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch('/builder/projects');
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) {
      console.error('Failed to fetch projects:', e);
    }
  };

  const startBuild = async () => {
    if (!prompt.trim() || isBuilding) return;
    
    setIsBuilding(true);
    setBuildStatus('running');
    setLogs([]);

    try {
      // 1. Start build on backend
      const res = await fetch('/builder/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          app_name: null,
          stack: 'react_fastapi',
          database: 'sqlite',
          skip_images: false,  // Will fallback to gradient SVGs automatically
          auto_start: true
        })
      });

      const data = await res.json();
      const buildId = data.build_id;
      setCurrentBuildId(buildId);

      // 2. Connect WebSocket for live logs
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/builder/ws/${buildId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        addLog('🔌 Connected to build stream...', 0);
      };

      ws.onmessage = (event) => {
        const msg: BuildLog = JSON.parse(event.data);
        setLogs(prev => [...prev, msg]);
        
        if (msg.status === 'completed') {
          setBuildStatus('completed');
          setIsBuilding(false);
          ws.close();
          fetchProjects();
        } else if (msg.status === 'failed') {
          setBuildStatus('failed');
          setIsBuilding(false);
          ws.close();
        }
      };

      ws.onerror = () => {
        addLog('❌ WebSocket connection failed. Check builder server.', 0);
        setBuildStatus('failed');
        setIsBuilding(false);
      };

      ws.onclose = () => {
        if (buildStatus === 'running') {
          setBuildStatus('failed');
          setIsBuilding(false);
        }
      };

    } catch (e) {
      addLog(`❌ Failed to start build: ${e}`, 0);
      setBuildStatus('failed');
      setIsBuilding(false);
    }
  };

  const addLog = (message: string, progress: number) => {
    setLogs(prev => [...prev, {
      type: 'build_log',
      build_id: currentBuildId || '',
      status: 'running',
      message,
      progress,
      timestamp: new Date().toISOString()
    }]);
  };

  const startExistingProject = async (name: string) => {
    try {
      await fetch(`/builder/projects/${name}/start`, { method: 'POST' });
      addLog(`🚀 Started project: ${name}`, 100);
    } catch (e) {
      addLog(`❌ Failed to start ${name}`, 0);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'failed': return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'running': return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      default: return <Terminal className="w-4 h-4 text-slate-400" />;
    }
  };

  const getProgressColor = (progress: number) => {
    if (progress < 30) return 'text-blue-400';
    if (progress < 70) return 'text-yellow-400';
    if (progress < 100) return 'text-green-400';
    return 'text-emerald-400';
  };

  return (
    <div className={`fixed right-0 top-0 h-full transition-all duration-300 ${isOpen ? 'w-96' : 'w-0'} z-50`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute left-0 top-1/2 -translate-x-full -translate-y-1/2 bg-slate-900/90 border border-slate-700 text-cyan-400 p-2 rounded-l-lg hover:bg-slate-800 transition"
      >
        {isOpen ? <X className="w-5 h-5" /> : <Terminal className="w-5 h-5" />}
      </button>

      <div className="h-full bg-slate-900/95 border-l border-cyan-500/30 backdrop-blur-sm flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-cyan-400 font-mono text-sm tracking-wider uppercase font-bold">
            Antigravity Workspace
          </h2>
          <div className="mt-2 text-xs text-slate-500 font-mono">
            {buildStatus === 'running' && <span className="text-yellow-400">● BUILDING...</span>}
            {buildStatus === 'completed' && <span className="text-green-400">● READY</span>}
            {buildStatus === 'failed' && <span className="text-red-400">● FAILED</span>}
            {buildStatus === 'idle' && <span>● IDLE</span>}
          </div>
        </div>

        <div className="p-4 border-b border-slate-800">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="// Describe your app, sir..."
            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-sm text-cyan-100 placeholder-slate-600 font-mono resize-none h-20 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none"
            disabled={isBuilding}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) startBuild();
            }}
          />
          <button
            onClick={startBuild}
            disabled={isBuilding || !prompt.trim()}
            className="mt-2 w-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-600 text-white text-sm font-mono py-2 rounded-lg transition flex items-center justify-center gap-2"
          >
            {isBuilding ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> BUILDING...</>
            ) : (
              <><Play className="w-4 h-4" /> EXECUTE BUILD</>
            )}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-xs">
          {logs.length === 0 && (
            <div className="text-slate-600 text-center mt-8">
              No active build. Enter a prompt to begin.
            </div>
          )}
          
          {logs.map((log, i) => (
            <div key={i} className="flex gap-2 items-start animate-in fade-in slide-in-from-left-2 duration-200">
              <span className="mt-0.5">{getStatusIcon(log.status)}</span>
              <div className="flex-1">
                <span className={getProgressColor(log.progress)}>
                  {log.message}
                </span>
                {log.progress > 0 && (
                  <div className="mt-1 h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-cyan-500 transition-all duration-500"
                      style={{ width: `${log.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>

        {projects.length > 0 && (
          <div className="p-4 border-t border-slate-800 max-h-48 overflow-y-auto">
            <h3 className="text-slate-400 text-xs uppercase tracking-wider mb-2 font-bold">
              Generated Projects
            </h3>
            <div className="space-y-1">
              {projects.map((p) => (
                <div 
                  key={p.name}
                  className="flex items-center justify-between p-2 bg-slate-950 rounded border border-slate-800 hover:border-cyan-500/30 transition"
                >
                  <div className="flex items-center gap-2">
                    <Folder className="w-3 h-3 text-slate-500" />
                    <span className="text-slate-300 text-xs">{p.name}</span>
                  </div>
                  {p.can_start && (
                    <button
                      onClick={() => startExistingProject(p.name)}
                      className="text-cyan-400 hover:text-cyan-300 text-xs"
                    >
                      START
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="p-3 border-t border-slate-800 text-[10px] text-slate-600 font-mono text-center">
          J.A.R.V.I.S. v2.0 Real App Engine
        </div>
      </div>
    </div>
  );
}
