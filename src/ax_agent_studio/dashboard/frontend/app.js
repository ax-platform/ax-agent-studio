// API Base URL
const API_BASE = window.location.origin;

// WebSocket for logs
let logsWebSocket = null;

// State
let monitors = [];
let environments = [];
let configs = [];
let configsByEnvironment = {};
let models = [];
let prompts = [];
let providers = [];
let deploymentGroups = [];
let autoScroll = true;
let selectedEnvironment = 'local'; // Default to local
let selectedProvider = 'ollama'; // Default provider
let logFilter = 'all'; // Default to show all logs
let verboseMode = false; // Default to condensed logs

const escapeAttr = (value) => String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

// Initialize dashboard
document.addEventListener('DOMContentLoaded', async () => {
    await loadEnvironments();
    await loadConfigs();
    await loadProviders();
    await loadPrompts();
    await loadDeploymentGroups();
    await loadMonitors();
    await updateKillSwitchButton(); // Check initial kill switch state
    initializeWebSocket();
    setupEventListeners();
    updateMonitorTypeUI(document.getElementById('monitor-type-select').value);

    // Refresh monitors and kill switch state every 5 seconds
    setInterval(async () => {
        await loadMonitors();
        await updateKillSwitchButton();
        await loadDeploymentGroups();
    }, 5000);
});

// Event Listeners
function updateMonitorTypeUI(monitorType) {
    const providerGroup = document.getElementById('provider-group');
    const modelGroup = document.getElementById('model-group');
    const systemPromptGroup = document.getElementById('system-prompt-group');
    const frameworksInfo = document.getElementById('frameworks-info');
    const startButton = document.querySelector('#start-monitor-form button[type="submit"]');

    const hideAdvancedGroups = ['echo', 'frameworks'].includes(monitorType);
    if (providerGroup) providerGroup.style.display = hideAdvancedGroups ? 'none' : 'block';
    if (modelGroup) modelGroup.style.display = hideAdvancedGroups ? 'none' : 'block';
    if (systemPromptGroup) systemPromptGroup.style.display = hideAdvancedGroups ? 'none' : 'block';

    if (frameworksInfo) {
        frameworksInfo.style.display = monitorType === 'frameworks' ? 'block' : 'none';
    }

    if (startButton) {
        if (monitorType === 'frameworks') {
            startButton.disabled = true;
            startButton.textContent = '📚 Explore Framework';
        } else {
            startButton.disabled = false;
            startButton.textContent = '▶️ Deploy Agent';
        }
    }
}

function setupEventListeners() {
    document.getElementById('pause-all-btn').addEventListener('click', async () => {
        await pauseAllMonitors();
    });

    document.getElementById('reset-all-btn').addEventListener('click', async () => {
        if (confirm('Reset backlog for all agents in this environment?')) {
            await resetAllAgents();
        }
    });

    document.getElementById('start-monitor-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await startMonitor();
    });

    document.getElementById('environment-select').addEventListener('change', async (e) => {
        selectedEnvironment = e.target.value;
        await loadConfigsForEnvironment(selectedEnvironment);
        await loadDeploymentGroups(selectedEnvironment);
    });

    document.getElementById('monitor-type-select').addEventListener('change', (e) => {
        updateMonitorTypeUI(e.target.value);
    });

    document.getElementById('provider-select').addEventListener('change', async (e) => {
        selectedProvider = e.target.value;
        await loadModelsForProvider(selectedProvider);
    });

    document.getElementById('auto-scroll').addEventListener('change', (e) => {
        autoScroll = e.target.checked;
    });

    document.getElementById('log-filter').addEventListener('change', (e) => {
        logFilter = e.target.value;
        filterLogs();
    });

    document.getElementById('verbose-mode').addEventListener('change', (e) => {
        verboseMode = e.target.checked;
        applyVerboseMode();
    });

    document.getElementById('copy-logs-btn').addEventListener('click', () => {
        copyLogs();
    });

    document.getElementById('refresh-logs-btn').addEventListener('click', () => {
        refreshLogs();
    });

    document.getElementById('clear-logs-btn').addEventListener('click', async () => {
        try {
            // Clear log files on server
            const response = await fetch(`${API_BASE}/api/logs/clear-all`, {
                method: 'POST'
            });
            const data = await response.json();

            // Clear DOM
            document.getElementById('logs-container').innerHTML = '<p class="empty-state">Logs cleared. Waiting for new logs...</p>';

            if (data.success) {
                showNotification(`Cleared ${data.count} log file(s) ✓`, 'success');
            }
        } catch (error) {
            console.error('Error clearing logs:', error);
            showNotification('Failed to clear logs', 'error');
        }
    });

    // Kill button - toggles between kill and resume
    document.getElementById('kill-btn').addEventListener('click', async () => {
        await toggleKillSwitch();
    });
}

// API Calls
async function loadEnvironments() {
    try {
        const response = await fetch(`${API_BASE}/api/environments`);
        const data = await response.json();
        environments = data.environments;

        const select = document.getElementById('environment-select');
        select.innerHTML = environments.map(env =>
            `<option value="${env}" ${env === 'local' ? 'selected' : ''}>${env.charAt(0).toUpperCase() + env.slice(1)}</option>`
        ).join('');

        // Set default selected environment
        selectedEnvironment = environments.includes('local') ? 'local' : environments[0];
    } catch (error) {
        console.error('Error loading environments:', error);
        showNotification('Failed to load environments', 'error');
    }
}

async function loadConfigs() {
    try {
        const response = await fetch(`${API_BASE}/api/configs/by-environment`);
        const data = await response.json();
        configsByEnvironment = data.configs_by_environment;

        // Load configs for selected environment
        await loadConfigsForEnvironment(selectedEnvironment);
    } catch (error) {
        console.error('Error loading configs:', error);
        showNotification('Failed to load configs', 'error');
    }
}

async function loadConfigsForEnvironment(environment) {
    const envConfigs = configsByEnvironment[environment] || [];
    configs = envConfigs;

    const select = document.getElementById('agent-select');
    if (configs.length === 0) {
        select.innerHTML = '<option value="">No agents in this environment</option>';
        document.getElementById('agent-help').textContent = '';
    } else {
        select.innerHTML = configs.map(c =>
            `<option value="${c.path}" data-server="${c.server_url}">${c.display_name || c.agent_name}</option>`
        ).join('');

        // Show server info for first agent
        updateAgentHelp(configs[0]);
    }

    // Update agent help on selection change
    select.onchange = (e) => {
        const config = configs.find(c => c.path === e.target.value);
        if (config) updateAgentHelp(config);
    };
}

function updateAgentHelp(config) {
    const helpText = document.getElementById('agent-help');
    if (config) {
        helpText.textContent = `${config.server_type === 'local' ? '🏠 Local' : '🌐 Remote'} • ${config.description || config.server_url}`;
    } else {
        helpText.textContent = '';
    }
}

// Removed demo functionality - focus on Agent Factory core features

async function loadModels() {
    // Deprecated - kept for backward compatibility
    // Use loadModelsForProvider() instead
    await loadModelsForProvider('ollama');
}

async function loadProviders() {
    try {
        const response = await fetch(`${API_BASE}/api/providers`);
        const data = await response.json();
        providers = data.providers;

        const select = document.getElementById('provider-select');
        select.innerHTML = providers.length > 0
            ? providers.map(p => `<option value="${p.id}">${p.name}</option>`).join('')
            : '<option value="">No providers available</option>';

        // Load defaults
        const defaultsResponse = await fetch(`${API_BASE}/api/providers/defaults`);
        const defaults = await defaultsResponse.json();

        // Set default provider
        if (defaults.provider) {
            selectedProvider = defaults.provider;
            select.value = defaults.provider;
        }

        // Load models for default provider
        await loadModelsForProvider(selectedProvider);

    } catch (error) {
        console.error('Error loading providers:', error);
        showNotification('Failed to load providers', 'error');
    }
}

async function loadModelsForProvider(providerId) {
    try {
        const response = await fetch(`${API_BASE}/api/providers/${providerId}/models`);
        const data = await response.json();
        models = data.models;

        const select = document.getElementById('model-select');
        const options = models.map(m => {
            const label = m.recommended ? `${m.name} ⭐` : m.name;
            const selected = m.default ? ' selected' : '';
            return `<option value="${m.id}" title="${m.description}"${selected}>${label}</option>`;
        });

        select.innerHTML = models.length > 0
            ? options.join('')
            : '<option value="">No models available</option>';
    } catch (error) {
        console.error('Error loading models:', error);
        showNotification(`Failed to load models for ${providerId}`, 'error');
    }
}

async function loadPrompts() {
    try {
        const response = await fetch(`${API_BASE}/api/prompts`);
        const data = await response.json();
        prompts = data.prompts;

        const select = document.getElementById('system-prompt-select');
        select.innerHTML = '<option value="">None (use model defaults)</option>' +
            prompts.map(p => `<option value="${p.file}" data-description="${p.description}">${p.name}</option>`).join('');

        // Update help text when prompt is selected
        select.addEventListener('change', (e) => {
            const helpText = document.getElementById('prompt-help');
            const selectedOption = e.target.options[e.target.selectedIndex];
            const description = selectedOption.dataset.description;
            helpText.textContent = description || 'Choose a personality template';
        });
    } catch (error) {
        console.error('Error loading prompts:', error);
        showNotification('Failed to load system prompts', 'error');
    }
}

async function loadDeploymentGroups(environment = selectedEnvironment) {
    try {
        const url = new URL(`${API_BASE}/api/deployments`);
        if (environment) {
            url.searchParams.set('environment', environment);
        }

        const response = await fetch(url.toString());
        const data = await response.json();
        deploymentGroups = data.deployment_groups || [];
        renderDeploymentGroups();
    } catch (error) {
        console.error('Error loading deployment groups:', error);
        showNotification('Failed to load deployment groups', 'error');
    }
}

async function loadMonitors() {
    try {
        const response = await fetch(`${API_BASE}/api/monitors`);
        const data = await response.json();
        monitors = data.monitors;
        renderMonitors();
        updateLogFilter();
    } catch (error) {
        console.error('Error loading monitors:', error);
        showNotification('Failed to load monitors', 'error');
    }
}

async function startMonitor() {
    const configPath = document.getElementById('agent-select').value;
    const monitorType = document.getElementById('monitor-type-select').value;
    const provider = document.getElementById('provider-select').value;
    const model = document.getElementById('model-select').value;
    const promptFile = document.getElementById('system-prompt-select').value;

    if (monitorType === 'frameworks') {
        showNotification('Frameworks is an informational section. Explore the quick-start guide below.', 'info');
        return;
    }

    const config = configs.find(c => c.path === configPath);
    if (!config) {
        showNotification('Please select an agent', 'error');
        return;
    }

    // Get the actual prompt content from the selected prompt file
    let systemPromptContent = null;
    let systemPromptName = null;
    if (promptFile) {
        const selectedPrompt = prompts.find(p => p.file === promptFile);
        if (selectedPrompt) {
            systemPromptContent = selectedPrompt.prompt;
            systemPromptName = selectedPrompt.name;
        }
    }

    try {
        const response = await fetch(`${API_BASE}/api/monitors/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                config: {
                    agent_name: config.agent_name,
                    config_path: configPath,
                    monitor_type: monitorType,
                    provider: ['echo', 'frameworks'].includes(monitorType) ? null : provider,
                    model: ['echo', 'frameworks'].includes(monitorType) ? null : model,
                    system_prompt: systemPromptContent,
                    system_prompt_name: systemPromptName
                }
            })
        });

        const data = await response.json();
        if (data.success) {
            showNotification(`Agent deployed: ${config.agent_name}`, 'success');
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);

            // Expand Running Agents section if collapsed
            const monitorsList = document.getElementById('monitors-list');
            const toggle = document.getElementById('agents-toggle');
            if (monitorsList.style.display === 'none') {
                monitorsList.style.display = 'block';
                toggle.textContent = '▼';
                localStorage.setItem('runningAgentsCollapsed', 'false');
            }

            // Scroll to Running Agents section
            monitorsList.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            showNotification('Failed to deploy agent', 'error');
        }
    } catch (error) {
        console.error('Error deploying agent:', error);
        showNotification('Failed to deploy agent', 'error');
    }
}

async function deployGroup(groupId) {
    try {
        const response = await fetch(`${API_BASE}/api/deployments/${groupId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ environment: selectedEnvironment })
        });

        const data = await response.json();
        if (data.success) {
            const startedCount = Array.isArray(data.monitors) ? data.monitors.length : (data.started_count || 0);
            showNotification(`Deployment group '${groupId}' started - ${startedCount} agent(s) deployed`, 'success');
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);

            // Scroll to running agents section to show results
            const runningAgents = document.querySelector('#monitors-list');
            if (runningAgents) {
                runningAgents.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Ensure section is expanded
                const agentsSection = document.querySelector('.left-panel .card:first-child');
                if (agentsSection && agentsSection.classList.contains('collapsed')) {
                    toggleRunningAgents();
                }
            }
        } else {
            throw new Error(data.detail || 'Unknown error');
        }
    } catch (error) {
        console.error(`Error deploying group ${groupId}:`, error);
        showNotification(`Failed to deploy group '${groupId}'`, 'error');
    }
}

async function stopGroup(groupId) {
    try {
        const response = await fetch(`${API_BASE}/api/deployments/${groupId}/stop`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.success) {
            const stoppedCount = data.stopped ?? 0;
            showNotification(`Deployment group '${groupId}' paused (${stoppedCount} agent(s))`, 'success');
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);
        } else {
            throw new Error(data.detail || 'Unknown error');
        }
    } catch (error) {
        console.error(`Error pausing group ${groupId}:`, error);
        showNotification(`Failed to pause group '${groupId}'`, 'error');
    }
}

async function pauseMonitor(monitorId) {
    try {
        const response = await fetch(`${API_BASE}/api/monitors/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ monitor_id: monitorId })
        });

        const data = await response.json();
        if (data.success) {
            showNotification('Monitor paused', 'success');
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);
        } else {
            showNotification('Failed to pause monitor', 'error');
        }
    } catch (error) {
        console.error('Error pausing monitor:', error);
        showNotification('Failed to pause monitor', 'error');
    }
}

async function startMonitorFromStatus(monitorId) {
    try {
        const response = await fetch(`${API_BASE}/api/monitors/restart/${monitorId}`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.success) {
            showNotification('Monitor started', 'success');
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);
        } else {
            showNotification('Failed to start monitor', 'error');
        }
    } catch (error) {
        console.error('Error starting monitor:', error);
        showNotification('Failed to start monitor', 'error');
    }
}

async function killMonitor(monitorId) {
    try {
        // Kill the monitor
        const killResponse = await fetch(`${API_BASE}/api/monitors/kill`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ monitor_id: monitorId })
        });

        const killData = await killResponse.json();
        if (killData.success) {
            // Auto-delete after killing
            const deleteResponse = await fetch(`${API_BASE}/api/monitors/${monitorId}`, {
                method: 'DELETE'
            });

            const deleteData = await deleteResponse.json();
            if (deleteData.success) {
                showNotification('Monitor killed and removed ✓', 'success');
            } else {
                showNotification('Monitor killed (manual delete needed)', 'success');
            }
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);
        } else {
            showNotification('Failed to kill monitor', 'error');
        }
    } catch (error) {
        console.error('Error killing monitor:', error);
        showNotification('Failed to kill monitor', 'error');
    }
}

async function pauseAllMonitors() {
    try {
        const response = await fetch(`${API_BASE}/api/monitors/stop-all`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.success) {
            // Set global flag for kill switch
            window.killSwitchActive = data.kill_switch_active || true;

            showNotification(data.message || 'Paused all monitors', 'success');
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);
        } else {
            showNotification('Failed to pause monitors', 'error');
        }
    } catch (error) {
        console.error('Error pausing monitors:', error);
        showNotification('Failed to pause monitors', 'error');
    }
}

async function resetAgent(agentName) {
    try {
        const response = await fetch(`${API_BASE}/api/agents/${encodeURIComponent(agentName)}/reset`, {
            method: 'POST'
        });

        const data = await response.json();
        if (data.success) {
            const cleared = data.result?.remote_cleared || 0;
            const localCleared = data.result?.local_cleared || 0;
            showNotification(`Reset ${agentName} backlog (${cleared} remote, ${localCleared} local)`, 'success');
            if (data.result?.errors && data.result.errors.length) {
                showNotification(`Warnings while resetting ${agentName}: ${data.result.errors.join('; ')}`, 'warning');
            }
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);
        } else {
            showNotification(`Failed to reset ${agentName}`, 'error');
        }
    } catch (error) {
        console.error(`Error resetting ${agentName}:`, error);
        showNotification(`Failed to reset ${agentName}`, 'error');
    }
}

async function resetAllAgents() {
    try {
        const response = await fetch(`${API_BASE}/api/agents/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ environment: selectedEnvironment })
        });

        const data = await response.json();
        if (data.success) {
            const total = data.count || 0;
            showNotification(`Reset backlog for ${total} agent(s)`, 'success');
            if (data.skipped_running && data.skipped_running.length) {
                showNotification(`Skipped ${data.skipped_running.length} running agent(s): ${data.skipped_running.join(', ')}`, 'warning');
            }
            await loadMonitors();
            await loadDeploymentGroups(selectedEnvironment);
        } else {
            showNotification('Failed to reset agents', 'error');
        }
    } catch (error) {
        console.error('Error resetting agents:', error);
        showNotification('Failed to reset agents', 'error');
    }
}

async function testMonitor(agentName, monitorType) {
    // Find the test button and show immediate feedback
    const buttons = document.querySelectorAll('.monitor-card button');
    let testButton = null;
    buttons.forEach(btn => {
        if (btn.textContent.includes('✏️') && btn.closest('.monitor-card').textContent.includes(agentName)) {
            testButton = btn;
        }
    });

    // Disable button and show loading state
    if (testButton) {
        testButton.disabled = true;
        testButton.textContent = '⏳';
    }

    // Send a test message from a different agent
    const fromAgent = agentName === 'lunar_craft_128' ? 'orion_344' : 'lunar_craft_128';

    // Context-aware test messages based on monitor type
    let testMessage;
    if (monitorType === 'echo') {
        testMessage = `Test echo at ${new Date().toLocaleTimeString()} 🧪`;
    } else if (monitorType === 'ollama' || monitorType === 'langgraph') {
        const aiQuestions = [
            "What's a fun fact about AI?",
            "Tell me a quick joke!",
            "What's the weather like in your digital world?",
            "If you could have any superpower, what would it be?",
            "What's your favorite programming language and why?"
        ];
        const randomQuestion = aiQuestions[Math.floor(Math.random() * aiQuestions.length)];
        testMessage = randomQuestion;
    } else {
        testMessage = `Test message at ${new Date().toLocaleTimeString()} 🧪`;
    }

    try {
        const response = await fetch(`${API_BASE}/api/messages/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_agent: fromAgent,
                to_agent: agentName,
                message: testMessage
            })
        });

        const data = await response.json();
        if (data.success) {
            showNotification(`Test sent to @${agentName} ✓`, 'success');
            // Show checkmark briefly
            if (testButton) {
                testButton.textContent = '✓';
                setTimeout(() => {
                    testButton.textContent = '✏️';
                    testButton.disabled = false;
                }, 1500);
            }
        } else {
            showNotification('Failed to send test message', 'error');
            if (testButton) {
                testButton.textContent = '✏️';
                testButton.disabled = false;
            }
        }
    } catch (error) {
        console.error('Error sending test message:', error);
        showNotification('Failed to send test message', 'error');
        if (testButton) {
            testButton.textContent = '✏️';
            testButton.disabled = false;
        }
    }
}

// Expose functions to global scope for onclick handlers
window.pauseMonitor = pauseMonitor;
window.startMonitorFromStatus = startMonitorFromStatus;
window.killMonitor = killMonitor;
window.resetAgent = resetAgent;
window.testMonitor = testMonitor;

// Render Functions
function renderDeploymentGroups() {
    const container = document.getElementById('deployment-groups-list');
    if (!container) return;

    if (!deploymentGroups || deploymentGroups.length === 0) {
        container.innerHTML = '<p class="empty-state">No deployment groups configured</p>';
        return;
    }

    container.innerHTML = deploymentGroups.map(group => {
        const defaults = group.defaults || {};
        const details = [
            defaults.monitor ? `Monitor: ${defaults.monitor}` : null,
            defaults.provider ? `Provider: ${defaults.provider}` : null,
            defaults.model ? `Model: ${defaults.model}` : null,
            defaults.process_backlog !== undefined ? `Backlog: ${defaults.process_backlog ? 'resume' : 'fresh'}` : null
        ].filter(Boolean).join(' · ');

        const agentsMarkup = group.agents.map(agent => {
            const parts = [`@${agent.id}`];
            if (agent.monitor) parts.push(agent.monitor);
            if (agent.model) parts.push(agent.model);
            return `<span class="agent-chip">${parts.join(' • ')}</span>`;
        }).join('');

        const tagsMarkup = (group.tags || []).map(tag => `<span class="group-tag">${tag}</span>`).join('');

        const runningText = `${group.running_count || 0}/${group.total_agents} running`;
        const statusEmoji = group.status === 'running' ? '🟢' : '⚪️';
        const actionButton = group.status === 'running'
            ? `<button class="btn btn-danger btn-sm" onclick="stopGroup('${group.id}')">Stop Group</button>`
            : `<button class="btn btn-success btn-sm" onclick="deployGroup('${group.id}')">Deploy Group</button>`;

        return `
        <div class="group-card">
            <div class="group-header">
                <div class="group-title">
                    <strong>${group.name}</strong>
                    <span class="group-status">${statusEmoji} ${group.status.toUpperCase()}</span>
                </div>
                <div class="group-actions">
                    ${actionButton}
                </div>
            </div>
            <p class="group-description">${group.description || 'No description provided.'}</p>
            <div class="group-meta">
                <span>Agents: ${group.total_agents}</span>
                <span>${runningText}</span>
                ${details ? `<span>${details}</span>` : ''}
                ${group.environment ? `<span>Env: ${group.environment}</span>` : ''}
            </div>
            ${tagsMarkup ? `<div class="group-tags">${tagsMarkup}</div>` : ''}
            <div class="group-agents">
                ${agentsMarkup}
            </div>
        </div>
        `;
    }).join('');
}

function renderMonitors() {
    const container = document.getElementById('monitors-list');

    if (monitors.length === 0) {
        container.innerHTML = '<p class="empty-state">No agents running</p>';
        return;
    }

    container.innerHTML = monitors.map(monitor => {
        const providerName = getFriendlyProviderName(monitor.provider);
        const modelName = getFriendlyModelName(monitor.provider, monitor.model);
        const isRunning = monitor.status === 'running';
        const hasMonitorId = Boolean(monitor.id && !String(monitor.id).startsWith('orphan_'));
        const statusLabel = isRunning ? 'RUNNING' : 'PAUSED';
        const statusClass = isRunning ? 'running' : 'stopped';

        const testControl = isRunning && monitor.id
            ? `<button class="btn btn-primary btn-sm" onclick="testMonitor('${escapeAttr(monitor.agent_name)}', '${escapeAttr(monitor.monitor_type)}')" title="Send Test Message">✏️</button>`
            : '';

        const pauseOrStartControl = hasMonitorId
            ? (isRunning
                ? `<button class="btn btn-secondary btn-sm" title="Pause agent (keeps backlog)" onclick="pauseMonitor('${escapeAttr(monitor.id)}')">⏸ Pause</button>`
                : `<button class="btn btn-primary btn-sm" title="Start fresh (ignore backlog)" onclick="startMonitorFromStatus('${escapeAttr(monitor.id)}', false)">▶️ Start</button>`)
            : '';

        const resumeControl = !isRunning && hasMonitorId
            ? `<button class="btn btn-secondary btn-sm" title="Resume backlog" onclick="startMonitorFromStatus('${escapeAttr(monitor.id)}', true)">⏯ Resume</button>`
            : '';

        const resetControl = monitor.agent_name
            ? `<button class="btn btn-warning btn-sm" ${isRunning ? 'disabled' : ''} title="${isRunning ? 'Pause first to reset backlog' : 'Reset backlog before starting'}" onclick="resetAgent('${escapeAttr(monitor.agent_name)}')">🔄 Reset</button>`
            : '';

        // ALWAYS show kill button - critical for cleaning up orphans
        const killControl = monitor.id
            ? `<button class="btn btn-danger btn-sm" onclick="killMonitor('${escapeAttr(monitor.id)}')" title="Force kill">💀</button>`
            : '';

        const deploymentInfo = monitor.deployment_group ? ` | Group: ${monitor.deployment_group}` : '';
        const promptInfo = monitor.system_prompt_name ? `System Prompt: ${monitor.system_prompt_name}` : 'System Prompt: None';

        return `
        <div class="monitor-card">
            <div class="monitor-top">
                <div class="monitor-name">
                    ${getMonitorEmoji(monitor.monitor_type)} ${monitor.agent_name}
                </div>
                <div class="monitor-controls">
                    <div class="monitor-status ${statusClass}">
                        ${isRunning ? '🟢' : '⏸️'} ${statusLabel}
                    </div>
                    <div class="monitor-actions">
                        ${testControl}
                        ${pauseOrStartControl}
                        ${resumeControl}
                        ${resetControl}
                        ${killControl}
                    </div>
                </div>
            </div>
            <div class="monitor-info">
                <div class="monitor-details">
                    Type: ${monitor.monitor_type} |
                    ${monitor.provider ? `Provider: ${providerName} | ` : ''}
                    ${monitor.model ? `Model: ${modelName}` : ''}
                    ${monitor.uptime_seconds && isRunning ? ` | Uptime: ${formatUptime(monitor.uptime_seconds)}` : ''}
                    <br>
                    ${monitor.environment ? `Environment: ${monitor.environment} | ` : ''}
                    ${monitor.mcp_servers && monitor.mcp_servers.length > 0 ? `Tools: ${monitor.mcp_servers.join(', ')} | ` : ''}
                    ${promptInfo}${deploymentInfo}
                </div>
            </div>
        </div>
    `;
    }).join('');
}

// Helper function to get friendly provider name
function getFriendlyProviderName(providerId) {
    if (!providerId) return 'Unknown';

    const provider = providers.find(p => p.id === providerId);
    if (provider) {
        return provider.name;
    }

    // Fallback to capitalized ID
    return providerId.charAt(0).toUpperCase() + providerId.slice(1);
}

// Helper function to get friendly model name
function getFriendlyModelName(providerId, modelId) {
    if (!modelId) return 'Unknown';

    // Find provider
    const provider = providers.find(p => p.id === providerId);
    if (!provider || !provider.models) {
        return modelId; // Fallback to ID
    }

    // Find model in provider
    const model = provider.models.find(m => m.id === modelId);
    if (model) {
        return model.name;
    }

    // Fallback to ID
    return modelId;
}

function getMonitorEmoji(type) {
    const emojis = {
        'echo': '🔊',
        'ollama': '🤖',
        'langgraph': '🧠',
        'frameworks': '🧩',
        'demo': '🎬'
    };
    return emojis[type] || '📡';
}

function formatUptime(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

// Update log filter dropdown with agent names
function updateLogFilter() {
    const select = document.getElementById('log-filter');
    const currentValue = select.value;

    // Get unique agent names from monitors
    const agentNames = [...new Set(monitors.map(m => m.agent_name))].sort();

    // Build options
    let options = '<option value="all">All Agents</option>';
    agentNames.forEach(name => {
        options += `<option value="${name}">${name}</option>`;
    });

    select.innerHTML = options;

    // Restore previous selection if still valid
    if (currentValue !== 'all' && agentNames.includes(currentValue)) {
        select.value = currentValue;
    } else {
        select.value = 'all';
        logFilter = 'all';
    }
}

// Filter logs based on selected agent
function filterLogs() {
    const container = document.getElementById('logs-container');
    const logLines = container.querySelectorAll('.log-line');

    logLines.forEach(line => {
        const agentName = line.dataset.agent;
        const isVerbose = line.dataset.verbose === 'true';

        // Hide if agent filter doesn't match
        if (logFilter !== 'all' && agentName !== logFilter) {
            line.style.display = 'none';
            return;
        }

        // Hide if verbose log and verbose mode is off
        if (isVerbose && !verboseMode) {
            line.style.display = 'none';
            return;
        }

        // Show the log
        line.style.display = 'block';
    });

    // Auto-scroll after filtering if enabled
    if (autoScroll) {
        container.scrollTop = container.scrollHeight;
    }
}

// Apply verbose mode to all existing logs
function applyVerboseMode() {
    const container = document.getElementById('logs-container');
    const logLines = container.querySelectorAll('.log-line');

    logLines.forEach(line => {
        const isVerbose = line.dataset.verbose === 'true';
        const agentName = line.dataset.agent;

        // Check both agent filter and verbose mode
        const agentMatch = logFilter === 'all' || agentName === logFilter;
        const verboseMatch = verboseMode || !isVerbose;

        if (agentMatch && verboseMatch) {
            line.style.display = 'block';
        } else {
            line.style.display = 'none';
        }
    });

    // Auto-scroll after applying verbose mode if enabled
    if (autoScroll) {
        container.scrollTop = container.scrollHeight;
    }
}

// WebSocket for logs
function initializeWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;

    logsWebSocket = new WebSocket(wsUrl);

    logsWebSocket.onopen = () => {
        console.log('WebSocket connected');
        showNotification('Live logs connected', 'success');
    };

    logsWebSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        appendLog(data);
    };

    logsWebSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        showNotification('Log streaming error', 'error');
    };

    logsWebSocket.onclose = () => {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(initializeWebSocket, 5000);
    };
}

function copyLogs() {
    const container = document.getElementById('logs-container');
    const logLines = container.querySelectorAll('.log-line');

    if (logLines.length === 0) {
        showNotification('No logs to copy', 'error');
        return;
    }

    // Extract text from all log lines
    const logText = Array.from(logLines)
        .map(line => line.textContent)
        .join('\n');

    // Copy to clipboard
    navigator.clipboard.writeText(logText).then(() => {
        showNotification(`Copied ${logLines.length} log lines`, 'success');
    }).catch(err => {
        console.error('Failed to copy logs:', err);
        showNotification('Failed to copy logs', 'error');
    });
}

function refreshLogs() {
    // Clear the logs display
    const container = document.getElementById('logs-container');
    container.innerHTML = '<p class="empty-state">Refreshing logs...</p>';

    // Close existing WebSocket connection
    if (logsWebSocket) {
        logsWebSocket.onclose = null; // Prevent auto-reconnect
        logsWebSocket.close();
    }

    // Reconnect immediately
    setTimeout(() => {
        initializeWebSocket();
        showNotification('Logs refreshed', 'success');
    }, 100);
}

function appendLog(data) {
    const container = document.getElementById('logs-container');

    // Clear empty state if needed
    if (container.querySelector('.empty-state')) {
        container.innerHTML = '';
    }

    if (data.type === 'log') {
        const logLine = document.createElement('div');
        logLine.className = 'log-line';
        logLine.textContent = data.content;

        // Extract agent name from monitor_id
        let agentName = 'unknown';
        const monitorId = data.monitor_id || '';

        // Try to match against known agent names
        // Monitor ID format: agent_name_type_uuid
        if (monitorId) {
            // Find the longest matching agent name from our monitors list
            const matchingAgent = monitors
                .map(m => m.agent_name)
                .filter(name => monitorId.startsWith(name))
                .sort((a, b) => b.length - a.length)[0]; // Longest match first

            if (matchingAgent) {
                agentName = matchingAgent;
            } else {
                // Fallback: parse from format agent_name_type_uuid
                const parts = monitorId.split('_');
                if (parts.length > 2) {
                    // Remove last 2 parts (type and uuid)
                    agentName = parts.slice(0, -2).join('_');
                } else {
                    agentName = monitorId;
                }
            }
        }

        // Store agent name as data attribute
        logLine.dataset.agent = agentName;

        // Detect if this is a verbose log (full response)
        const isVerbose = data.content.includes('💬 RESPONSE:');
        logLine.dataset.verbose = isVerbose.toString();

        // Colorize based on content
        if (data.content.includes('ERROR') || data.content.includes('❌')) {
            logLine.classList.add('error');
        } else if (data.content.includes('✅') || data.content.includes('SUCCESS')) {
            logLine.classList.add('success');
        } else if (isVerbose) {
            logLine.classList.add('verbose');
        }

        // Apply current filters (agent + verbose mode)
        const shouldShow = (logFilter === 'all' || agentName === logFilter) &&
                          (verboseMode || !isVerbose);
        if (!shouldShow) {
            logLine.style.display = 'none';
        }

        container.appendChild(logLine);

        // Limit log lines to prevent infinite growth (keep last 500 lines)
        const MAX_LOG_LINES = 500;
        const logLines = container.querySelectorAll('.log-line');
        if (logLines.length > MAX_LOG_LINES) {
            // Remove oldest log lines
            const toRemove = logLines.length - MAX_LOG_LINES;
            for (let i = 0; i < toRemove; i++) {
                logLines[i].remove();
            }
        }

        // Auto-scroll if enabled (and log is visible)
        if (autoScroll && logLine.style.display !== 'none') {
            container.scrollTop = container.scrollHeight;
        }
    }
}

// Toggle deploy form
function toggleDeployForm() {
    const form = document.getElementById('start-monitor-form');
    const toggle = document.getElementById('deploy-toggle');
    const isCollapsed = form.style.display === 'none';

    if (isCollapsed) {
        form.style.display = 'block';
        toggle.textContent = '▼';
        localStorage.setItem('deployFormCollapsed', 'false');
    } else {
        form.style.display = 'none';
        toggle.textContent = '▶';
        localStorage.setItem('deployFormCollapsed', 'true');
    }
}

// Toggle running agents
function toggleRunningAgents() {
    const list = document.getElementById('monitors-list');
    const toggle = document.getElementById('agents-toggle');
    const isCollapsed = list.style.display === 'none';

    if (isCollapsed) {
        list.style.display = 'block';
        toggle.textContent = '▼';
        localStorage.setItem('runningAgentsCollapsed', 'false');
    } else {
        list.style.display = 'none';
        toggle.textContent = '▶';
        localStorage.setItem('runningAgentsCollapsed', 'true');
    }
}

// Toggle live logs
function toggleLiveLogs() {
    const section = document.getElementById('logs-section');
    const toggle = document.getElementById('logs-toggle');
    const isCollapsed = section.style.display === 'none';

    if (isCollapsed) {
        section.style.display = 'block';
        toggle.textContent = '▼';
        localStorage.setItem('liveLogsCollapsed', 'false');
    } else {
        section.style.display = 'none';
        toggle.textContent = '▶';
        localStorage.setItem('liveLogsCollapsed', 'true');
    }
}

// Restore collapsed states on load
document.addEventListener('DOMContentLoaded', () => {
    // Deploy form
    if (localStorage.getItem('deployFormCollapsed') === 'true') {
        const form = document.getElementById('start-monitor-form');
        const toggle = document.getElementById('deploy-toggle');
        form.style.display = 'none';
        toggle.textContent = '▶';
    }

    // Running agents
    if (localStorage.getItem('runningAgentsCollapsed') === 'true') {
        const list = document.getElementById('monitors-list');
        const toggle = document.getElementById('agents-toggle');
        list.style.display = 'none';
        toggle.textContent = '▶';
    }

    // Live logs
    if (localStorage.getItem('liveLogsCollapsed') === 'true') {
        const section = document.getElementById('logs-section');
        const toggle = document.getElementById('logs-toggle');
        section.style.display = 'none';
        toggle.textContent = '▶';
    }
});

// Toggle Kill Switch (Kill → Resume → Kill)
async function toggleKillSwitch() {
    try {
        // First check current status
        const statusResponse = await fetch(`${API_BASE}/api/kill-switch/status`);
        const statusData = await statusResponse.json();

        if (statusData.active) {
            // Kill switch is active → Deactivate it (Resume)
            const response = await fetch(`${API_BASE}/api/kill-switch/deactivate`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                showNotification(data.message, 'success');
                await updateKillSwitchButton();
            }
        } else {
            // Kill switch is off → Activate it (Kill)
            if (confirm('⚠️ ACTIVATE KILL SWITCH?\n\nThis will:\n- Pause all running agents\n- Stop message processing\n- Agents stay running but idle\n\nPress Kill again to resume.')) {
                const response = await fetch(`${API_BASE}/api/monitors/kill-all`, {
                    method: 'POST'
                });
                const data = await response.json();
                if (data.success) {
                    showNotification(data.message, 'success');
                    await updateKillSwitchButton();
                    await loadMonitors();
                }
            }
        }
    } catch (error) {
        console.error('Failed to toggle kill switch:', error);
        showNotification('Failed to toggle kill switch', 'error');
    }
}

// Update Kill Switch Button State
async function updateKillSwitchButton() {
    try {
        const response = await fetch(`${API_BASE}/api/kill-switch/status`);
        const data = await response.json();

        const killBtn = document.getElementById('kill-btn');
        const killSwitchStatus = document.getElementById('kill-switch-status');

        if (data.active) {
            // Kill switch is ON → Show Resume button
            killBtn.innerHTML = '▶️ Resume';
            killBtn.className = 'btn btn-success';
            killBtn.title = 'Resume all agents (deactivate kill switch)';
            killSwitchStatus.style.display = 'block';
        } else {
            // Kill switch is OFF → Show Kill button
            killBtn.innerHTML = '☠️ Kill';
            killBtn.className = 'btn btn-danger';
            killBtn.title = 'Nuclear option: Kill all monitors + activate kill switch';
            killSwitchStatus.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to check kill switch status:', error);
    }
}

// Notifications
function showNotification(message, type = 'info') {
    // Simple console logging for now
    console.log(`[${type.toUpperCase()}] ${message}`);

    // TODO: Add toast notifications
}
