document.addEventListener('DOMContentLoaded', function() {
    async function fetchStats() {
        try {
            const res1 = await fetch('/functions');
            let totalFunctions = '--';
            if (res1.ok) {
                const data = await res1.json();
                totalFunctions = data.functions ? data.functions.length : '--';
            }
            document.getElementById('total-functions').textContent = totalFunctions;
            const res2 = await fetch('/admin/call_stats_data');
            let totalCalls = '--';
            if (res2.ok) {
                const data = await res2.json();
                totalCalls = data.total !== undefined ? data.total : '--';
            }
            document.getElementById('total-calls').textContent = totalCalls;
        } catch(e) {
            document.getElementById('total-functions').textContent = '--';
            document.getElementById('total-calls').textContent = '--';
        }
    }
    fetchStats();
}); 