// MERIDIAN — Frontend Application
const API_URL = window.location.origin;

// DOM elements
const searchForm = document.getElementById('searchForm');
const targetInput = document.getElementById('targetInput');
const searchBtn = document.getElementById('searchBtn');
const resultsSection = document.getElementById('resultsSection');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');

// Track completed agents for progress
let completedAgents = 0;
const TOTAL_AGENTS = 7; // 6 specialist + 1 synthesis

// Agent name -> CSS-friendly ID
function agentId(name) {
    return name.toLowerCase().replace(/ & /g, '-').replace(/ /g, '-');
}

// Color for risk score
function riskColor(score) {
    if (score < 2.5) return 'var(--green)';
    if (score < 5.0) return 'var(--yellow)';
    if (score < 7.5) return 'var(--orange)';
    return 'var(--red)';
}

function riskClass(level) {
    return (level || '').toLowerCase();
}

// Set gauge arc based on score (0-10)
function setGauge(score) {
    const arc = document.getElementById('gaugeArc');
    const maxDash = 251;
    const dashLen = (score / 10) * maxDash;
    arc.setAttribute('stroke-dasharray', `${dashLen} ${maxDash}`);

    const scoreEl = document.getElementById('riskScore');
    let current = 0;
    const step = score / 40;
    const interval = setInterval(() => {
        current += step;
        if (current >= score) {
            current = score;
            clearInterval(interval);
        }
        scoreEl.textContent = current.toFixed(1);
        scoreEl.style.color = riskColor(current);
    }, 25);
}

// Update progress bar
function updateProgress(completed, total, text) {
    const fill = document.getElementById('progressFill');
    const textEl = document.getElementById('progressText');
    const pct = (completed / total) * 100;
    fill.style.width = pct + '%';
    textEl.textContent = text;
}

// Update agent counter
function updateAgentCounter() {
    const counter = document.getElementById('agentsCounter');
    if (counter) {
        const visible = Math.min(completedAgents, 6);
        counter.textContent = visible + ' / 6 complete';
        if (visible === 6) {
            counter.style.color = 'var(--green)';
        }
    }
}

// Add log entry
function addLog(message, type) {
    type = type || '';
    const logEntries = document.getElementById('logEntries');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    entry.innerHTML =
        '<span class="log-time">' + time + '</span>' +
        '<span class="log-event ' + type + '">' + message + '</span>';
    logEntries.prepend(entry);
}

// Reset all agent cards
function resetAgents() {
    completedAgents = 0;
    var agents = ['entity-discovery', 'financial-signal', 'legal-intelligence',
                    'executive-background', 'sentiment-narrative', 'geo-jurisdiction'];
    agents.forEach(function(id) {
        var statusEl = document.getElementById('status-' + id);
        var scoreEl = document.getElementById('score-' + id);
        var findingsEl = document.getElementById('findings-' + id);
        if (statusEl) statusEl.querySelector('.status-indicator').className = 'status-indicator waiting';
        if (scoreEl) { scoreEl.style.width = '0%'; scoreEl.style.background = 'var(--green)'; }
        if (findingsEl) findingsEl.textContent = 'Waiting...';
    });
    document.querySelectorAll('.agent-card').forEach(function(c) { c.className = 'agent-card'; });
    // Reset thoughts
    agents.forEach(function(id) {
        var thoughtEl = document.getElementById('thoughts-' + id);
        if (thoughtEl) { thoughtEl.innerHTML = ''; thoughtEl.classList.remove('active'); }
    });
    document.getElementById('logEntries').innerHTML = '';
    document.getElementById('riskScore').textContent = '--';
    document.getElementById('riskScore').style.color = 'var(--text-primary)';
    document.getElementById('riskBadge').textContent = 'PENDING';
    document.getElementById('riskBadge').className = 'risk-badge';
    document.getElementById('gaugeArc').setAttribute('stroke-dasharray', '0 251');
    document.getElementById('riskRecommendation').style.display = 'none';
    document.getElementById('redFlagsContainer').style.display = 'none';
    document.getElementById('executiveSummary').style.display = 'none';

    // Reset progress
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = 'Starting investigation...';
    document.getElementById('progressContainer').style.display = 'block';

    // Reset agent counter
    var counter = document.getElementById('agentsCounter');
    if (counter) {
        counter.textContent = '0 / 6 complete';
        counter.style.color = '';
    }
}

// Update agent card when agent completes
function updateAgentCard(agentName, data) {
    var id = agentId(agentName);
    var statusEl = document.getElementById('status-' + id);
    var scoreEl = document.getElementById('score-' + id);
    var findingsEl = document.getElementById('findings-' + id);
    var card = findingsEl ? findingsEl.closest('.agent-card') : null;

    if (statusEl) {
        statusEl.querySelector('.status-indicator').className = 'status-indicator complete';
    }
    if (card) card.classList.remove('running');
    if (card) card.classList.add('complete');

    // Hide thoughts on complete
    var thoughtEl = document.getElementById('thoughts-' + id);
    if (thoughtEl) {
        setTimeout(function() { thoughtEl.classList.remove('active'); }, 800);
    }

    if (scoreEl && data.risk_score !== undefined) {
        var pct = (data.risk_score / 10) * 100;
        scoreEl.style.width = pct + '%';
        scoreEl.style.background = riskColor(data.risk_score);
    }

    if (findingsEl && data.findings) {
        var firstPara = data.findings.split('\n\n')[0];
        var html = '<p>' + firstPara + '</p>';

        if (data.red_flags && data.red_flags.length > 0) {
            html += '<div class="agent-red-flags">';
            data.red_flags.slice(0, 3).forEach(function(flag) {
                var short = flag.length > 60 ? flag.substring(0, 57) + '...' : flag;
                html += '<span class="flag-tag">' + short + '</span>';
            });
            html += '</div>';
        }
        findingsEl.innerHTML = html;
    }
}

// Mark agent as running
function markAgentRunning(agentName) {
    var id = agentId(agentName);
    var statusEl = document.getElementById('status-' + id);
    var findingsEl = document.getElementById('findings-' + id);
    var card = findingsEl ? findingsEl.closest('.agent-card') : null;

    if (statusEl) {
        statusEl.querySelector('.status-indicator').className = 'status-indicator running';
    }
    if (card) card.classList.add('running');
}

// Show final results
function showFinalResults(data) {
    // Hide progress
    document.getElementById('progressContainer').style.display = 'none';

    // Risk badge
    var badge = document.getElementById('riskBadge');
    badge.textContent = data.risk_level;
    badge.className = 'risk-badge ' + riskClass(data.risk_level);

    // Gauge
    setGauge(data.overall_risk_score);

    // Recommendation
    var rec = document.getElementById('riskRecommendation');
    var recIcon = document.getElementById('recIcon');
    var recText = document.getElementById('recText');
    var proceed = (data.proceed_recommendation || '').toUpperCase();

    var recMap = {
        'REJECT': { icon: '\u{1F6AB}', text: 'DO NOT PROCEED \u2014 Critical risk identified', cls: 'reject' },
        'INVESTIGATE_FURTHER': { icon: '\u{1F50D}', text: 'INVESTIGATE FURTHER \u2014 Additional due diligence required', cls: 'investigate' },
        'CONDITIONAL': { icon: '\u26A0\uFE0F', text: 'CONDITIONAL APPROVAL \u2014 Proceed with safeguards', cls: 'conditional' },
        'APPROVE': { icon: '\u2705', text: 'APPROVED \u2014 Standard due diligence sufficient', cls: 'approve' },
    };
    var r = recMap[proceed] || recMap['INVESTIGATE_FURTHER'];
    recIcon.textContent = r.icon;
    recText.textContent = r.text;
    rec.className = 'risk-recommendation ' + r.cls;
    rec.style.display = 'flex';

    // Red flags
    if (data.top_red_flags && data.top_red_flags.length > 0) {
        var list = document.getElementById('redFlagsList');
        list.innerHTML = '';
        data.top_red_flags.forEach(function(flag) {
            var li = document.createElement('li');
            li.textContent = flag;
            list.appendChild(li);
        });
        document.getElementById('redFlagsContainer').style.display = 'block';
    }

    // Executive summary
    if (data.executive_summary) {
        var summaryDiv = document.getElementById('summaryContent');
        var paragraphs = data.executive_summary.split('\n\n');
        summaryDiv.innerHTML = paragraphs.map(function(p) { return '<p>' + p + '</p>'; }).join('');

        if (data.recommended_actions && data.recommended_actions.length > 0) {
            var actionsDiv = document.getElementById('recommendedActions');
            actionsDiv.innerHTML = '<h3>Recommended Actions</h3>';
            data.recommended_actions.forEach(function(action) {
                var div = document.createElement('div');
                div.className = 'action-item';
                div.textContent = action;
                actionsDiv.appendChild(div);
            });
        }
        document.getElementById('executiveSummary').style.display = 'block';
    }
}

// Main investigation function
async function runInvestigation(target) {
    resetAgents();
    resultsSection.style.display = 'block';
    document.getElementById('targetName').textContent = target;

    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    statusDot.classList.add('running');
    statusText.textContent = 'Investigating...';
    searchBtn.disabled = true;
    searchBtn.querySelector('.btn-text').style.display = 'none';
    searchBtn.querySelector('.btn-loader').style.display = 'inline';

    addLog('Investigation started: "' + target + '"', 'started');
    updateProgress(0, TOTAL_AGENTS, 'Investigating "' + target + '"...');

    try {
        var response = await fetch(API_URL + '/investigate/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target }),
        });

        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';

        while (true) {
            var result = await reader.read();
            if (result.done) break;

            buffer += decoder.decode(result.value, { stream: true });
            var lines = buffer.split('\n');
            buffer = lines.pop();

            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if (!line.startsWith('data: ')) continue;
                var jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                    var event = JSON.parse(jsonStr);
                    handleEvent(event);
                } catch (e) {
                    // skip malformed events
                }
            }
        }
    } catch (err) {
        addLog('Error: ' + err.message, 'error');
        statusDot.classList.remove('running');
        statusDot.classList.add('error');
        statusText.textContent = 'Error';
        updateProgress(0, 1, 'Error: ' + err.message);
    } finally {
        searchBtn.disabled = false;
        searchBtn.querySelector('.btn-text').style.display = 'inline';
        searchBtn.querySelector('.btn-loader').style.display = 'none';
    }
}

function handleEvent(event) {
    switch (event.event) {
        case 'investigation_started':
            addLog('Investigation ID: ' + event.investigation_id, '');
            updateProgress(0, TOTAL_AGENTS, 'Running Entity Discovery agent...');
            break;

        case 'agent_started':
            markAgentRunning(event.agent);
            addLog('Agent started: ' + event.agent, 'started');
            if (event.agent !== 'Risk Synthesis') {
                updateProgress(completedAgents, TOTAL_AGENTS, 'Running ' + event.agent + ' agent...');
            } else {
                updateProgress(completedAgents, TOTAL_AGENTS, 'Synthesizing risk assessment...');
            }
            break;

        case 'agent_complete':
            completedAgents++;
            if (event.agent === 'Risk Synthesis') {
                addLog('Risk Synthesis complete \u2014 Score: ' + event.risk_score + '/10', 'complete');
                updateProgress(TOTAL_AGENTS, TOTAL_AGENTS, 'Risk synthesis complete. Finalizing report...');
            } else {
                updateAgentCard(event.agent, event);
                updateAgentCounter();
                var scoreStr = event.risk_score !== undefined ? ' (Risk: ' + event.risk_score + '/10)' : '';
                addLog('Agent complete: ' + event.agent + scoreStr, 'complete');
                updateProgress(completedAgents, TOTAL_AGENTS, event.agent + ' complete');
            }
            break;

        case 'investigation_complete':
            _lastInvestigationData = event;
            showFinalResults(event);
            statusDot.classList.remove('running');
            statusText.textContent = 'Complete';
            addLog('Investigation complete \u2014 Overall Risk: ' + event.overall_risk_score + '/10 [' + event.risk_level + ']', 'complete');
            break;

        case 'agent_thinking':
            showAgentThought(event.agent, event.thought);
            break;

        case 'stream_end':
            break;
    }
}

// Streaming agent thought display with typing effect
function showAgentThought(agentName, thought) {
    var id = agentId(agentName);
    var el = document.getElementById('thoughts-' + id);
    if (!el) return;
    el.classList.add('active');
    // Type out the thought character by character
    el.innerHTML = '';
    var i = 0;
    var cursor = document.createElement('span');
    cursor.className = 'cursor';
    el.appendChild(cursor);
    function typeChar() {
        if (i < thought.length) {
            el.insertBefore(document.createTextNode(thought[i]), cursor);
            i++;
            setTimeout(typeChar, 15);
        } else {
            // remove cursor after done
            setTimeout(function() { if (cursor.parentNode) cursor.remove(); }, 1500);
        }
    }
    typeChar();
}

// ===== Past Investigations History =====

var _selectMode = false;
var _selectedIds = new Set();

function toggleSelectMode(on) {
    _selectMode = on;
    _selectedIds.clear();
    document.getElementById('selectModeBtn').style.display = on ? 'none' : 'flex';
    document.getElementById('deleteSelectedBtn').style.display = on ? 'flex' : 'none';
    document.getElementById('cancelSelectBtn').style.display = on ? 'flex' : 'none';
    document.getElementById('selectedCount').textContent = '0';
    loadHistory();
}

function updateSelectedCount() {
    document.getElementById('selectedCount').textContent = _selectedIds.size;
}

document.getElementById('selectModeBtn').addEventListener('click', function() {
    toggleSelectMode(true);
});

document.getElementById('cancelSelectBtn').addEventListener('click', function() {
    toggleSelectMode(false);
});

document.getElementById('deleteSelectedBtn').addEventListener('click', async function() {
    if (_selectedIds.size === 0) return;
    if (!confirm('Delete ' + _selectedIds.size + ' selected investigation(s)?')) return;
    var promises = [];
    _selectedIds.forEach(function(id) {
        promises.push(fetch(API_URL + '/investigations/' + id, { method: 'DELETE' }));
    });
    await Promise.all(promises);
    toggleSelectMode(false);
});

async function loadHistory() {
    var grid = document.getElementById('historyGrid');
    var empty = document.getElementById('historyEmpty');
    try {
        var resp = await fetch(API_URL + '/investigations?size=20');
        var data = await resp.json();

        if (!data.investigations || data.investigations.length === 0) {
            empty.style.display = 'block';
            grid.innerHTML = '';
            grid.appendChild(empty);
            return;
        }
        empty.style.display = 'none';
        grid.innerHTML = '';

        data.investigations.forEach(function(inv) {
            var level = (inv.risk_level || 'LOW').toLowerCase();
            var score = (inv.overall_risk_score || 0).toFixed(1);
            var date = inv.completed_at
                ? new Date(inv.completed_at).toLocaleString()
                : new Date(inv.started_at).toLocaleString();
            var flags = (inv.red_flags || []).length;
            var invId = inv.investigation_id;

            var card = document.createElement('div');
            card.className = 'history-card' + (_selectMode ? ' selectable' : '');

            var checkboxHtml = _selectMode
                ? '<div class="history-checkbox"></div>'
                : '';

            card.innerHTML =
                checkboxHtml +
                '<div class="history-risk-circle ' + level + '">' + score + '</div>' +
                '<div class="history-info">' +
                    '<div class="history-name">' + inv.target_name + '</div>' +
                    '<div class="history-meta">' +
                        '<span>' + date + '</span>' +
                        '<span>' + flags + ' red flags</span>' +
                        '<span class="history-level ' + level + '">' + (inv.risk_level || 'UNKNOWN').toUpperCase() + '</span>' +
                    '</div>' +
                '</div>';

            if (_selectMode) {
                card.addEventListener('click', function() {
                    if (_selectedIds.has(invId)) {
                        _selectedIds.delete(invId);
                        card.classList.remove('selected');
                    } else {
                        _selectedIds.add(invId);
                        card.classList.add('selected');
                    }
                    updateSelectedCount();
                });
            } else {
                card.addEventListener('click', function() { loadPastInvestigation(inv); });
            }
            grid.appendChild(card);
        });
    } catch (err) {
        empty.textContent = 'Failed to load history.';
        empty.style.display = 'block';
    }
}

function loadPastInvestigation(inv) {
    resetAgents();
    resultsSection.style.display = 'block';
    document.getElementById('targetName').textContent = inv.target_name;
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Hide progress for past investigations
    document.getElementById('progressContainer').style.display = 'none';

    // Populate agent cards from stored findings
    var findings = inv.agent_findings || [];
    findings.forEach(function(af) {
        if (af.agent_name === 'Risk Synthesis') return;
        updateAgentCard(af.agent_name, {
            risk_score: af.risk_contribution,
            findings: af.findings,
            red_flags: af.red_flags || [],
        });
        completedAgents++;
    });
    updateAgentCounter();

    var actions = inv.recommended_actions || [];
    if (typeof actions === 'string') {
        try { actions = JSON.parse(actions); } catch (e) { actions = []; }
    }

    var finalData = {
        overall_risk_score: inv.overall_risk_score || 0,
        risk_level: inv.risk_level || 'UNKNOWN',
        executive_summary: inv.summary || '',
        top_red_flags: inv.red_flags || [],
        recommended_actions: actions,
        proceed_recommendation: inv.overall_risk_score >= 7.5 ? 'REJECT'
            : inv.overall_risk_score >= 5.0 ? 'INVESTIGATE_FURTHER'
            : inv.overall_risk_score >= 2.5 ? 'CONDITIONAL' : 'APPROVE',
    };

    _lastInvestigationData = finalData;
    _lastInvestigationData.target = inv.target_name;
    _lastInvestigationData.investigation_id = inv.investigation_id;
    _lastInvestigationData.agent_findings = inv.agent_findings || [];
    showFinalResults(finalData);
    addLog('Loaded past investigation for "' + inv.target_name + '"', 'complete');
}

// ===== Data Stats =====

async function loadDataStats() {
    var indices = [
        { id: 'statEntities', index: 'meridian-entities' },
        { id: 'statFilings', index: 'meridian-filings' },
        { id: 'statLegal', index: 'meridian-legal' },
        { id: 'statNews', index: 'meridian-news' },
        { id: 'statExecs', index: 'meridian-executives' },
    ];

    for (var i = 0; i < indices.length; i++) {
        var item = indices[i];
        try {
            var resp = await fetch(API_URL + '/esql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: 'FROM ' + item.index + ' | STATS count = COUNT(*)' }),
            });
            var data = await resp.json();
            var count = (data && data.values && data.values[0] && data.values[0][0]) || 0;
            var el = document.getElementById(item.id);
            if (el) animateNumber(el, count);
        } catch (e) {
            // silently fail
        }
    }
}

function animateNumber(el, target) {
    var current = 0;
    var step = Math.max(1, Math.ceil(target / 30));
    var interval = setInterval(function() {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(interval);
        }
        el.textContent = current.toLocaleString();
    }, 30);
}

// ===== Download Report =====

var _lastInvestigationData = null;

function generateReportText(data) {
    var lines = [];
    lines.push('='.repeat(70));
    lines.push('MERIDIAN — Corporate Intelligence Report');
    lines.push('='.repeat(70));
    lines.push('');
    lines.push('Target: ' + (data.target || 'Unknown'));
    lines.push('Date: ' + new Date().toISOString().split('T')[0]);
    lines.push('Investigation ID: ' + (data.investigation_id || 'N/A'));
    lines.push('');
    lines.push('-'.repeat(70));
    lines.push('RISK ASSESSMENT');
    lines.push('-'.repeat(70));
    lines.push('Overall Risk Score: ' + (data.overall_risk_score || 0).toFixed(1) + ' / 10');
    lines.push('Risk Level: ' + (data.risk_level || 'UNKNOWN'));
    lines.push('Recommendation: ' + (data.proceed_recommendation || 'N/A'));
    lines.push('');

    if (data.top_red_flags && data.top_red_flags.length > 0) {
        lines.push('-'.repeat(70));
        lines.push('RED FLAGS (' + data.top_red_flags.length + ')');
        lines.push('-'.repeat(70));
        data.top_red_flags.forEach(function(flag, i) {
            lines.push('  ' + (i + 1) + '. ' + flag);
        });
        lines.push('');
    }

    if (data.executive_summary) {
        lines.push('-'.repeat(70));
        lines.push('EXECUTIVE SUMMARY');
        lines.push('-'.repeat(70));
        lines.push(data.executive_summary);
        lines.push('');
    }

    if (data.agent_findings && data.agent_findings.length > 0) {
        lines.push('-'.repeat(70));
        lines.push('AGENT FINDINGS');
        lines.push('-'.repeat(70));
        data.agent_findings.forEach(function(af) {
            lines.push('');
            lines.push('[' + af.agent_name + '] Risk: ' + (af.risk_contribution || 0).toFixed(1) + '/10');
            lines.push(af.findings || 'No findings.');
            if (af.red_flags && af.red_flags.length > 0) {
                lines.push('  Red Flags: ' + af.red_flags.join('; '));
            }
        });
        lines.push('');
    }

    if (data.recommended_actions && data.recommended_actions.length > 0) {
        lines.push('-'.repeat(70));
        lines.push('RECOMMENDED ACTIONS');
        lines.push('-'.repeat(70));
        data.recommended_actions.forEach(function(action, i) {
            lines.push('  ' + (i + 1) + '. ' + action);
        });
        lines.push('');
    }

    lines.push('='.repeat(70));
    lines.push('Generated by MERIDIAN — Multi-Agent Corporate Intelligence Platform');
    lines.push('Powered by Elasticsearch + Gemini AI');
    lines.push('='.repeat(70));

    return lines.join('\n');
}

document.getElementById('downloadReport').addEventListener('click', function() {
    if (!_lastInvestigationData) return;
    var report = generateReportText(_lastInvestigationData);
    var blob = new Blob([report], { type: 'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    var safeName = (_lastInvestigationData.target || 'report').replace(/[^a-zA-Z0-9]/g, '_');
    a.download = 'MERIDIAN_Report_' + safeName + '_' + new Date().toISOString().split('T')[0] + '.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// ===== Clear History =====

document.getElementById('clearHistoryBtn').addEventListener('click', async function() {
    if (!confirm('Delete all past investigations?')) return;
    try {
        await fetch(API_URL + '/investigations', { method: 'DELETE' });
        loadHistory();
    } catch (e) {
        // ignore
    }
});

// ===== Suggestion Chips =====

document.querySelectorAll('.suggestion-chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
        var target = chip.getAttribute('data-target');
        targetInput.value = target;
        runInvestigation(target).then(function() { loadHistory(); });
    });
});

// ===== Event listeners =====

searchForm.addEventListener('submit', function(e) {
    e.preventDefault();
    var target = targetInput.value.trim();
    if (target) {
        runInvestigation(target).then(function() { loadHistory(); });
    }
});

// ===== Compare Mode =====

var _compareMode = false;
var _compareSelected = [];
var _compareInvestigations = [];

document.getElementById('compareModeBtn').addEventListener('click', function() {
    _compareMode = true;
    _compareSelected = [];
    _compareInvestigations = [];
    // Switch history to compare-select mode
    document.getElementById('compareModeBtn').style.display = 'none';
    document.getElementById('cancelSelectBtn').style.display = 'flex';
    document.getElementById('selectModeBtn').style.display = 'none';
    loadHistoryForCompare();
});

document.getElementById('closeCompare').addEventListener('click', function() {
    document.getElementById('compareSection').style.display = 'none';
    _compareMode = false;
    _compareSelected = [];
    document.getElementById('compareModeBtn').style.display = 'flex';
    document.getElementById('cancelSelectBtn').style.display = 'none';
    document.getElementById('selectModeBtn').style.display = 'flex';
    loadHistory();
});

// Override cancel to also handle compare mode
var origCancelHandler = document.getElementById('cancelSelectBtn').onclick;
document.getElementById('cancelSelectBtn').addEventListener('click', function() {
    if (_compareMode) {
        _compareMode = false;
        _compareSelected = [];
        document.getElementById('compareModeBtn').style.display = 'flex';
        document.getElementById('cancelSelectBtn').style.display = 'none';
        document.getElementById('selectModeBtn').style.display = 'flex';
        loadHistory();
    }
});

async function loadHistoryForCompare() {
    var grid = document.getElementById('historyGrid');
    var empty = document.getElementById('historyEmpty');
    try {
        var resp = await fetch(API_URL + '/investigations?size=20');
        var data = await resp.json();
        if (!data.investigations || data.investigations.length < 2) {
            alert('Need at least 2 investigations to compare.');
            _compareMode = false;
            document.getElementById('compareModeBtn').style.display = 'flex';
            document.getElementById('cancelSelectBtn').style.display = 'none';
            document.getElementById('selectModeBtn').style.display = 'flex';
            return;
        }
        grid.innerHTML = '';
        empty.style.display = 'none';
        _compareInvestigations = data.investigations;

        data.investigations.forEach(function(inv, idx) {
            var level = (inv.risk_level || 'LOW').toLowerCase();
            var score = (inv.overall_risk_score || 0).toFixed(1);
            var card = document.createElement('div');
            card.className = 'history-card selectable';
            card.innerHTML =
                '<div class="history-checkbox"></div>' +
                '<div class="history-risk-circle ' + level + '">' + score + '</div>' +
                '<div class="history-info">' +
                    '<div class="history-name">' + inv.target_name + '</div>' +
                    '<div class="history-meta">' +
                        '<span class="history-level ' + level + '">' + (inv.risk_level || 'UNKNOWN') + '</span>' +
                        '<span>Select to compare</span>' +
                    '</div>' +
                '</div>';

            card.addEventListener('click', function() {
                var alreadyIdx = _compareSelected.indexOf(idx);
                if (alreadyIdx !== -1) {
                    _compareSelected.splice(alreadyIdx, 1);
                    card.classList.remove('selected');
                } else if (_compareSelected.length < 2) {
                    _compareSelected.push(idx);
                    card.classList.add('selected');
                }
                if (_compareSelected.length === 2) {
                    showComparison(
                        _compareInvestigations[_compareSelected[0]],
                        _compareInvestigations[_compareSelected[1]]
                    );
                }
            });
            grid.appendChild(card);
        });
    } catch (e) {
        // ignore
    }
}

function showComparison(invA, invB) {
    document.getElementById('compareSection').style.display = 'block';
    renderCompareCard('compareLeft', invA);
    renderCompareCard('compareRight', invB);
    document.getElementById('compareSection').scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Reset compare select
    _compareMode = false;
    document.getElementById('compareModeBtn').style.display = 'flex';
    document.getElementById('cancelSelectBtn').style.display = 'none';
    document.getElementById('selectModeBtn').style.display = 'flex';
    loadHistory();
}

function renderCompareCard(containerId, inv) {
    var el = document.getElementById(containerId);
    var score = (inv.overall_risk_score || 0).toFixed(1);
    var level = (inv.risk_level || 'LOW').toLowerCase();
    var findings = inv.agent_findings || [];

    var html = '<div class="compare-company-name">' + inv.target_name + '</div>';
    html += '<div class="compare-risk-row">';
    html += '<span class="compare-risk-score" style="color:' + riskColor(inv.overall_risk_score || 0) + '">' + score + '</span>';
    html += '<span class="risk-badge ' + level + '">' + (inv.risk_level || 'UNKNOWN') + '</span>';
    html += '</div>';

    // Agent breakdown
    html += '<div class="compare-agents">';
    findings.forEach(function(af) {
        if (af.agent_name === 'Risk Synthesis') return;
        var agentScore = (af.risk_contribution || 0).toFixed(1);
        html += '<div class="compare-agent-row">';
        html += '<span class="compare-agent-name">' + af.agent_name + '</span>';
        html += '<span class="compare-agent-score" style="color:' + riskColor(af.risk_contribution || 0) + '">' + agentScore + '/10</span>';
        html += '</div>';
    });
    html += '</div>';

    // Red flags
    var flags = inv.red_flags || [];
    if (flags.length > 0) {
        html += '<div class="compare-flags">';
        html += '<h4>Red Flags (' + flags.length + ')</h4>';
        flags.slice(0, 5).forEach(function(flag) {
            html += '<div class="compare-flag-item">' + flag + '</div>';
        });
        html += '</div>';
    }

    el.innerHTML = html;
}

// ===== Corporate Network Graph =====

function renderNetworkGraph(entityFinding) {
    var container = document.getElementById('networkGraph');
    if (!container) return;

    var raw = entityFinding.raw_data || entityFinding;
    var primary = raw.primary_entity || {};
    var subs = raw.subsidiaries || [];
    var related = raw.related_entities || [];

    if (!primary.name && subs.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    var nodes = [];
    var edges = [];

    // Add primary entity
    var primaryName = primary.name || 'Unknown';
    nodes.push({ id: 'primary', label: primaryName, type: 'primary', jurisdiction: primary.jurisdiction || '' });

    // Add subsidiaries
    subs.forEach(function(sub, i) {
        var subName = sub.name || sub.entity_name || ('Sub ' + (i + 1));
        var nodeId = 'sub-' + i;
        nodes.push({ id: nodeId, label: subName, type: 'subsidiary', jurisdiction: sub.jurisdiction || '' });
        edges.push({ from: 'primary', to: nodeId });
    });

    // Add related entities
    related.forEach(function(rel, i) {
        var relName = rel.name || rel.entity_name || ('Related ' + (i + 1));
        var nodeId = 'rel-' + i;
        nodes.push({ id: nodeId, label: relName, type: 'related', jurisdiction: rel.jurisdiction || '' });
        edges.push({ from: 'primary', to: nodeId });
    });

    // If only primary node, add placeholder
    if (nodes.length === 1) {
        container.innerHTML = '<div class="network-empty">No subsidiaries or related entities found in data.</div>';
        return;
    }

    // Layout: primary center, children in circle
    var width = container.clientWidth || 700;
    var height = Math.max(320, nodes.length * 30);
    var cx = width / 2;
    var cy = height / 2;
    var radius = Math.min(width, height) * 0.35;

    // Position nodes
    nodes[0].x = cx;
    nodes[0].y = cy;
    var childNodes = nodes.slice(1);
    childNodes.forEach(function(n, i) {
        var angle = (2 * Math.PI * i) / childNodes.length - Math.PI / 2;
        n.x = cx + radius * Math.cos(angle);
        n.y = cy + radius * Math.sin(angle);
    });

    // Build SVG
    var svg = '<svg width="' + width + '" height="' + height + '" viewBox="0 0 ' + width + ' ' + height + '">';

    // Draw edges
    edges.forEach(function(e) {
        var from = nodes.find(function(n) { return n.id === e.from; });
        var to = nodes.find(function(n) { return n.id === e.to; });
        if (from && to) {
            svg += '<line x1="' + from.x + '" y1="' + from.y + '" x2="' + to.x + '" y2="' + to.y + '" stroke="rgba(99,102,241,0.3)" stroke-width="1.5" stroke-dasharray="4,4"/>';
        }
    });

    // Draw nodes
    nodes.forEach(function(n) {
        var r = n.type === 'primary' ? 32 : 22;
        var fill = n.type === 'primary' ? 'rgba(99,102,241,0.15)' :
                   n.type === 'subsidiary' ? 'rgba(6,182,212,0.1)' : 'rgba(234,179,8,0.1)';
        var stroke = n.type === 'primary' ? '#6366f1' :
                     n.type === 'subsidiary' ? '#06b6d4' : '#eab308';
        svg += '<circle cx="' + n.x + '" cy="' + n.y + '" r="' + r + '" fill="' + fill + '" stroke="' + stroke + '" stroke-width="2"/>';

        // Label
        var label = n.label.length > 18 ? n.label.substring(0, 16) + '...' : n.label;
        var fontSize = n.type === 'primary' ? 11 : 9;
        svg += '<text x="' + n.x + '" y="' + (n.y + r + 14) + '" text-anchor="middle" fill="#94a3b8" font-size="' + fontSize + '" font-family="Inter,sans-serif" font-weight="600">' + label + '</text>';

        // Jurisdiction tag
        if (n.jurisdiction) {
            var jurLabel = n.jurisdiction.length > 12 ? n.jurisdiction.substring(0, 10) + '..' : n.jurisdiction;
            svg += '<text x="' + n.x + '" y="' + (n.y + r + 26) + '" text-anchor="middle" fill="#64748b" font-size="8" font-family="JetBrains Mono,monospace">' + jurLabel + '</text>';
        }

        // Type icon in node
        var icon = n.type === 'primary' ? 'HQ' : n.type === 'subsidiary' ? 'SUB' : 'REL';
        svg += '<text x="' + n.x + '" y="' + (n.y + 4) + '" text-anchor="middle" fill="' + stroke + '" font-size="' + (n.type === 'primary' ? 10 : 8) + '" font-family="JetBrains Mono,monospace" font-weight="700">' + icon + '</text>';
    });

    svg += '</svg>';

    // Legend
    var legend = '<div class="network-legend">' +
        '<span class="legend-item"><span class="legend-dot" style="background:#6366f1"></span>Headquarters</span>' +
        '<span class="legend-item"><span class="legend-dot" style="background:#06b6d4"></span>Subsidiary</span>' +
        '<span class="legend-item"><span class="legend-dot" style="background:#eab308"></span>Related</span>' +
        '</div>';

    container.innerHTML = legend + '<div class="network-svg-wrap">' + svg + '</div>';
}

// ===== Real-time News Monitor =====

var _newsWatchInterval = null;
var _newsWatchTarget = null;
var _lastNewsCount = 0;

function startNewsWatch(target) {
    stopNewsWatch();
    _newsWatchTarget = target;
    _lastNewsCount = 0;
    var watchPanel = document.getElementById('newsWatchPanel');
    if (watchPanel) {
        watchPanel.style.display = 'block';
        document.getElementById('watchTarget').textContent = target;
        document.getElementById('watchStatus').textContent = 'Monitoring...';
        document.getElementById('watchStatus').className = 'watch-status active';
        document.getElementById('newsAlerts').innerHTML = '';
    }

    // Initial check
    checkForNews(target);

    // Poll every 30 seconds
    _newsWatchInterval = setInterval(function() {
        checkForNews(target);
    }, 30000);
}

function stopNewsWatch() {
    if (_newsWatchInterval) {
        clearInterval(_newsWatchInterval);
        _newsWatchInterval = null;
    }
    _newsWatchTarget = null;
    var watchPanel = document.getElementById('newsWatchPanel');
    if (watchPanel) {
        document.getElementById('watchStatus').textContent = 'Stopped';
        document.getElementById('watchStatus').className = 'watch-status stopped';
    }
}

async function checkForNews(target) {
    try {
        var escapedTarget = target.replace(/"/g, '\\"');
        var query = 'FROM meridian-news | WHERE entity_names LIKE "*' + escapedTarget + '*" | STATS total = COUNT(*), neg = SUM(CASE(sentiment_label == "negative", 1, 0)), recent = SUM(CASE(published_at >= NOW() - 7 days, 1, 0))';
        var resp = await fetch(API_URL + '/esql', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query }),
        });
        var data = await resp.json();
        var values = (data && data.values && data.values[0]) || [0, 0, 0];
        var total = values[0] || 0;
        var neg = values[1] || 0;
        var recent = values[2] || 0;

        var alertsEl = document.getElementById('newsAlerts');
        if (!alertsEl) return;

        // Update watch stats
        document.getElementById('watchTotal').textContent = total;
        document.getElementById('watchRecent').textContent = recent;
        document.getElementById('watchNegative').textContent = neg;

        // Check for new articles since last check
        if (_lastNewsCount > 0 && total > _lastNewsCount) {
            var diff = total - _lastNewsCount;
            var alertDiv = document.createElement('div');
            alertDiv.className = 'news-alert';
            var time = new Date().toLocaleTimeString('en-US', { hour12: false });
            alertDiv.innerHTML = '<span class="alert-time">' + time + '</span><span class="alert-text">' + diff + ' new article(s) detected for ' + target + '</span>';
            alertsEl.prepend(alertDiv);
        }

        _lastNewsCount = total;
        document.getElementById('watchLastCheck').textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
    } catch (e) {
        // silently continue
    }
}

// Watch button handler
document.addEventListener('click', function(e) {
    if (e.target.id === 'startWatchBtn' || e.target.closest('#startWatchBtn')) {
        var target = document.getElementById('targetName').textContent;
        if (target) startNewsWatch(target);
    }
    if (e.target.id === 'stopWatchBtn' || e.target.closest('#stopWatchBtn')) {
        stopNewsWatch();
    }
});

// Hook into investigation complete to show network graph
var _origShowFinalResults = showFinalResults;
showFinalResults = function(data) {
    _origShowFinalResults(data);

    // Show network graph if entity findings available
    if (data.agent_findings) {
        var entityF = data.agent_findings.find(function(f) { return f.agent_name === 'Entity Discovery'; });
        if (entityF) {
            renderNetworkGraph(entityF);
        }
    }
};

// Empty input on load
targetInput.value = '';

// Load data on page load
loadHistory();
loadDataStats();
