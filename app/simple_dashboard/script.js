const API_BASE = "http://127.0.0.1:8000";

// --- Tab Switching Logic (Quick Launch) ---
function showScanner(scannerId) {
    // Hide all scanner cards
    document.querySelectorAll('.result-card').forEach(card => {
        card.classList.remove('active');
    });

    // Show selected scanner card
    const selectedCard = document.getElementById(scannerId + '-card');
    if (selectedCard) {
        selectedCard.classList.add('active');
        // Scroll to it
        selectedCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Update active state in sidebar/quick launch if needed
    // (Optional visual feedback)
}

// --- Helper: Status Badge Generator ---
function getStatusBadge(score, status) {
    if (status === "THREAT" || score >= 60) {
        return `<span class="badge badge-danger"><i class="fas fa-exclamation-triangle"></i> THREAT (${score})</span>`;
    } else if (score >= 40) {
        return `<span class="badge" style="background-color: var(--warning); color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;"><i class="fas fa-exclamation-circle"></i> WARNING (${score})</span>`;
    }
    return `<span class="badge badge-safe"><i class="fas fa-check-circle"></i> SAFE (${score})</span>`;
}

function getAlertBadges(alerts, score = 100) {
    if (!alerts || alerts.length === 0) return '';
    let color = "var(--danger)"; // Default red for THREAT
    if (score < 40) color = "var(--success)"; // Greenish var(--success) for safe 
    else if (score < 60) color = "var(--warning)"; // Yellow for warning

    return alerts.map(a => `<div style="margin-top:5px; font-size:0.85rem;"><span style="color:${color}; font-weight:bold;">•</span> <span style="color:var(--text-main);">${a}</span></div>`).join('');
}

// --- API Interactions ---

// 1. Text Analysis
async function analyzeText() {
    const text = document.getElementById("textInput").value;
    const type = document.getElementById("textType").value;
    const resultBox = document.getElementById("textResult");

    if (!text) {
        resultBox.innerHTML = '<span style="color:var(--text-muted)">Please enter text to analyze.</span>';
        return;
    }

    resultBox.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Analyzing...';

    try {
        const res = await fetch(`${API_BASE}/api/v1/text/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, check_type: type })
        });
        const data = await res.json();

        resultBox.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <strong>Result:</strong>
                ${getStatusBadge(data.risk_score, data.status)}
            </div>
            ${getAlertBadges(data.alerts, data.risk_score)}
            <div style="margin-top:10px; font-size:0.8rem; color:var(--text-muted)">
                Analysis Complete.
            </div>
        `;
        fetchHistory(); // Refresh logs
    } catch (e) {
        resultBox.innerHTML = `<span style="color:var(--danger)">Error: ${e.message}</span>`;
    }
}

// 2. Web Scan
async function scanWeb() {
    const url = document.getElementById("urlInput").value;
    const resultBox = document.getElementById("webResult");
    const reasonBox = document.getElementById("webReason");

    if (!url) {
        resultBox.innerHTML = '<span style="color:var(--text-muted)">Please enter a URL.</span>';
        if (reasonBox) reasonBox.style.display = 'none';
        return;
    }

    resultBox.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Scanning URL...';
    if (reasonBox) reasonBox.style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/api/v1/web/scan`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: url, feature: "all" })
        });
        const data = await res.json();
        const isThreat = data.risk_score > 50;

        resultBox.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong>Verdict:</strong>
                ${getStatusBadge(data.risk_score, isThreat ? "THREAT" : "SAFE")}
            </div>
        `;

        if (data.alerts && data.alerts.length > 0) {
            if (reasonBox) {
                reasonBox.style.display = 'block';
                reasonBox.innerHTML = `<strong style="color: var(--text-main);">Reasons for Verdict:</strong> ${getAlertBadges(data.alerts, data.risk_score)}`;
            }
        }

        fetchHistory();
    } catch (e) {
        resultBox.innerHTML = `<span style="color:var(--danger)">Error: ${e.message}</span>`;
    }
}

function toggleNetwork() {
    const isChecked = document.getElementById("networkToggle").checked;
    const networkLabel = document.getElementById("networkLabel");
    const networkIcon = document.getElementById("networkIcon");

    if (isChecked) {
        networkLabel.innerText = "Network Access: ENABLED";
        networkLabel.style.color = "var(--danger)";
        networkIcon.style.color = "var(--danger)";
    } else {
        networkLabel.innerText = "Network Access: DISABLED";
        networkLabel.style.color = "var(--text-main)";
        networkIcon.style.color = "var(--text-muted)";
    }
}

// 3. File Scan
async function scanFile() {
    const fileInput = document.getElementById("fileInput");
    const resultBox = document.getElementById("fileResult");
    const networkToggle = document.getElementById("networkToggle");

    if (fileInput.files.length === 0) {
        resultBox.innerHTML = '<span style="color:var(--text-muted)">Please select a file.</span>';
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    if (networkToggle) {
        formData.append("enable_network", networkToggle.checked);
    }

    resultBox.innerHTML = `
        <div style="margin-bottom: 10px;">
            <i class="fas fa-flask fa-spin" style="color: #8a2be2"></i> 
            <strong style="color: #8a2be2;">Sending file to isolated Sandbox...</strong>
        </div>
        <div style="width: 100%; background-color: var(--border-color); border-radius: 4px; overflow: hidden; height: 6px; position: relative;">
            <div style="position: absolute; left: 0; top: 0; bottom: 0; width: 30%; background-color: #8a2be2; animation: loading-bar 1.5s infinite ease-in-out; border-radius: 4px;"></div>
        </div>
        <style>@keyframes loading-bar { 0% { left: -30%; } 100% { left: 100%; } }</style>
    `;

    try {
        const res = await fetch(`${API_BASE}/api/v1/file/scan-file`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        resultBox.innerHTML = `
             <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <strong>Sandbox Verdict:</strong>
                ${getStatusBadge(data.risk_score, data.is_safe ? "SAFE" : "THREAT")}
            </div>
            ${getAlertBadges(data.alerts, data.risk_score)}
        `;
        fetchHistory();
    } catch (e) {
        resultBox.innerHTML = `<span style="color:var(--danger)">Sandbox Error: ${e.message}</span>`;
    }
}

// 3b. Email Scan
async function scanEmail() {
    const fileInput = document.getElementById("emailInput");
    const resultBox = document.getElementById("emailResult");

    if (fileInput.files.length === 0) {
        resultBox.innerHTML = '<span style="color:var(--text-muted)">Please select an .eml file.</span>';
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    resultBox.innerHTML = `
        <div style="margin-bottom: 10px;">
            <i class="fas fa-envelope-open fa-spin" style="color: #ff6b6b"></i> 
            <strong style="color: #ff6b6b;">Parsing email and routing components to AI Guards...</strong>
        </div>
        <div style="width: 100%; background-color: var(--border-color); border-radius: 4px; overflow: hidden; height: 6px; position: relative;">
            <div style="position: absolute; left: 0; top: 0; bottom: 0; width: 30%; background-color: #ff6b6b; animation: loading-bar 1.5s infinite ease-in-out; border-radius: 4px;"></div>
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/api/v1/email-sandbox/analyze`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (!data.success) {
            resultBox.innerHTML = `<span style="color:var(--danger)">Error: ${data.error}</span>`;
            return;
        }

        const analysis = data.analysis;

        // Generate Threat Report HTML from the sections
        let threatReportHtml = "";
        if (Object.keys(analysis.threat_report).length > 0) {
            threatReportHtml = `<div style="margin-top: 15px; padding: 12px; border-left: 4px solid var(--danger); background: var(--input-bg); border-radius: 4px; font-size: 0.9rem;">
                <strong style="color: var(--danger)"><i class="fas fa-shield-virus"></i> Detailed Threat Report:</strong>
                <ul style="margin-top: 8px; padding-left: 20px;">`;

            for (const [key, report] of Object.entries(analysis.threat_report)) {
                threatReportHtml += `<li><strong>${key.replace('_', ' ').toUpperCase()}</strong>: ${report.reason}
                    <ul style="color:var(--text-muted); font-size: 0.8rem;">`;
                report.alerts.forEach(a => {
                    threatReportHtml += `<li>${a}</li>`;
                });
                threatReportHtml += `</ul></li>`;
            }
            threatReportHtml += `</ul></div>`;
        } else {
            threatReportHtml = `<div style="margin-top: 10px; color: var(--success); font-size: 0.9rem;">
                <i class="fas fa-check-circle"></i> No threats found in any component.
             </div>`;
        }

        resultBox.innerHTML = `
             <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <strong>Sandbox Verdict:</strong>
                ${getStatusBadge(analysis.final_score, analysis.status)}
            </div>
            <div style="margin-bottom: 10px; font-size: 0.9rem;">
                <strong>Subject:</strong> ${analysis.email_subject || 'N/A'}
            </div>
            ${getAlertBadges(analysis.alerts, analysis.final_score)}
            ${threatReportHtml}
        `;
        fetchHistory();
    } catch (e) {
        resultBox.innerHTML = `<span style="color:var(--danger)">Sandbox Error: ${e.message}</span>`;
    }
}

// 4. Audio Scan
async function scanAudio() {
    const fileInput = document.getElementById("audioInput");
    const resultBox = document.getElementById("audioResult");

    if (fileInput.files.length === 0) {
        resultBox.innerHTML = '<span style="color:var(--text-muted)">Please select an audio file.</span>';
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    resultBox.innerHTML = `
        <div style="margin-bottom: 10px;">
            <i class="fas fa-flask fa-spin" style="color: #8957e5"></i> 
            <strong style="color: #8957e5;">Opening audio in isolated Sandbox...</strong>
        </div>
        <div style="width: 100%; background-color: var(--border-color); border-radius: 4px; overflow: hidden; height: 6px; position: relative;">
            <div style="position: absolute; left: 0; top: 0; bottom: 0; width: 30%; background-color: #8957e5; animation: loading-bar 1.5s infinite ease-in-out; border-radius: 4px;"></div>
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/api/v1/audio/detect-voice`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        resultBox.innerHTML = `
             <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <strong>Sandbox Verdict:</strong>
                ${getStatusBadge(data.risk_score, data.is_deepfake ? "THREAT" : "SAFE")}
            </div>
            ${getAlertBadges(data.alerts, data.risk_score)}
        `;
        fetchHistory();
    } catch (e) {
        resultBox.innerHTML = `<span style="color:var(--danger)">Sandbox Error: ${e.message}</span>`;
    }
}



// 6. Secure Chat Interceptor
function toggleShield() {
    const isChecked = document.getElementById("shieldToggle").checked;
    const shieldLabel = document.getElementById("shieldLabel");
    const shieldIcon = document.getElementById("shieldIcon");
    const chatWindow = document.getElementById("chatWindow");

    if (isChecked) {
        shieldLabel.innerText = "GenAI Shield: ACTIVE";
        shieldLabel.style.color = "var(--primary)";
        shieldIcon.style.color = "var(--primary)";
        chatWindow.style.borderColor = "var(--primary)";
    } else {
        shieldLabel.innerText = "GenAI Shield: BYPASSED";
        shieldLabel.style.color = "var(--danger)";
        shieldIcon.style.color = "var(--danger)";
        chatWindow.style.borderColor = "var(--danger)";
    }
}

async function sendSecureChat() {
    const inputField = document.getElementById("chatInput");
    const chatWindow = document.getElementById("chatWindow");
    const message = inputField.value.trim();

    if (!message) return;

    // Add user message to UI
    chatWindow.innerHTML += `
        <div style="align-self: flex-end; background: var(--primary); color: white; padding: 12px 16px; border-radius: 12px; max-width: 80%; line-height:1.5;">
            ${message}
        </div>
    `;
    inputField.value = "";
    chatWindow.scrollTop = chatWindow.scrollHeight;

    // Read shield state
    const shieldEnabled = document.getElementById("shieldToggle").checked;

    // Add loading indicator
    const loadingId = "msg-" + Date.now();

    if (shieldEnabled) {
        chatWindow.innerHTML += `
            <div id="${loadingId}" style="align-self: flex-start; background: var(--input-bg); padding: 12px 16px; border-radius: 12px; color: var(--text-muted); font-style: italic;">
                <i class="fas fa-shield-alt fa-flip" style="color:var(--primary)"></i> Guard Interceptor Analyzing...
            </div>
        `;
    } else {
        chatWindow.innerHTML += `
            <div id="${loadingId}" style="align-self: flex-start; background: var(--input-bg); padding: 12px 16px; border-radius: 12px; color: var(--danger); font-style: italic;">
                <i class="fas fa-unlock-alt" style="color:var(--danger)"></i> Shield Bypassed, connecting to Bot...
            </div>
        `;
    }
    chatWindow.scrollTop = chatWindow.scrollHeight;

    try {
        const res = await fetch(`${API_BASE}/api/v1/secure-chat/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message, shield_enabled: shieldEnabled })
        });
        const data = await res.json();

        document.getElementById(loadingId).remove();

        if (data.status === "BLOCKED") {
            // Display Blocked Message
            chatWindow.innerHTML += `
                <div style="align-self: center; background: #fff1f0; border: 1px solid #ffccc7; color: var(--danger); padding: 10px 15px; border-radius: 8px; width: 100%; text-align: center; font-weight: 600; font-size: 0.9rem; margin: 10px 0;">
                    <i class="fas fa-hand-paper"></i> [BLOCKED BY GENAI GUARD]
                    <div style="font-weight: normal; font-size: 0.8rem; margin-top:5px; color: var(--text-main);">
                        ${data.reason.join(" | ")}
                    </div>
                </div>
            `;
        } else {
            // Display AI Response
            chatWindow.innerHTML += `
                <div style="align-self: flex-start; background: #fff; padding: 12px 16px; border-radius: 12px; border: 1px solid var(--border-color); max-width: 80%; line-height:1.5;">
                    <i class="fas fa-robot" style="color: var(--success); margin-right: 5px;"></i> 
                    ${data.response}
                </div>
            `;
        }
        chatWindow.scrollTop = chatWindow.scrollHeight;
        fetchHistory();

    } catch (e) {
        document.getElementById(loadingId).remove();
        chatWindow.innerHTML += `
            <div style="align-self: flex-start; background: #fff1f0; color: var(--danger); padding: 12px 16px; border-radius: 12px; max-width: 80%;">
                Error connecting to guard interceptor: ${e.message}
            </div>
        `;
    }
}

// --- History & Stats ---

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/history`);
        const data = await res.json();
        updateStats(data);
        renderAlerts(data);
    } catch (e) {
        console.log("Error fetching history:", e);
    }
}

async function fetchGmailHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/history/gmail`);
        const data = await res.json();
        renderGmailStream(data);
    } catch (e) {
        console.log("Error fetching gmail history:", e);
    }
}

function updateStats(data) {
    // Calculate simple stats from the ephemeral log for demo purposes
    // specific counters will reset on server restart, but that's expected
    const totalScans = data.length;
    const threats = data.filter(item => item.status === 'THREAT').length;

    document.getElementById('stat-total-scans').innerText = totalScans;
    document.getElementById('stat-threats').innerText = threats;
}

function renderAlerts(data) {
    const container = document.getElementById('alertsList');
    if (data.length === 0) {
        container.innerHTML = '<div class="alert-item" style="text-align:center;">No recent alerts</div>';
        return;
    }

    // Show last 10
    const recent = data.slice().reverse().slice(0, 10);

    const html = recent.map(item => {
        const isThreat = item.status === 'THREAT';
        const color = isThreat ? 'var(--danger)' : 'var(--success)';
        const icon = isThreat ? 'exclamation-triangle' : 'check-circle';

        return `
        <div class="alert-item" style="border-left: 3px solid ${color}">
            <div class="alert-header">
                <span class="alert-module" style="color:${color}">${item.module}</span>
                <span class="alert-time">${item.timestamp.split(' ')[1]}</span>
            </div>
            <div style="font-size:0.9rem; margin-top:4px;">
                ${item.input_type || 'Scan Request'}
            </div>
            ${item.alerts.length > 0 ? `<div style="color:var(--text-muted); font-size:0.8rem; margin-top:4px;">${item.alerts[0]}</div>` : ''}
        </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function renderGmailStream(data) {
    const container = document.getElementById('gmailStreamFeed');
    if (!container) return;

    const streamData = data.filter(item => item.module === "Gmail Streamer");

    if (streamData.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 20px;">Waiting for incoming emails... <i class="fas fa-circle-notch fa-spin"></i></div>';
        return;
    }

    const html = streamData.map(item => {
        const isThreat = item.risk_score > 50;
        const color = isThreat ? 'var(--danger)' : 'var(--success)';
        const bg = isThreat ? 'rgba(255, 71, 87, 0.1)' : 'rgba(46, 213, 115, 0.1)';

        let threatReportHtml = "";
        if (item.threat_report && Object.keys(item.threat_report).length > 0) {
            threatReportHtml = `<div style="display: flex; flex-direction: column; height: auto; width: 100%; box-sizing: border-box; margin-top: 15px; padding: 12px; background: var(--bg-panel); border: 1px solid var(--border-color); border-left: 4px solid ${color}; border-radius: 4px; font-size: 0.85rem;">
                <strong style="color: var(--text-main)"><i class="fas fa-microscope" style="color: ${color}"></i> AI Guard Analysis:</strong>
                <ul style="margin-top: 8px; padding-left: 20px; margin-bottom: 0;">`;

            for (const [guard, report] of Object.entries(item.threat_report)) {
                threatReportHtml += `<li style="margin-bottom: 5px; color: var(--text-main);"><strong>${guard.replace('_', ' ').toUpperCase()}</strong>: ${report.reason}
                    <ul style="color:var(--text-muted); font-size: 0.8rem;">`;
                if (report.alerts) {
                    report.alerts.forEach(a => {
                        threatReportHtml += `<li>${a}</li>`;
                    });
                }
                threatReportHtml += `</ul></li>`;
            }
            threatReportHtml += `</ul></div>`;
        }

        return `
        <div style="flex-shrink: 0; min-height: min-content; border: 1px solid var(--border-color); border-radius: 8px; padding: 15px; background: ${bg}; position: relative; overflow: hidden; margin-bottom: 15px;">
            <div style="position: absolute; top:0; left:0; width: 4px; height: 100%; background: ${color};"></div>
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                <div>
                    <h4 style="margin: 0; color: var(--text-main); font-size: 1rem;"><i class="fas fa-envelope"></i> ${item.input_type || 'Incoming Email'}</h4>
                    <span style="font-size: 0.8rem; color: var(--text-muted);"><i class="far fa-clock"></i> ${item.timestamp}</span>
                </div>
                ${getStatusBadge(item.risk_score, isThreat ? "THREAT" : "SAFE")}
            </div>
            ${item.alerts && item.alerts.length > 0 ? getAlertBadges(item.alerts, item.risk_score) : ''}
            ${threatReportHtml}
        </div>
        `;
    }).join('');

    container.innerHTML = html;
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    fetchHistory();
    fetchGmailHistory(); // Initial fetch
    setInterval(fetchHistory, 3000);
    setInterval(fetchGmailHistory, 3000); // Dedicated heartbeat for Gmail stream

    // Default show Text scanner
    showScanner('text');
});
