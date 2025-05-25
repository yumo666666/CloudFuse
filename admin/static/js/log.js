document.addEventListener('DOMContentLoaded', function() {
    let logWs = null;
    let logBuffer = '';
    function startLogStream() {
        if (logWs && logWs.readyState === WebSocket.OPEN) return;
        if (logWs) logWs.close();
        logBuffer = '';
        logWs = new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/admin/logs/stream');
        logWs.onopen = function() {
            logBuffer = '连接成功，等待输出...\n';
            renderLogStream();
        };
        logWs.onmessage = function(e) {
            logBuffer += e.data;
            renderLogStream();
        };
        logWs.onclose = function(){};
        logWs.onerror = function(error){};
    }
    function renderLogStream() {
        const preLog = document.getElementById('log-cards');
        if (preLog) {
            preLog.textContent = logBuffer;
            preLog.scrollTop = preLog.scrollHeight;
        }
    }
    startLogStream();
}); 