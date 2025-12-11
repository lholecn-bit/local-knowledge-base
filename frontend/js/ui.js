// frontend/js/ui.js
class UI {
constructor() {
        this.chatHistory = document.getElementById('chatHistory');
        this.questionInput = document.getElementById('questionInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.fileInput = document.getElementById('fileInput');
        this.documentsList = document.getElementById('documentsList');
        this.totalChunksEl = document.getElementById('totalChunks');
        this.dbStatusEl = document.getElementById('dbStatus');
        this.clearKbBtn = document.getElementById('clearKbBtn');
        this.refreshStatsBtn = document.getElementById('refreshStatsBtn');
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
        
        this.isLoading = false;
        this.abortController = null;
        this.currentMessageEl = null;
        this.onModeChange = null; // 添加模式改变回调
        this._highlightTimeout = null;  // ✅ 加这一行
        
        // 初始化模式选择器事件
        this._initModeSelector();
    }

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
        
        let content = `<div class="message-content">${this.markdownToHtml(message)}</div>`;
        
        if (sources && sources.length > 0) {
            content += this._buildSourcesHtml(sources);
        }
        
        messageDiv.innerHTML = content;
        this.chatHistory.appendChild(messageDiv);
        
        this._highlightCode(messageDiv);
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
     * 处理流式内容（只做一次，不重复处理）
     */
    _processStreamContent(element) {
        if (!element) return;
        
        // ✅ 获取纯文本
        const plainText = element.textContent;
        
        // ✅ 转换为 HTML
        const htmlContent = this.markdownToHtml(plainText);
        
        // ✅ 设置 HTML
        element.innerHTML = htmlContent;
        
        // ✅ 最后才高亮
        this._highlightCode(element);
    }

    updateStreamMessage(text) {
        if (!text) return;
        
        if (typeof text !== 'string') {
            text = String(text);
        }
        
        if (this.currentMessageEl) {
            const contentDiv = this.currentMessageEl.querySelector('.stream-content');
            if (contentDiv) {
                // ✅ 只追加纯文本到 textContent
                contentDiv.textContent += text;
                
                // ✅ 延迟处理
                clearTimeout(this._highlightTimeout);
                this._highlightTimeout = setTimeout(() => {
                    this._processStreamContent(contentDiv);
                }, 300);
                
                this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
            }
        }
    }

    /**
     * 延迟高亮（防止频繁重排）
     */
    _scheduleHighlight(element) {
        if (this._highlightTimeout) {
            clearTimeout(this._highlightTimeout);
        }
        
        this._highlightTimeout = setTimeout(() => {
            // ✅ 现在才转换 Markdown 为 HTML
            const text = element.textContent;
            element.innerHTML = this.markdownToHtml(text);
            
            // ✅ 然后高亮代码块
            this._highlightCode(element);
            
            this._highlightTimeout = null;
        }, 300);  // 300ms 延迟，等待流数据稳定
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
        let sourcesHtml = '<div class="sources-container"><strong>📚 相关文档：</strong><ul>';
        const addedSources = new Set();
        
        for (const source of sources) {
            const filename = source.source || source.filename || source.name || 'Unknown';
            
            if (addedSources.has(filename)) continue;
            addedSources.add(filename);
            
            sourcesHtml += `<li><strong>${this.escapeHtml(filename)}</strong></li>`;
        }
        
        sourcesHtml += '</ul></div>';
        return sourcesHtml;
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
     * Markdown 转 HTML（改进版，处理代码块更严谨）
     */
    markdownToHtml(text) {
        if (!text) return '';
        
        // ✅ 如果已经包含高亮后的 HTML，直接返回
        if (text.includes('hljs') || text.includes('data-highlighted')) {
            return text;
        }
        
        const codeBlocks = [];
        let html = text;
        
        // ✅ 提取代码块：```language\n...code...\n```
        html = html.replace(/```([a-z0-9\-_]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
            const cleanCode = code.trim()
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            // ✅ 确保语言标签不为空或只有空格
            const langTrimmed = lang ? lang.trim() : '';
            const langAttr = langTrimmed ? `class="language-${langTrimmed}"` : 'class="language-plaintext"';
            
            codeBlocks.push(`<pre><code ${langAttr}>${cleanCode}</code></pre>`);
            return placeholder;
        });
        
        // ✅ 提取代码块：```...code...```（不带语言）
        html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
            const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
            const cleanCode = code.trim()
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            codeBlocks.push(`<pre><code class="language-plaintext">${cleanCode}</code></pre>`);
            return placeholder;
        });
        
        // ✅ 转义剩余的 HTML
        html = this.escapeHtml(html);
        
        // ✅ 恢复代码块
        for (let i = 0; i < codeBlocks.length; i++) {
            html = html.replace(`__CODEBLOCK_${i}__`, codeBlocks[i]);
        }
        
        // ✅ 行内代码
        html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
        
        // ✅ 加粗
        html = html.replace(/\*\*([^\*]+?)\*\*/g, '<strong>$1</strong>');
        
        // ✅ 斜体
        html = html.replace(/\*([^\*\n]+?)\*/g, '<em>$1</em>');
        
        // ✅ 换行
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }

}
