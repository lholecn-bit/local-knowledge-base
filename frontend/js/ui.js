// frontend/js/ui.js
class UI {
constructor() {
        // 聊天/问答区
        this.chatHistory = document.getElementById('chatHistory');
        this.questionInput = document.getElementById('questionInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.stopBtn = document.getElementById('stopBtn');
        // 文档上传/列表（侧边栏）
        this.fileInput = document.getElementById('fileInput');
        this.documentsList = document.getElementById('documentsList');
        this.totalChunksEl = document.getElementById('totalChunks');
        this.dbStatusEl = document.getElementById('dbStatus');
        this.clearKbBtn = document.getElementById('clearKbBtn');
        this.refreshStatsBtn = document.getElementById('refreshStatsBtn');
        // 公共
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
        this.confirmModal = document.getElementById('confirmModal');
        this.confirmYesBtn = document.getElementById('confirmYesBtn');
        this.confirmNoBtn = document.getElementById('confirmNoBtn');
        this.useStreamCheckbox = document.getElementById('useStreamCheckbox');
        this.topKInput = document.getElementById('topKInput');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        // 文档管理区
        this.navChat = document.getElementById('navChat');
        this.navDocMgmt = document.getElementById('navDocMgmt');
        this.chatPanel = document.getElementById('chatPanel');
        this.docMgmtPanel = document.getElementById('docMgmtPanel');
        this.docMgmtToggle = document.getElementById('docMgmtToggle');
        this.docSearchInput = document.getElementById('docSearchInput');
        this.docRefreshBtn = document.getElementById('docRefreshBtn');
        this.docBatchDeleteBtn = document.getElementById('docBatchDeleteBtn');
        this.docMgmtTable = document.getElementById('docMgmtTable');
        this.docMgmtTableBody = document.getElementById('docMgmtTableBody');
        this.docSelectAll = document.getElementById('docSelectAll');
        this.sidebar = document.querySelector('.sidebar');
        this.sidebarToggle = document.getElementById('sidebarToggle');

        this.isLoading = false;
        this.abortController = null;
        this.currentMessageEl = null;
        this.onModeChange = null; // 添加模式改变回调
        this._highlightTimeout = null;

        // 初始化模式选择器事件
        this._initModeSelector();
        // 初始化导航切换
        this._initNavSwitch();
        // 应用侧边栏折叠状态（如有）
        this._applySidebarState();
    }

    /**
     * 初始化侧边栏导航切换
     */
    _initNavSwitch() {
        if (this.navChat && this.navDocMgmt && this.chatPanel && this.docMgmtPanel) {
            this.navChat.addEventListener('click', (e) => {
                e.preventDefault();
                this.showChatPanel();
            });
            this.navDocMgmt.addEventListener('click', (e) => {
                e.preventDefault();
                this.showDocMgmtPanel();
            });
            // 顶部切换按钮
            if (this.docMgmtToggle) {
                this.docMgmtToggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    // 如果当前文档管理可见，则切回聊天
                    if (this.docMgmtPanel.style.display !== 'none') {
                        this.showChatPanel();
                    } else {
                        this.showDocMgmtPanel();
                    }
                });
            }
        }
            // 侧边栏折叠按钮
            if (this.sidebarToggle && this.sidebar) {
                this.sidebarToggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleSidebar();
                });
            }
    }


    toggleSidebar() {
        if (!this.sidebar) return;
        const collapsed = this.sidebar.classList.toggle('collapsed');
        try { localStorage.setItem('sidebarCollapsed', collapsed ? '1' : '0'); } catch (e) {}
    }

    _applySidebarState() {
        try {
            const v = localStorage.getItem('sidebarCollapsed');
            if (v === '1' && this.sidebar) this.sidebar.classList.add('collapsed');
        } catch (e) {}
    }
    showChatPanel() {
        this.chatPanel.style.display = '';
        this.docMgmtPanel.style.display = 'none';
        this.navChat.classList.add('active');
        this.navDocMgmt.classList.remove('active');
        const title = document.getElementById('panelTitle');
        if (title) title.textContent = '问答检索';
        if (this.docMgmtToggle) this.docMgmtToggle.textContent = '文档管理';
    }

    showDocMgmtPanel() {
        this.chatPanel.style.display = 'none';
        this.docMgmtPanel.style.display = '';
        this.navChat.classList.remove('active');
        this.navDocMgmt.classList.add('active');
        const title = document.getElementById('panelTitle');
        if (title) title.textContent = '文档管理';
        if (this.docMgmtToggle) this.docMgmtToggle.textContent = '返回问答';
    }

    /**
     * 渲染文档管理表格
     * @param {Array} files - 文档数组，含元数据
     */
    renderDocMgmtTable(files) {
        if (!Array.isArray(files) || files.length === 0) {
            this.docMgmtTableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#888;">暂无文档</td></tr>';
            return;
        }
        let html = '';
        for (const file of files) {
            html += `
                <tr>
                    <td><input type="checkbox" class="doc-select" data-filename="${this.escapeHtml(file.name)}"></td>
                    <td class="doc-name">${this.escapeHtml(file.name)}</td>
                    <td>${this.escapeHtml(file.type || (file.name && file.name.split('.').pop().toUpperCase()) || '')}</td>
                    <td>${file.size ? this._formatSize(file.size) : '-'}</td>
                    <td>${file.upload_time ? this._formatTime(file.upload_time) : '-'}</td>
                    <td>${file.chunks ?? '-'}</td>
                    <td>${file.status ?? '已索引'}</td>
                    <td>
                        <button class="btn btn-sm btn-info doc-detail-btn" data-filename="${this.escapeHtml(file.name)}">详情</button>
                        <button class="btn btn-sm btn-danger doc-delete-btn" data-filename="${this.escapeHtml(file.name)}">删除</button>
                    </td>
                </tr>
            `;
        }
        this.docMgmtTableBody.innerHTML = html;
    }

    /**
     * 工具：格式化文件大小
     */
    _formatSize(size) {
        if (typeof size !== 'number') return size;
        if (size < 1024) return size + ' B';
        if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
        return (size / 1024 / 1024).toFixed(2) + ' MB';
    }

    /**
     * 工具：格式化时间戳
     */
    _formatTime(ts) {
        // 支持 ISO 字符串或时间戳
        let d = typeof ts === 'string' ? new Date(ts) : new Date(ts * 1000);
        if (isNaN(d.getTime())) return '-';
        return d.toLocaleString('zh-CN', { hour12: false });
    }

    // ...existing code...

    /**
     * 初始化模式选择器事件处理
     */
    _initModeSelector() {
        const modeRadios = document.querySelectorAll('input[name="queryMode"]');
        modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (this.onModeChange) {
                    this.onModeChange(e.target.value);
                }
            });
        });
    }

    /**
     * 绑定模式改变事件
     */
    bindModeChange(callback) {
        this.onModeChange = callback;
    }

    bindSendButton(onQuery) {
        this.sendBtn.addEventListener('click', onQuery);
        this.questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                onQuery();
            }
        });
    }

    bindFileInputChange(onFileSelect) {
        this.fileInput.addEventListener('change', (e) => {
            onFileSelect(e.target.files);
        });
    }

    bindClearKBButton(onClear) {
        this.clearKbBtn.addEventListener('click', onClear);
    }

    bindRefreshStatsButton(onRefresh) {
        this.refreshStatsBtn.addEventListener('click', onRefresh);
    }

    bindDocumentDelete(onDelete) {
        this.onDocumentDelete = onDelete;
    }

    getQuestion() {
        return this.questionInput.value.trim();
    }

    clearInput() {
        this.questionInput.value = '';
    }

    focusInput() {
        this.questionInput.focus();
    }

    addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.innerHTML = `<div class="message-content">${this.escapeHtml(message)}</div>`;
        this.chatHistory.appendChild(messageDiv);
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }

    addAssistantMessage(message, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        
        // ✅ 用 marked.js 渲染
        let content = `<div class="message-content">${this.markdownToHtml(message)}</div>`;
        
        if (sources && sources.length > 0) {
            content += this._buildSourcesHtml(sources);
        }
        
        messageDiv.innerHTML = content;
        this.chatHistory.appendChild(messageDiv);
        
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }


    addStreamMessage() {
        this.currentMessageEl = document.createElement('div');
        this.currentMessageEl.className = 'message assistant-message';
        this.currentMessageEl.innerHTML = '<div class="message-content stream-content"></div>';
        
        this.chatHistory.appendChild(this.currentMessageEl);
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }

    /**
     * 处理流式内容（使用 marked.js）
     */
    _processStreamContent(element) {
        if (!element) return;
        
        // ✅ 获取纯文本
        const plainText = element.textContent;
        
        // ✅ 用 marked.js 转换为 HTML
        const htmlContent = this.markdownToHtml(plainText);
        
        // ✅ 设置 HTML
        element.innerHTML = htmlContent;
    }


    updateStreamMessage(text) {
        if (!text) return;
        
        if (typeof text !== 'string') {
            text = String(text);
        }
        
        if (this.currentMessageEl) {
            const contentDiv = this.currentMessageEl.querySelector('.stream-content');
            if (contentDiv) {
                // ✅ 只追加纯文本
                contentDiv.textContent += text;
                
                // ✅ 延迟处理（等待流数据稳定）
                clearTimeout(this._highlightTimeout);
                this._highlightTimeout = setTimeout(() => {
                    this._processStreamContent(contentDiv);
                }, 300);
                
                this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
            }
        }
    }

    showSources(sources) {
        if (!this.currentMessageEl) return;
        if (!sources || sources.length === 0) return;
        
        const sourcesHtml = this._buildSourcesHtml(sources);
        
        if (!this.currentMessageEl.querySelector('.sources-container')) {
            this.currentMessageEl.innerHTML += sourcesHtml;
        }
        
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }

    _buildSourcesHtml(sources) {
        if (!sources || sources.length === 0) return '';
        
        const sourcesList = [];
        const seenFilenames = new Set();
        
        for (const source of sources) {
            // ✅ 兼容两种格式：
            // 1. 直接字符串：["file1.pdf", "file2.md"]
            // 2. 对象格式：[{source: "file1.pdf", content: "...", score: 0.95}, ...]
            const filename = typeof source === 'string' 
                ? source 
                : (source.source || source.filename || source.name);
            
            if (!filename || seenFilenames.has(filename)) continue;
            
            seenFilenames.add(filename);
            sourcesList.push(`<li> ${this.escapeHtml(filename)}</li>`);
        }
        
        if (sourcesList.length === 0) return '';
        
        return `<div class="sources-container"><strong>📚 相关文档：</strong><ul>${sourcesList.join('')}</ul></div>`;
    }


    /**
     * 高亮代码块（最终修复版）
     */
    _highlightCode(element) {
        if (typeof hljs === 'undefined') return;
        
        const codeBlocks = element.querySelectorAll('pre code');
        codeBlocks.forEach(block => {
            try {
                // ✅ 检查是否已经高亮过
                if (block.classList.contains('hljs')) {
                    return;  // 跳过已经高亮的块
                }
                
                // ✅ 获取原始代码（必须是文本，不能有 HTML）
                const code = block.textContent;
                
                if (!code || !code.trim()) {
                    return;
                }
                
                // ✅ 完全清空，重新设置为纯文本
                block.innerHTML = '';
                block.textContent = code;
                
                // ✅ 清除所有类名，重新开始
                block.className = '';
                
                // ✅ 从 <pre> 标签的 class 中提取语言
                const preElement = block.parentElement;
                let language = null;
                
                if (preElement && preElement.className) {
                    const match = preElement.className.match(/language-([a-z0-9\-_]+)/i);
                    if (match && match[1] && match[1].trim() !== '-') {
                        language = match[1].trim();
                    }
                }
                
                // ✅ 如果没找到语言，尝试从 code 的 class 中找
                if (!language && block.className) {
                    const match = block.className.match(/language-([a-z0-9\-_]+)/i);
                    if (match && match[1] && match[1].trim() !== '-') {
                        language = match[1].trim();
                    }
                }
                
                // ✅ 设置语言类
                if (language && language !== '') {
                    block.className = `language-${language}`;
                }
                
                // ✅ 进行高亮
                hljs.highlightElement(block);
                
            } catch (err) {
                console.debug(`代码高亮跳过: ${err.message}`);
            }
        });
    }

    setSendButtonState(enabled) {
        this.sendBtn.disabled = !enabled;
        this.sendBtn.style.opacity = enabled ? '1' : '0.5';
    }

    showLoading(text = '处理中...') {
        this.loadingText.textContent = text;
        this.loadingOverlay.style.display = 'flex';
        this.isLoading = true;
    }

    hideLoading() {
        this.loadingOverlay.style.display = 'none';
        this.isLoading = false;
    }

    showConfirmModal(message, callback) {
        document.getElementById('confirmText').textContent = message;
        this.confirmModal.style.display = 'flex';

        const handleYes = () => {
            this.confirmModal.style.display = 'none';
            this.confirmYesBtn.removeEventListener('click', handleYes);
            this.confirmNoBtn.removeEventListener('click', handleNo);
            callback(true);
        };

        const handleNo = () => {
            this.confirmModal.style.display = 'none';
            this.confirmYesBtn.removeEventListener('click', handleYes);
            this.confirmNoBtn.removeEventListener('click', handleNo);
            callback(false);
        };

        this.confirmYesBtn.addEventListener('click', handleYes);
        this.confirmNoBtn.addEventListener('click', handleNo);
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'error' ? '#ff6b6b' : type === 'success' ? '#51cf66' : '#4c6ef5'};
            color: white;
            border-radius: 5px;
            z-index: 10000;
            max-width: 400px;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // 显示文档详情模态框
    showDocumentDetail(detail) {
        const modal = document.getElementById('docDetailModal');
        const body = document.getElementById('docDetailBody');
        const title = document.getElementById('docDetailTitle');
        if (!modal || !body || !title) return;

        title.textContent = `文档详情：${detail.name}`;
        const sizeText = detail.size ? this._formatSize(detail.size) : '-';
        const uploadTime = detail.upload_time || '-';
        const chunks = detail.chunks || 0;
        const status = detail.status || '-';

        let html = `
            <p><strong>路径：</strong> ${this.escapeHtml(detail.path || '-')}</p>
            <p><strong>大小：</strong> ${sizeText}</p>
            <p><strong>上传时间：</strong> ${this.escapeHtml(uploadTime)}</p>
            <p><strong>分块数：</strong> ${chunks}</p>
            <p><strong>状态：</strong> ${this.escapeHtml(status)}</p>
            <hr />
            <h4>分块预览（显示前 2000 字）</h4>
        `;

        if (detail.chunks_detail && detail.chunks_detail.length > 0) {
            html += '<div class="chunks-list">';
            detail.chunks_detail.forEach((c, idx) => {
                html += `<div class="chunk-item"><h5>Chunk ${idx + 1}</h5><div class="chunk-content">${this.markdownToHtml(c.content)}</div></div>`;
            });
            html += '</div>';
        } else {
            html += '<p style="color:#666">暂无分块预览</p>';
        }

        body.innerHTML = html;

        // 绑定按钮
        const reindexBtn = document.getElementById('docReindexBtn');
        const closeBtn = document.getElementById('docCloseBtn');
        reindexBtn.dataset.filename = detail.name;

        const handleClose = () => {
            modal.style.display = 'none';
            reindexBtn.removeEventListener('click', handleReindex);
            closeBtn.removeEventListener('click', handleClose);
        };

        const handleReindex = async (e) => {
            if (this.onReindexDocument) {
                const filename = e.target.dataset.filename;
                await this.onReindexDocument(filename);
            }
        };

        reindexBtn.addEventListener('click', handleReindex);
        closeBtn.addEventListener('click', handleClose);

        modal.style.display = 'flex';
    }

    bindReindexDocument(callback) {
        this.onReindexDocument = callback;
    }

    updateStats(stats) {
        this.totalChunksEl.textContent = stats.total_chunks || 0;
        this.dbStatusEl.textContent = stats.total_chunks > 0 ? '✓ 就绪' : '空';
        this.dbStatusEl.style.color = stats.total_chunks > 0 ? '#51cf66' : '#ff6b6b';
    }

    updateDocumentsList(files) {
        if (files.length === 0) {
            this.documentsList.innerHTML = '<p class="no-documents">暂无文档</p>';
            return;
        }

        let html = '';
        for (const file of files) {
            html += `
                <div class="document-item">
                    <span class="doc-name">${this.escapeHtml(file.name)}</span>
                    <button class="btn-delete" data-filename="${this.escapeHtml(file.name)}">删除</button>
                </div>
            `;
        }
        this.documentsList.innerHTML = html;

        this.documentsList.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filename = e.target.dataset.filename;
                if (this.onDocumentDelete) {
                    this.onDocumentDelete(filename);
                }
            });
        });
    }

    clearChatHistory() {
        this.chatHistory.innerHTML = `
            <div class="welcome-message">
                <h2>👋 欢迎使用知识库系统</h2>
                <p>请上传文档，然后提出您的问题</p>
                <div class="tips">
                    <h4>使用提示：</h4>
                    <ul>
                        <li>在左侧上传 PDF、Word、TXT 或 Markdown 文件</li>
                        <li>系统会自动处理文件内容并创建向量索引</li>
                        <li>在下方输入您的问题，系统会基于已上传的文档回答</li>
                        <li>支持多轮对话</li>
                    </ul>
                </div>
            </div>
        `;
    }

    shouldUseStream() {
        return this.useStreamCheckbox.checked;
    }

    getTopK() {
        return parseInt(this.topKInput.value) || 3;
    }

    escapeHtml(text) {
        if (text === null || text === undefined) {
            return '';
        }
        
        if (typeof text !== 'string') {
            text = String(text);
        }
        
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Markdown 转 HTML（完整版 - 包含错误处理和自定义渲染）
     */
    markdownToHtml(text) {
        if (!text) return '';
        
        // ✅ 检查 marked 库
        if (typeof marked === 'undefined') {
            console.warn('⚠️ marked.js 库未加载');
            return this.escapeHtml(text).replace(/\n/g, '<br>');
        }
        
        try {
            // ✅ 保存 this 引用（因为在 highlight 函数里 this 会改变）
            const self = this;
            
            // ✅ 配置 marked
            marked.setOptions({
                breaks: true,
                gfm: true,
                pedantic: false,
                mangle: false,
                // ✅ 设置代码高亮函数
                highlight: (code, language) => {
                    // ✅ 移除代码块周围的空格
                    code = code.trim();
                    
                    // ✅ 尝试用指定语言高亮
                    if (language && typeof hljs !== 'undefined') {
                        try {
                            const highlighted = hljs.highlight(code, { 
                                language: language,
                                ignoreIllegals: true 
                            }).value;
                            return highlighted;
                        } catch (err) {
                            console.debug(`语言 '${language}' 高亮失败，尝试自动检测`);
                        }
                    }
                    
                    // ✅ 自动检测语言
                    if (typeof hljs !== 'undefined') {
                        try {
                            return hljs.highlightAuto(code).value;
                        } catch (err) {
                            console.debug('自动检测失败，返回原始代码');
                        }
                    }
                    
                    // ✅ 备用方案：转义 HTML（使用 self 而不是 this）
                    return self.escapeHtml(code);
                }
            });
            
            // ✅ 渲染 Markdown
            const html = marked.parse(text);
            
            return html;
        } catch (error) {
            console.error('❌ Markdown 渲染失败:', error);
            // ✅ 降级处理：返回转义后的文本
            return this.escapeHtml(text).replace(/\n/g, '<br>');
        }
    }

    /*
    * 显示上传进度条
    */
    showUploadProgress() {
        // 显示进度条容器
        const progressDiv = document.createElement('div');
        progressDiv.id = 'uploadProgressContainer';
        progressDiv.className = 'upload-progress-container';
        progressDiv.innerHTML = `
            <div class="progress-card">
                <h3>📤 上传进度</h3>
                <div class="progress-bar-container">
                    <div id="uploadProgressBar" class="progress-bar">
                        <div class="progress-fill" style="width: 0%"></div>
                    </div>
                    <span id="uploadProgressText">0%</span>
                </div>
                <p id="uploadMessage">准备上传...</p>
            </div>
        `;
        
        this.chatHistory.parentElement.appendChild(progressDiv);
    }

    /*
    * 更新上传进度条
    */
    updateUploadProgress(progress, message) {
        const progressBar = document.getElementById('uploadProgressBar');
        const progressText = document.getElementById('uploadProgressText');
        const progressMessage = document.getElementById('uploadMessage');
        
        if (progressBar) {
            const fill = progressBar.querySelector('.progress-fill');
            fill.style.width = progress + '%';
            progressText.textContent = progress + '%';
        }
        
        if (progressMessage && message) {
            progressMessage.textContent = message;
        }
    }

    /*
    * 隐藏上传进度条
    */
    hideUploadProgress() {
        const container = document.getElementById('uploadProgressContainer');
        if (container) {
            container.remove();
        }
    }
}
