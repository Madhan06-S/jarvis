// frontend/src/builder-ui.ts

export let activeProjectName: string | null = null;
export let activeFilePath: string | null = null;
export let isServerRunning = false;
export let activeProjectUrl: string | null = null;

const builderPanel = document.getElementById('builder-panel') as HTMLDivElement;
const btnOpenBuilder = document.getElementById('btn-open-builder') as HTMLButtonElement;
const btnCloseBuilder = document.getElementById('btn-close-builder') as HTMLButtonElement;
const projectListEl = document.getElementById('builder-project-list') as HTMLDivElement;
const fileTreeEl = document.getElementById('builder-file-tree') as HTMLDivElement;
const editorFilename = document.getElementById('editor-filename') as HTMLHeadingElement;
const btnSaveFile = document.getElementById('btn-save-file') as HTMLButtonElement;
const editorEl = document.getElementById('builder-editor') as HTMLTextAreaElement;
const mutatorsPanel = document.getElementById('project-mutators') as HTMLDivElement;
const btnAddFeature = document.getElementById('btn-add-feature') as HTMLButtonElement;
const btnFixProject = document.getElementById('btn-fix-project') as HTMLButtonElement;
const featurePromptEl = document.getElementById('feature-prompt') as HTMLInputElement;
const fixPromptEl = document.getElementById('fix-prompt') as HTMLInputElement;

const btnToggleServer = document.getElementById('btn-toggle-server') as HTMLButtonElement;
const btnDeployVercel = document.getElementById('btn-deploy-vercel') as HTMLButtonElement;
const btnOpenIde = document.getElementById('btn-open-ide') as HTMLButtonElement;
const btnOpenExternal = document.getElementById('btn-open-external') as HTMLButtonElement;

const previewFrame = document.getElementById('builder-preview') as HTMLIFrameElement;
const previewPlaceholder = document.getElementById('preview-placeholder') as HTMLDivElement;
const logsEl = document.getElementById('builder-logs') as HTMLDivElement;

const newProjName = document.getElementById('new-proj-name') as HTMLInputElement;
const newProjStack = document.getElementById('new-proj-stack') as HTMLSelectElement;
const newProjDb = document.getElementById('new-proj-db') as HTMLSelectElement;
const newProjDesc = document.getElementById('new-proj-desc') as HTMLTextAreaElement;
const btnBuildProject = document.getElementById('btn-build-project') as HTMLButtonElement;

export function initBuilderUI() {
    // Open/Close
    if (btnOpenBuilder) {
        btnOpenBuilder.addEventListener('click', () => {
            builderPanel.style.display = 'flex';
            refreshProjects();
        });
    }
    if (btnCloseBuilder) {
        btnCloseBuilder.addEventListener('click', () => {
            builderPanel.style.display = 'none';
        });
    }

    // Build Project
    if (btnBuildProject) {
        btnBuildProject.addEventListener('click', async () => {
            const name = newProjName.value.trim();
            const stack = newProjStack.value;
            const db = newProjDb.value;
            const desc = newProjDesc.value.trim();

            if (!desc) {
                appendLog("System warning: Description cannot be empty, sir.");
                return;
            }

            appendLog(`Initiating build sequence for project: [${name || "Auto-Generated"}]`);
            btnBuildProject.disabled = true;
            btnBuildProject.innerText = "COMPILING ARCHITECTURE...";

            try {
                const res = await fetch('/api/projects/build', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, stack, db, description: desc })
                });
                const data = await res.json();
                if (data.status === 'started') {
                    appendLog("System response: Scaffolding engine activated. Waiting for websocket streams...");
                    // Reset fields
                    newProjName.value = '';
                    newProjDesc.value = '';
                } else {
                    appendLog(`System error: Build failed to initialize.`);
                }
            } catch (err: any) {
                appendLog(`System error: ${err.message}`);
            } finally {
                btnBuildProject.disabled = false;
                btnBuildProject.innerText = "INITIATE BUILD SEQUENCE";
            }
        });
    }

    // Save File
    if (btnSaveFile) {
        btnSaveFile.addEventListener('click', async () => {
            if (!activeProjectName || !activeFilePath) return;
            const content = editorEl.value;
            appendLog(`Saving ${activeFilePath}...`);
            btnSaveFile.disabled = true;

            try {
                const res = await fetch(`/api/projects/${activeProjectName}/file`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: activeFilePath, content })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    appendLog(`✓ ${activeFilePath} saved successfully.`);
                } else {
                    appendLog(`✗ Failed to save ${activeFilePath}.`);
                }
            } catch (err: any) {
                appendLog(`System error: ${err.message}`);
            } finally {
                btnSaveFile.disabled = false;
            }
        });
    }

    // Add Feature
    if (btnAddFeature) {
        btnAddFeature.addEventListener('click', async () => {
            if (!activeProjectName) return;
            const feature = featurePromptEl.value.trim();
            if (!feature) return;

            appendLog(`Injecting feature: "${feature}" into ${activeProjectName}...`);
            featurePromptEl.value = '';
            try {
                await fetch(`/api/projects/${activeProjectName}/feature`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ feature })
                });
            } catch (err: any) {
                appendLog(`System error: ${err.message}`);
            }
        });
    }

    // Fix Project
    if (btnFixProject) {
        btnFixProject.addEventListener('click', async () => {
            if (!activeProjectName) return;
            const errorDesc = fixPromptEl.value.trim();
            if (!errorDesc) return;

            appendLog(`Initiating automated repair for: "${errorDesc}"...`);
            fixPromptEl.value = '';
            try {
                await fetch(`/api/projects/${activeProjectName}/fix`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ error: errorDesc })
                });
            } catch (err: any) {
                appendLog(`System error: ${err.message}`);
            }
        });
    }

    // Toggle Dev Server
    if (btnToggleServer) {
        btnToggleServer.addEventListener('click', async () => {
            if (!activeProjectName) return;
            const action = isServerRunning ? 'stop' : 'start';
            btnToggleServer.disabled = true;
            appendLog(`${action === 'start' ? 'Launching' : 'Shutting down'} dev server for ${activeProjectName}...`);

            try {
                const res = await fetch(`/api/projects/${activeProjectName}/server/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    if (action === 'start') {
                        isServerRunning = true;
                        activeProjectUrl = data.url;
                        btnToggleServer.innerText = "STOP DEV SERVER";
                        btnToggleServer.style.background = "rgba(239, 68, 68, 0.2)";
                        btnToggleServer.style.borderColor = "#ef4444";
                        btnToggleServer.style.color = "#ef4444";
                        
                        previewFrame.src = data.url;
                        previewFrame.style.display = "block";
                        previewPlaceholder.style.display = "none";
                        btnOpenExternal.disabled = false;
                        btnOpenExternal.style.color = "#00e5ff";
                        btnOpenExternal.style.borderColor = "#00e5ff";
                        btnOpenExternal.style.cursor = "pointer";
                        
                        appendLog(`✓ Dev server online at ${data.url}`);
                    } else {
                        isServerRunning = false;
                        activeProjectUrl = null;
                        btnToggleServer.innerText = "START DEV SERVER";
                        btnToggleServer.style.background = "rgba(0,229,255,0.1)";
                        btnToggleServer.style.borderColor = "rgba(0,229,255,0.3)";
                        btnToggleServer.style.color = "#00e5ff";
                        
                        previewFrame.src = "about:blank";
                        previewFrame.style.display = "none";
                        previewPlaceholder.style.display = "flex";
                        btnOpenExternal.disabled = true;
                        btnOpenExternal.style.color = "rgba(0,229,255,0.4)";
                        btnOpenExternal.style.borderColor = "rgba(0,229,255,0.3)";
                        btnOpenExternal.style.cursor = "not-allowed";
                        
                        appendLog(`✓ Dev server offline.`);
                    }
                }
            } catch (err: any) {
                appendLog(`System error: ${err.message}`);
            } finally {
                btnToggleServer.disabled = false;
            }
        });
    }

    // Deploy to Vercel
    if (btnDeployVercel) {
        btnDeployVercel.addEventListener('click', async () => {
            if (!activeProjectName) return;
            appendLog(`Packaging & initiating deployment to Vercel edge networks...`);
            btnDeployVercel.disabled = true;
            try {
                await fetch(`/api/projects/${activeProjectName}/deploy`, { method: 'POST' });
            } catch (err: any) {
                appendLog(`System error: ${err.message}`);
                btnDeployVercel.disabled = false;
            }
        });
    }

    // Open in IDE
    if (btnOpenIde) {
        btnOpenIde.addEventListener('click', async () => {
            if (!activeProjectName) return;
            appendLog(`Opening project directory in local workspace IDE...`);
            try {
                await fetch(`/api/projects/${activeProjectName}/open-editor`, { method: 'POST' });
            } catch (err: any) {
                appendLog(`System error: ${err.message}`);
            }
        });
    }

    // Open External Tab
    if (btnOpenExternal) {
        btnOpenExternal.addEventListener('click', () => {
            if (activeProjectUrl) {
                window.open(activeProjectUrl, '_blank');
            }
        });
    }
}

export async function refreshProjects() {
    try {
        const res = await fetch('/api/projects');
        const projects = await res.json();
        projectListEl.innerHTML = '';

        if (projects.length === 0) {
            projectListEl.innerHTML = '<div style="color:rgba(0,229,255,0.4); font-size:12px; text-align:center; margin-top:10px;">No projects found</div>';
            return;
        }

        projects.forEach((proj: any) => {
            const row = document.createElement('div');
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';
            row.style.padding = '8px 12px';
            row.style.border = '1px solid rgba(0,229,255,0.2)';
            row.style.borderRadius = '4px';
            row.style.cursor = 'pointer';
            row.style.background = activeProjectName === proj.name ? 'rgba(0,229,255,0.15)' : 'rgba(0,0,0,0.2)';
            row.style.fontSize = '12px';

            const nameEl = document.createElement('span');
            nameEl.innerText = proj.name;
            nameEl.style.fontWeight = 'bold';
            nameEl.style.color = activeProjectName === proj.name ? '#00e5ff' : 'rgba(0,229,255,0.85)';

            const statusEl = document.createElement('span');
            statusEl.innerText = proj.running ? '● RUNNING' : '■ OFFLINE';
            statusEl.style.color = proj.running ? '#00ff88' : 'rgba(0,229,255,0.4)';
            statusEl.style.fontSize = '10px';

            row.appendChild(nameEl);
            row.appendChild(statusEl);

            row.addEventListener('click', () => {
                selectProject(proj.name, proj.running, proj.url);
            });

            projectListEl.appendChild(row);
        });
    } catch (err: any) {
        appendLog(`System error listing projects: ${err.message}`);
    }
}

export async function selectProject(name: string, running: boolean, url: string | null) {
    activeProjectName = name;
    isServerRunning = running;
    activeProjectUrl = url;
    activeFilePath = null;

    editorFilename.innerText = "EDITOR: (No File Selected)";
    editorEl.value = '';
    editorEl.readOnly = true;
    btnSaveFile.style.display = 'none';

    // Enable buttons
    btnToggleServer.disabled = false;
    btnToggleServer.style.cursor = "pointer";
    btnToggleServer.innerText = running ? "STOP DEV SERVER" : "START DEV SERVER";
    if (running) {
        btnToggleServer.style.background = "rgba(239, 68, 68, 0.2)";
        btnToggleServer.style.borderColor = "#ef4444";
        btnToggleServer.style.color = "#ef4444";
        
        previewFrame.src = url || '';
        previewFrame.style.display = "block";
        previewPlaceholder.style.display = "none";
        
        btnOpenExternal.disabled = false;
        btnOpenExternal.style.color = "#00e5ff";
        btnOpenExternal.style.borderColor = "#00e5ff";
        btnOpenExternal.style.cursor = "pointer";
    } else {
        btnToggleServer.style.background = "rgba(0,229,255,0.1)";
        btnToggleServer.style.borderColor = "rgba(0,229,255,0.3)";
        btnToggleServer.style.color = "#00e5ff";
        
        previewFrame.src = "about:blank";
        previewFrame.style.display = "none";
        previewPlaceholder.style.display = "flex";
        
        btnOpenExternal.disabled = true;
        btnOpenExternal.style.color = "rgba(0,229,255,0.4)";
        btnOpenExternal.style.borderColor = "rgba(0,229,255,0.3)";
        btnOpenExternal.style.cursor = "not-allowed";
    }

    btnDeployVercel.disabled = false;
    btnDeployVercel.style.color = "#00e5ff";
    btnDeployVercel.style.borderColor = "#00e5ff";
    btnDeployVercel.style.cursor = "pointer";

    btnOpenIde.disabled = false;
    btnOpenIde.style.color = "#00e5ff";
    btnOpenIde.style.borderColor = "#00e5ff";
    btnOpenIde.style.cursor = "pointer";

    mutatorsPanel.style.display = 'flex';

    appendLog(`System active project updated to: [${name}]`);
    
    // Refresh File Tree
    await loadFileTree();
    // Refresh project selection backgrounds
    refreshProjects();
}

async function loadFileTree() {
    if (!activeProjectName) return;
    try {
        const res = await fetch(`/api/projects/${activeProjectName}/files`);
        const files = await res.json();
        fileTreeEl.innerHTML = '';

        if (files.length === 0) {
            fileTreeEl.innerHTML = '<div style="color:rgba(0,229,255,0.4); text-align:center;">Empty workspace</div>';
            return;
        }

        files.forEach((file: string) => {
            const item = document.createElement('div');
            item.style.padding = '4px 8px';
            item.style.cursor = 'pointer';
            item.style.fontSize = '11px';
            item.style.borderRadius = '3px';
            item.style.border = '1px solid transparent';
            item.style.overflow = 'hidden';
            item.style.textOverflow = 'ellipsis';
            item.style.whiteSpace = 'nowrap';
            item.innerText = file;

            if (activeFilePath === file) {
                item.style.background = 'rgba(0,229,255,0.15)';
                item.style.color = '#00e5ff';
            } else {
                item.style.color = 'rgba(0,229,255,0.7)';
            }

            item.addEventListener('mouseenter', () => {
                item.style.border = '1px solid rgba(0,229,255,0.3)';
            });
            item.addEventListener('mouseleave', () => {
                item.style.border = '1px solid transparent';
            });

            item.addEventListener('click', () => {
                selectFile(file);
            });

            fileTreeEl.appendChild(item);
        });
    } catch (err: any) {
        appendLog(`System error loading files: ${err.message}`);
    }
}

async function selectFile(path: string) {
    if (!activeProjectName) return;
    activeFilePath = path;
    editorFilename.innerText = `EDITOR: ${path}`;
    editorEl.value = 'Loading file contents, sir...';
    editorEl.readOnly = true;
    btnSaveFile.style.display = 'none';

    try {
        const res = await fetch(`/api/projects/${activeProjectName}/file?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        editorEl.value = data.content || '';
        editorEl.readOnly = false;
        btnSaveFile.style.display = 'block';
        
        // Re-draw file tree to update active file highlight
        await loadFileTree();
    } catch (err: any) {
        appendLog(`System error reading file: ${err.message}`);
        editorEl.value = 'Failed to load file contents.';
    }
}

export function appendLog(line: string) {
    if (!logsEl) return;
    const p = document.createElement('div');
    p.innerText = line;
    logsEl.appendChild(p);
    logsEl.scrollTop = logsEl.scrollHeight;
}

export function handleCodeStreamStart() {
    editorFilename.innerText = "STREAMING INCOMING CODE...";
    editorEl.value = "";
    editorEl.readOnly = true;
    btnSaveFile.style.display = "none";
}

export function handleCodeStreamChunk(chunk: string) {
    if (editorEl) {
        editorEl.value += chunk;
        editorEl.scrollTop = editorEl.scrollHeight;
    }
}

export function handleBuildComplete(name: string, url: string) {
    btnBuildProject.disabled = false;
    btnBuildProject.innerText = "INITIATE BUILD SEQUENCE";
    
    appendLog(`✅ System build completed for project: [${name}]`);
    appendLog(`Live server initialized at: ${url}`);
    
    refreshProjects();
    selectProject(name, true, url);
}
