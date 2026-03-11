// 初期化
document.addEventListener('DOMContentLoaded', () => {
    loadHealthStatus();
    setInterval(loadHealthStatus, 5000); // 5秒ごと
});

// ヘルスステータス取得
async function loadHealthStatus() {
    try {
        const res = await fetch('/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        updateConnectionStatus(data);
    } catch (error) {
        console.error('Failed to load health status:', error);
        showOverallStatus('エラー', 'error');
    }
}

// 接続状態UI更新
function updateConnectionStatus(data) {
    // 全体ステータス
    showOverallStatus(data.status === 'ok' ? '正常' : '異常あり', data.status);

    // SuperDirt
    updateStatusIndicator('superdirt', data.superdirt.connected);
    document.getElementById('superdirt-host').textContent =
        `${data.superdirt.host}:${data.superdirt.port}`;

    // MIDI
    updateStatusIndicator('midi', data.midi.connected);
    document.getElementById('midi-port').textContent =
        data.midi.port || '未接続';

    // Engine
    updateStatusIndicator('engine', data.engine.running);
    document.getElementById('engine-bpm').textContent = data.engine.bpm;
}

function updateStatusIndicator(id, isOk) {
    const element = document.getElementById(`${id}-status`);
    element.className = `status-indicator ${isOk ? 'status-ok' : 'status-error'}`;
    element.textContent = isOk ? '接続中' : '切断';
}

function showOverallStatus(text, status) {
    const badge = document.getElementById('overall-status');
    badge.textContent = text;
    badge.className = `status-badge status-${status === 'ok' ? 'ok' : 'error'}`;
}
