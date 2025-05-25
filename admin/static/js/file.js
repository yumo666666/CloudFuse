// 文件管理页主要 JS 逻辑
// 这里只做基础结构，后续可根据需要细化
// ...（可根据 index.html 相关 JS 拆分填充） 

document.addEventListener('DOMContentLoaded', function() {
    // ========== 文件管理页新版 ========== //
    const fileTableContainer = document.getElementById('file-table-container');
    const filePathNav = document.getElementById('file-path-nav');
    const fileBtnBack = document.getElementById('file-btn-back');
    const fileBtnAdd = document.getElementById('file-btn-add');
    const fileBtnRefresh = document.getElementById('file-btn-refresh');
    const fileBtnUpload = document.getElementById('file-btn-upload');
    const fileFolderUploadInput = document.getElementById('file-folder-upload');

    let fileCurrentPath = '';
    let fileTableData = [];
    let fileSelected = new Set();

    // File Edit Dialog elements
    const editDialog = document.getElementById('edit-dialog');
    const editDialogMask = document.getElementById('file-dialog-mask'); // Re-using existing mask
    const currentFileTitle = document.getElementById('current-file-title');
    const fileEditor = document.getElementById('file-editor');
    const editSaveBtn = document.getElementById('edit-save-btn');
    const editCancelBtn = document.getElementById('edit-cancel-btn');

    let currentEditingFilePath = null; // To store the full path of the file being edited

    function renderFilePathNav() {
        const segs = fileCurrentPath ? fileCurrentPath.split('/') : [];
        let html = `<span class='file-path-seg${segs.length === 0 ? ' active' : ''}' onclick="fileJumpTo('')">apps</span>`;
        let path = '';
        for (let i = 0; i < segs.length; ++i) {
            path += (path ? '/' : '') + segs[i];
            const isLast = i === segs.length - 1;
            html += `<span class='file-path-arrow'>&gt;</span><span class='file-path-seg${isLast ? ' active' : ''}' ${isLast ? '' : `onclick=\"fileJumpTo('${path}')\"`}>${segs[i]}</span>`;
        }
        filePathNav.innerHTML = html;
    }

    async function loadFileTable(path = '') {
        fileCurrentPath = path;
        fileSelected.clear();
        renderFilePathNav();
        fileTableContainer.innerHTML = '<div style="color:#888;padding:18px;">加载中...</div>';
        try {
            const res = await fetch('/admin/list_dir?path=' + encodeURIComponent(path));
            if (!res.ok) throw new Error('接口错误');
            fileTableData = await res.json();
            renderFileTable();
        } catch(e) {
            fileTableContainer.innerHTML = '<div style="color:red;padding:18px;">加载失败</div>';
        }
    }

    function renderFileTable() {
        let html = `<table style="width:100%;background:#fff;border-radius:8px;box-shadow:0 2px 8px #f0f0f0;font-size:15px;overflow:hidden;">
            <thead><tr style="background:#f7faff;">
                <th style="width:36px;"><input type='checkbox' id='file-check-all'></th>
                <th style="text-align:left;">名称</th>
                <th style="width:80px;">类型</th>
                <th style="width:100px;">大小</th>
                <th style="width:180px;">修改时间</th>
                <th style="width:220px;">操作</th>
            </tr></thead><tbody>`;
        for (const item of fileTableData) {
            const isFolder = item.type === 'folder';
            const icon = isFolder ? '📁' : '📄';
            const ext = item.name.split('.').pop().toLowerCase();
            // Only allow editing for specific file extensions
            const canEdit = !isFolder && ['py','json','txt','md','yaml','yml'].includes(ext);
            const rowId = 'row-' + item.name.replace(/[^a-zA-Z0-9_-]/g, '_');
            html += `<tr class='file-row' id='${rowId}'>
                <td><input type='checkbox' class='file-check' data-name='${item.name}'></td>
                <td class='file-name-cell' data-name='${item.name}' data-type='${item.type}' data-can-edit='${canEdit}'>
                    <button class='file-main-btn' onclick="event.stopPropagation();${isFolder ? `fileJumpTo('${fileCurrentPath ? fileCurrentPath + '/' : ''}${item.name}')` : (canEdit ? `fileEdit('${item.name}')` : `fileDownload('${item.name}')`)}">
                        <span style='font-size:18px;'>${icon}</span> <span>${item.name}</span>
                    </button>
                </td>
                <td>${isFolder ? '目录' : '文件'}</td>
                <td>${isFolder ? '-' : (item.size == null ? '-' : formatSize(item.size))}</td>
                <td>${item.mtime || '-'}</td>
                <td>
                    <button class='file-op-btn' title='下载' onclick="fileDownload('${item.name}')">⬇️</button>
                    <button class='file-op-btn' title='删除' onclick="fileDelete('${item.name}')">🗑️</button>
                    <button class='file-op-btn' title='重命名' onclick="fileRename('${item.name}')">✏️</button>
                </td>
            </tr>`;
        }
        html += '</tbody></table>';
        fileTableContainer.innerHTML = html;
        document.getElementById('file-check-all').onclick = function() {
            document.querySelectorAll('.file-check').forEach(cb => { cb.checked = this.checked; });
        };
        // 行选中交互
        document.querySelectorAll('.file-row').forEach(row => {
            row.onclick = function(e) {
                // 如果点击的是按钮或checkbox，不处理
                if (e.target.closest('.file-op-btn') || e.target.closest('.file-main-btn') || e.target.classList.contains('file-check')) return;
                row.classList.toggle('selected');
                const name = row.querySelector('.file-name-cell').getAttribute('data-name');
                const cb = row.querySelector('.file-check');
                cb.checked = row.classList.contains('selected');
            };
        });
    }

    function formatSize(size) {
        if (size < 1024) return size + ' B';
        if (size < 1024*1024) return (size/1024).toFixed(1) + ' KB';
        if (size < 1024*1024*1024) return (size/1024/1024).toFixed(1) + ' MB';
        return (size/1024/1024/1024).toFixed(1) + ' GB';
    }

    window.fileJumpTo = function(path) { loadFileTable(path); };

    // New function to handle file editing
    window.fileEdit = async function(name) {
        const filePath = fileCurrentPath ? fileCurrentPath + '/' + name : name;
        currentEditingFilePath = filePath;
        currentFileTitle.textContent = `编辑文件: ${filePath}`;
        fileEditor.value = '加载中...';
        editDialogMask.style.display = 'flex';
        editDialog.style.display = 'flex';

        try {
            const res = await fetch('/admin/get_file_content?path=' + encodeURIComponent(filePath));
            if (!res.ok) throw new Error(`Error fetching file: ${res.status} ${res.statusText}`);
            const data = await res.json();
            if (data.content !== undefined) {
                fileEditor.value = data.content;
            } else {
                fileEditor.value = '无法获取文件内容。';
            }
        } catch (error) {
            console.error('Failed to load file content:', error);
            fileEditor.value = '加载文件内容失败: ' + error.message;
        }
    };

    window.hideEditDialog = function() {
        editDialogMask.style.display = 'none';
        editDialog.style.display = 'none';
        currentEditingFilePath = null;
        fileEditor.value = '';
    };

    // Add event listeners for save and cancel buttons in edit dialog
    editCancelBtn.onclick = window.hideEditDialog;
    editSaveBtn.onclick = async () => {
        if (!currentEditingFilePath) return;
        const content = fileEditor.value;

        const formData = new FormData();
        formData.append('path', currentEditingFilePath);
        formData.append('content', content);

        try {
            // Temporarily disable save button and show saving status
            editSaveBtn.textContent = '保存中...';
            editSaveBtn.disabled = true;

            const res = await fetch('/admin/save_file', {
                method: 'POST',
                body: formData // Use FormData for file content
            });

            if (res.ok) {
                showSuccessNotification('保存成功');
                window.hideEditDialog();
                // Optionally refresh the file list to update modified time
                loadFileTable(fileCurrentPath);
            } else {
                 const errorText = await res.text();
                 alert('保存失败: ' + res.status + ' ' + res.statusText + ', Details: ' + errorText);
            }
        } catch (error) {
            console.error('Failed to save file:', error);
            alert('保存文件失败: ' + error.message);
        } finally {
             // Re-enable save button and restore text
             editSaveBtn.textContent = '保存';
             editSaveBtn.disabled = false;
        }
    };

    // Function to show a custom success notification
    function showSuccessNotification(message) {
        const notification = document.createElement('div');
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.left = '50%';
        notification.style.transform = 'translateX(-50%)';
        notification.style.background = '#fff';
        notification.style.color = '#333';
        notification.style.padding = '12px 24px';
        notification.style.borderRadius = '24px';
        notification.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        notification.style.zIndex = '3000';
        notification.style.display = 'flex';
        notification.style.alignItems = 'center';
        notification.style.gap = '10px';
        notification.style.fontSize = '17px';
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s ease-in-out';

        notification.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="#4CAF50"/>
                <path d="M8 12.3L11 15.3L16 9.3" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="checkmark"/>
            </svg>
            <span>${message}</span>
        `;

        document.body.appendChild(notification);

        // Fade in
        setTimeout(() => {
            notification.style.opacity = '1';
        }, 10);

        // Fade out and remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    window.fileDownload = function(name) {
        const path = fileCurrentPath ? fileCurrentPath + '/' + name : name;
        window.open('/admin/download_file?path=' + encodeURIComponent(path), '_blank');
    };
    window.fileDelete = function(name) {
        // 这里只做简单实现，实际可弹窗确认
        if (!confirm('确定要删除 ' + name + ' 吗？')) return;
        const path = fileCurrentPath ? fileCurrentPath + '/' + name : name;
        fetch('/admin/delete_file?path=' + encodeURIComponent(path), {method:'DELETE'}).then(res => {
            if(res.ok) loadFileTable(fileCurrentPath);
            else alert('删除失败');
        });
    };
    window.fileRename = function(name) {
        const newName = prompt('输入新名称', name);
        if (!newName || newName === name) return;
        const path = fileCurrentPath ? fileCurrentPath + '/' + name : name;
        const form = new FormData();
        form.append('path', path);
        form.append('new_name', newName);
        fetch('/admin/rename_file', {method:'POST', body: form}).then(res => {
            if(res.ok) {
                showSuccessNotification('重命名成功');
                loadFileTable(fileCurrentPath);
            }
            else alert('重命名失败');
        });
    };

    fileBtnBack.onclick = () => {
        if (!fileCurrentPath) return;
        const segs = fileCurrentPath.split('/');
        segs.pop();
        loadFileTable(segs.join('/'));
    };
    fileBtnRefresh.onclick = () => loadFileTable(fileCurrentPath);
    fileBtnAdd.onclick = () => {
        let types = fileCurrentPath === ''
            ? [
                {type: 'project', label: '项目'},
                {type: 'folder', label: '文件夹'},
                {type: 'file', label: '文件'}
            ]
            : [
                {type: 'folder', label: '文件夹'},
                {type: 'file', label: '文件'}
            ];
        let typeBtns = types.map((t, i) =>
            `<button type='button' class='file-create-type-btn${i===0?' selected':''}' data-type='${t.type}'>${t.label}</button>`
        ).join('');
        showFileDialog(`
            <div class='file-create-dialog-title'>新建</div>
            <div class='file-create-type-group'>${typeBtns}</div>
            <div class='file-create-input-wrap'>
                <input id='create-name' class='file-create-input' placeholder='名称' autocomplete='off'>
            </div>
            <div class='file-create-btn-row'>
                <button class='file-create-btn cancel' type='button'>取消</button>
                <button class='file-create-btn confirm' type='button'>创建</button>
            </div>
        `);
        setTimeout(() => {
            const btns = document.querySelectorAll('.file-create-type-btn');
            btns.forEach(btn => {
                btn.onclick = function() {
                    btns.forEach(b => b.classList.remove('selected'));
                    this.classList.add('selected');
                };
            });
            document.querySelector('.file-create-btn.cancel').onclick = hideFileDialog;
            document.querySelector('.file-create-btn.confirm').onclick = async () => {
                const nameInput = document.getElementById('create-name');
                const name = nameInput ? nameInput.value.trim() : '';
                const selectedBtn = document.querySelector('.file-create-type-btn.selected');
                const type = selectedBtn ? selectedBtn.getAttribute('data-type') : types[0].type;
                const typeText = types.find(t => t.type === type)?.label || '';
                if (!name) {
                    nameInput.focus();
                    nameInput.placeholder = '名称不能为空';
                    return;
                }
                if (type === 'project') {
                    showProjectDetailDialog(name);
                    return;
                }
                const data = { path: fileCurrentPath, name, type };
                const res = await fetch('/admin/create_file_or_folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
                });
                if (res.ok) {
                    const result = await res.json();
                    if (result.status === 'success') {
                        showSuccessNotification(`${typeText} "${name}" 创建成功`);
                        loadFileTable(fileCurrentPath);
                        hideFileDialog();
                    } else {
                        alert(`${typeText} "${name}" 创建失败: ` + (result.detail || JSON.stringify(result)));
                    }
                } else {
                    const errorText = await res.text();
                    alert(`${typeText} "${name}" 创建失败: ` + res.status + ' ' + res.statusText + ', Details: ' + errorText);
                }
            };
        }, 10);
    };

    // ========== 迁移 showFileDialog、hideFileDialog、showProjectDetailDialog ==========
    const fileDialogMask = document.getElementById('file-dialog-mask');
    const fileDialog = document.getElementById('file-dialog');
    function showFileDialog(html, onok, oncancel) {
        fileDialog.innerHTML = html;
        fileDialogMask.style.display = 'flex';
        fileDialog.style.display = 'block';
        const okBtn = fileDialog.querySelector('.file-dialog-ok');
        const cancelBtn = fileDialog.querySelector('.file-dialog-cancel');
        if (okBtn) okBtn.onclick = () => { if(onok) onok(); hideFileDialog(); };
        if (cancelBtn) cancelBtn.onclick = hideFileDialog;
        fileDialogMask.onclick = function(e) {
            if (e.target === fileDialogMask) {
                hideFileDialog();
            }
        };
    }
    function hideFileDialog() {
        fileDialogMask.style.display = 'none';
        fileDialog.style.display = 'none';
    }
    function showProjectDetailDialog(projectName) {
        let inputParams = [];
        let outputParams = [];
        function syncParams() {
            document.querySelectorAll('#input-param-list > div').forEach((div, i) => {
                const [nameInput, typeSelect] = div.querySelectorAll('input,select');
                if (inputParams[i]) {
                    inputParams[i].name = nameInput.value;
                    inputParams[i].type = typeSelect.value;
                }
            });
            document.querySelectorAll('#output-param-list > div').forEach((div, i) => {
                const [nameInput, typeSelect] = div.querySelectorAll('input,select');
                if (outputParams[i]) {
                    outputParams[i].name = nameInput.value;
                    outputParams[i].type = typeSelect.value;
                }
            });
        }
        function render() {
            const descInput = document.getElementById('project-desc');
            const savedDesc = descInput ? descInput.value : '';
            let html = `
                <div class='file-create-dialog-title'>新建项目：${projectName}</div>
                <div style='margin-bottom:18px;'>
                    <label style='font-weight:bold;font-size:20px;'>函数描述：</label><br>
                    <input id='project-desc' class='file-create-input' placeholder='输入函数描述' style='margin-top:10px;margin-bottom:0;' value='${savedDesc}'>
                </div>
                <div style='margin-bottom:18px;'>
                    <label style='font-weight:bold;font-size:20px;'>输入参数：</label><br>
                    <div id='input-param-list'>
                        ${inputParams.map((p, i) => `
                            <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                                <input class='file-create-input' style='flex:2;padding:10px 16px;font-size:16px;' placeholder='参数名称' value='${p.name||''}'>
                                <select class='file-create-input' style='flex:1;padding:10px 16px;font-size:16px;background:#fff;'>
                                    <option value='str' ${p.type === 'str' ? 'selected' : ''}>字符串 (str)</option>
                                    <option value='int' ${p.type === 'int' ? 'selected' : ''}>整数 (int)</option>
                                    <option value='float' ${p.type === 'float' ? 'selected' : ''}>浮点数 (float)</option>
                                    <option value='bool' ${p.type === 'bool' ? 'selected' : ''}>布尔值 (bool)</option>
                                    <option value='list' ${p.type === 'list' ? 'selected' : ''}>列表 (list)</option>
                                    <option value='dict' ${p.type === 'dict' ? 'selected' : ''}>字典 (dict)</option>
                                </select>
                                <button class='file-create-btn cancel param-del-btn' style='padding:6px 16px;font-size:15px;' data-idx='${i}'>删除</button>
                            </div>
                        `).join('')}
                    </div>
                    <button class='file-create-btn confirm' id='add-input-param' style='width:100%;margin-top:8px;'>添加输入参数</button>
                </div>
                <div style='margin-bottom:18px;'>
                    <label style='font-weight:bold;font-size:20px;'>返回参数：</label><br>
                    <div id='output-param-list'>
                        ${outputParams.map((p, i) => `
                            <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                                <input class='file-create-input' style='flex:2;padding:10px 16px;font-size:16px;' placeholder='参数名称' value='${p.name||''}'>
                                <select class='file-create-input' style='flex:1;padding:10px 16px;font-size:16px;background:#fff;'>
                                    <option value='str' ${p.type === 'str' ? 'selected' : ''}>字符串 (str)</option>
                                    <option value='int' ${p.type === 'int' ? 'selected' : ''}>整数 (int)</option>
                                    <option value='float' ${p.type === 'float' ? 'selected' : ''}>浮点数 (float)</option>
                                    <option value='bool' ${p.type === 'bool' ? 'selected' : ''}>布尔值 (bool)</option>
                                    <option value='list' ${p.type === 'list' ? 'selected' : ''}>列表 (list)</option>
                                    <option value='dict' ${p.type === 'dict' ? 'selected' : ''}>字典 (dict)</option>
                                </select>
                                <button class='file-create-btn cancel param-del-btn' style='padding:6px 16px;font-size:15px;' data-idx='${i}'>删除</button>
                            </div>
                        `).join('')}
                    </div>
                    <button class='file-create-btn confirm' id='add-output-param' style='width:100%;margin-top:8px;'>添加返回参数</button>
                </div>
                <div class='file-create-btn-row'>
                    <button class='file-create-btn cancel' type='button'>取消</button>
                    <button class='file-create-btn confirm' id='project-create-btn' type='button'>创建</button>
                </div>
            `;
            showFileDialog(html);
            fileDialog.onclick = function(e) {
                e.stopPropagation();
                if (e.target.classList.contains('param-del-btn')) {
                    syncParams();
                    const idx = parseInt(e.target.getAttribute('data-idx'));
                    const isInput = e.target.closest('#input-param-list') !== null;
                    if (isInput) inputParams.splice(idx, 1);
                    else outputParams.splice(idx, 1);
                    render();
                }
                if (e.target.id === 'add-input-param') {
                    syncParams();
                    inputParams.push({name:'',type:'str'});
                    render();
                }
                if (e.target.id === 'add-output-param') {
                    syncParams();
                    outputParams.push({name:'',type:'str'});
                    render();
                }
            };
            document.querySelector('.file-create-btn.cancel').onclick = hideFileDialog;
            document.getElementById('project-create-btn').onclick = async () => {
                syncParams();
                const desc = document.getElementById('project-desc').value.trim();
                const inputList = inputParams.filter(p => p.name);
                const outputList = outputParams.filter(p => p.name);
                function genPyType(t) {
                    return {str:'str',int:'int',float:'float',bool:'bool',list:'list',dict:'dict'}[t]||'str';
                }
                function genDefaultValue(t) {
                    return {str: "''", int: '0', float: '0.0', bool: 'False', list: '[]', dict: '{}'}[t]||"''";
                }
                const paramStr = inputList.map(p => `${p.name}: ${genPyType(p.type)}`).join(', ');
                const docParams = inputList.map(p => `    ${p.name}: ${p.type}`).join('\n');
                const docReturns = outputList.map(p => `    ${p.name}: ${p.type}`).join('\n');
                const funcCode = `def ${projectName}(${paramStr}):\n    """\n    ${desc}\n    参数:\n${docParams}\n    返回:\n${docReturns}\n    """\n    # TODO: 实现你的业务逻辑\n    return {}`;
                const config = {
                    url: `/function/${projectName}`,
                    method: 'GET',
                    name: desc,
                    parameters: inputList.map(p => ({
                        name: p.name,
                        type: p.type,
                        required: true,
                        description: '',
                        default: ''
                    }))
                };
                const data = {
                    function_name: projectName,
                    files: {
                        function: funcCode,
                        config: JSON.stringify(config, null, 2),
                        intro: desc
                    }
                };
                const res = await fetch('/admin/create_function', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    const result = await res.json();
                    if (result.status === 'success') {
                        showSuccessNotification(`项目 "${projectName}" 创建成功`);
                        loadFileTable(fileCurrentPath);
                        hideFileDialog();
                    } else {
                        alert(`项目 "${projectName}" 创建失败: ` + (result.detail || JSON.stringify(result)));
                    }
                } else {
                    const errorText = await res.text();
                    alert(`项目 "${projectName}" 创建失败: ` + res.status + ' ' + res.statusText + ', Details: ' + errorText);
                }
            };
        }
        render();
    }

    // 页面加载时自动加载根目录
    loadFileTable('');
}); 