document.addEventListener('DOMContentLoaded', function() {
    let allApiConfigs = [];
    let filteredApiConfigs = [];
    let currentApi = null;

    async function loadApiConfigs() {
        const res = await fetch('/functions');
        if (!res.ok) return;
        const data = await res.json();
        if (!data.functions) return;
        allApiConfigs = [];
        for (const fn of data.functions) {
            if (!fn.name) continue;
            try {
                const res2 = await fetch(`/admin/get_function_file_content/${fn.name}?file_path=config.json`);
                if (!res2.ok) continue;
                const conf = await res2.json();
                if (conf && conf.content) {
                    const cfg = JSON.parse(conf.content);
                    cfg._funcname = fn.name;
                    allApiConfigs.push(cfg);
                }
            } catch(e) {}
        }
        filteredApiConfigs = allApiConfigs;
        renderApiList();
        if (filteredApiConfigs.length > 0) showApiDetail(filteredApiConfigs[0]);
    }
    function renderApiList() {
        const list = document.getElementById('api-list');
        list.innerHTML = '';
        filteredApiConfigs.forEach((api, idx) => {
            const mainTitle = api.name && api.name.trim() ? api.name : api._funcname;
            const subTitle = api.url || '';
            const item = document.createElement('div');
            item.className = 'apilist-item' + (currentApi && currentApi._funcname === api._funcname ? ' active' : '');
            item.style = `padding:12px 14px;margin:6px 0;border-radius:8px;cursor:pointer;background:${currentApi && currentApi._funcname === api._funcname ? '#e3f0ff':'#fff'};border:1px solid #e3eaf2;font-size:15px;transition:background 0.2s;`;
            item.innerHTML = `<span style=\"color:#2196F3;font-weight:bold;\">${mainTitle}</span><br><span style=\"font-size:13px;color:#888\">${subTitle}</span>`;
            item.onclick = () => { currentApi = api; renderApiList(); showApiDetail(api); };
            list.appendChild(item);
        });
    }
    document.getElementById('api-search').oninput = function() {
        const kw = this.value.trim().toLowerCase();
        filteredApiConfigs = allApiConfigs.filter(api => api.name.toLowerCase().includes(kw) || (api.url||'').toLowerCase().includes(kw));
        renderApiList();
        if (filteredApiConfigs.length > 0) showApiDetail(filteredApiConfigs[0]);
        else document.getElementById('api-detail-content').innerHTML = '';
    };
    function showApiDetail(api) {
        let html = '';
        const mainTitle = api._display_name && api._display_name.trim() ? api._display_name : api._funcname;
        const fullUrl = `http://${window.location.host}${api.url||''}`;
        html += `<div style=\"background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(33,150,243,0.06);padding:32px 36px 24px 36px;\">
            <div style=\"display:flex;align-items:center;gap:16px;margin-bottom:8px;\">
                <div style=\"font-size:22px;color:#2196F3;font-weight:bold;\">${api.name}</div>
                <span class=\"route-chip\" onclick=\"copyRouteLink(this, '${fullUrl}')\">${api.url||''}</span>
                                         </div>
            <div style=\"margin:0 0 18px 0;\">
                <span class=\"call-url-chip\" onclick=\"copyRouteLink(this, '${fullUrl}')\">${fullUrl}</span>
                                </div>
            <div style=\"margin:18px 0 0 0;font-size:15px;color:#555;\">${api._display_name||''}</div>
            <div style=\"margin:24px 0 0 0;\">
                <div style=\"font-size:16px;font-weight:bold;color:#2196F3;margin-bottom:8px;\">请求体结构</div>
                <div>${renderParamStruct(api.parameters||[])}</div>
                                </div>
            <div style=\"margin:24px 0 0 0;\">
                <div style=\"font-size:16px;font-weight:bold;color:#2196F3;margin-bottom:8px;\">接口调试</div>
                <form id=\"apidebug-form\" onsubmit=\"sendApiDebug(event)\">
                    ${renderParamInputs(api.parameters||[])}
                    <button type=\"submit\" style=\"margin-top:12px;background:#2196F3;color:#fff;border:none;border-radius:8px;padding:10px 28px;font-size:16px;cursor:pointer;\">发送请求</button>
                </form>
                            </div>
            <div id=\"api-body-panel\" style=\"margin:24px 0 0 0;\">
                <div style=\"font-size:16px;font-weight:bold;color:#2196F3;margin-bottom:8px;display:flex;align-items:center;gap:16px;\">
                    <span>请求体（JSON）</span>
                    <button id=\"toggle-body-btn\" style=\"background:#e3f0ff;color:#2196F3;border:none;border-radius:6px;padding:4px 10px;cursor:pointer;font-size:14px;\" onclick=\"toggleApiBody()\">展开</button>
                    <button id=\"copy-body-btn\" style=\"background:#e3f0ff;color:#2196F3;border:none;border-radius:6px;padding:4px 10px;cursor:pointer;font-size:14px;display:none;\" onclick=\"copyApiBodyJson()\">复制</button>
                                </div>
                <pre id=\"api-body-json\" style=\"background:#f7faff;border-radius:8px;padding:18px 14px;font-size:15px;min-height:48px;max-height:320px;overflow:auto;display:none;\"></pre>
                            </div>
            <div style=\"margin:24px 0 0 0;\">
                <div style=\"font-size:16px;font-weight:bold;color:#2196F3;margin-bottom:8px;\">响应</div>
                <pre id=\"apidebug-response\" style=\"background:#f7faff;border-radius:8px;padding:18px 14px;font-size:15px;min-height:48px;\"></pre>
                        </div>
        </div>`;
        document.getElementById('api-detail-content').innerHTML = html;
        updateApiBodyJson(api);
        const form = document.getElementById('apidebug-form');
        if (form) {
            form.oninput = () => updateApiBodyJson(api);
        }
    }
    function updateApiBodyJson(api) {
        const form = document.getElementById('apidebug-form');
        const params = {};
        if (form && api.parameters) {
            for (const p of api.parameters) {
                const el = form.querySelector(`[name='${p.name}']`);
                params[p.name] = el ? el.value : (p.default || (p.type === 'number' ? 0 : ''));
            }
        }
        const jsonStr = JSON.stringify(params, null, 2);
        const pre = document.getElementById('api-body-json');
        if (pre) pre.textContent = jsonStr;
    }
    function toggleApiBody() {
        const pre = document.getElementById('api-body-json');
        const btn = document.getElementById('toggle-body-btn');
        const copyBtn = document.getElementById('copy-body-btn');
        if (pre.style.display === 'none') {
            pre.style.display = 'block';
            btn.textContent = '收起';
            copyBtn.style.display = '';
        } else {
            pre.style.display = 'none';
            btn.textContent = '展开';
            copyBtn.style.display = 'none';
        }
    }
    function copyApiBodyJson() {
        const pre = document.getElementById('api-body-json');
        if (pre) {
            navigator.clipboard.writeText(pre.textContent);
            const btn = document.getElementById('copy-body-btn');
            btn.textContent = '已复制！';
            setTimeout(() => { btn.textContent = '复制'; }, 1000);
        }
    }
    function renderParamStruct(params) {
        if (!params.length) return '<span style="color:#aaa;">无参数</span>';
        return params.map(p => `<div style="margin-bottom:8px;"><span style="background:#e3f0ff;color:#2196F3;border-radius:6px;padding:2px 10px;font-size:14px;margin-right:8px;">${p.name}</span><span style="color:#888;">${p.type}</span> <span style="color:#bbb;">${p.required?'必填':'可选'}</span> <span style="color:#aaa;">${p.description||''}</span></div>`).join('');
    }
    function renderParamInputs(params) {
        if (!params.length) return '<div style="color:#aaa;">无参数</div>';
        return params.map(p => `<div style="margin-bottom:12px;"><label style="font-size:15px;color:#555;margin-bottom:4px;display:block;">${p.name} <span style="color:#888;font-size:13px;">(${p.type}${p.required?'，必填':'，可选'})</span></label><input name="${p.name}" type="text" placeholder="${p.description||''}" value="${p.default||''}" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid #e3eaf2;background:#f7faff;font-size:15px;"></div>`).join('');
    }
    window.sendApiDebug = async function(e) {
        e.preventDefault();
        if (!currentApi) return;
        const form = document.getElementById('apidebug-form');
        const params = {};
        for (const el of form.elements) {
            if (el.name) params[el.name] = el.value;
        }
        let url = currentApi.url;
        let method = (currentApi.method||'GET').toUpperCase();
        let options = { method, headers: { 'Content-Type': 'application/json' } };
        if (method === 'GET') {
            const usp = new URLSearchParams(params);
            url += '?' + usp.toString();
        } else {
            options.body = JSON.stringify(params);
        }
        try {
            const res = await fetch(url, options);
            const data = await res.json();
            document.getElementById('apidebug-response').textContent = JSON.stringify(data, null, 2);
        } catch(e) {
            document.getElementById('apidebug-response').textContent = '请求失败：'+e.message;
        }
    }
    window.copyRouteLink = function(el, url) {
        navigator.clipboard.writeText(url);
        const old = el.textContent;
        el.textContent = '已复制！';
        el.style.background = '#b2e0ff';
        setTimeout(() => {
            el.textContent = old;
            el.style.background = '';
        }, 1000);
    }
    loadApiConfigs();
}); 