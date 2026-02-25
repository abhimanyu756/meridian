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
            showFinalResults(event);
            statusDot.classList.remove('running');
            statusText.textContent = 'Complete';
            addLog('Investigation complete \u2014 Overall Risk: ' + event.overall_risk_score + '/10 [' + event.risk_level + ']', 'complete');
            break;

        case 'stream_end':
            break;
    }
}

// ===== Past Investigations History =====

async function loadHistory() {
    var grid = document.getElementById('historyGrid');
    var empty = document.getElementById('historyEmpty');
    try {
        var resp = await fetch(API_URL + '/investigations?size=20');
        var data = await resp.json();

        if (!data.investigations || data.investigations.length === 0) {
            empty.style.display = 'block';
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

            var card = document.createElement('div');
            card.className = 'history-card';
            card.innerHTML =
                '<div class="history-risk-circle ' + level + '">' + score + '</div>' +
                '<div class="history-info">' +
                    '<div class="history-name">' + inv.target_name + '</div>' +
                    '<div class="history-meta">' +
                        '<span>' + date + '</span>' +
                        '<span>' + flags + ' red flags</span>' +
                        '<span class="history-level ' + level + '">' + (inv.risk_level || 'UNKNOWN').toUpperCase() + '</span>' +
                    '</div>' +
                '</div>';
            card.addEventListener('click', function() { loadPastInvestigation(inv); });
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

// Empty input on load
targetInput.value = '';

// Load data on page load
loadHistory();
loadDataStats();
