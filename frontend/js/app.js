// frontend/js/app.js
class App {
    constructor() {
        this.ui = new UI();
        this.api = new API();
        this.conversationMode = 'auto'; // 'auto', 'kb', 'llm'
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadStats();
        this.initDocMgmt();
    }

    bindEvents() {
        this.ui.bindSendButton(() => this.handleQuery());
        this.ui.bindFileInputChange((files) => this.handleFileUpload(files));
        this.ui.bindClearKBButton(() => this.handleClearKB());
        this.ui.bindRefreshStatsButton(() => this.loadStats());
        this.ui.bindDocumentDelete((filename) => this.handleDeleteDocument(filename));
        // 绑定模式改变事件
        this.ui.bindModeChange((mode) => this.setMode(mode));
    }

    /**
     * 文档管理模块初始化
     */
    initDocMgmt() {
        if (!this.ui.docMgmtPanel) return;
        // 加载文档列表
        this.loadDocMgmtList();
        // 刷新按钮
        if (this.ui.docRefreshBtn) {
            this.ui.docRefreshBtn.addEventListener('click', () => this.loadDocMgmtList());
        }
        // 搜索
        if (this.ui.docSearchInput) {
            this.ui.docSearchInput.addEventListener('input', () => this.filterDocMgmtTable());
        }
        // 批量删除
        if (this.ui.docBatchDeleteBtn) {
            this.ui.docBatchDeleteBtn.addEventListener('click', () => this.handleBatchDeleteDocs());
        }
        // 全选
        if (this.ui.docSelectAll) {
            this.ui.docSelectAll.addEventListener('change', (e) => this.toggleSelectAllDocs(e.target.checked));
        }
        // 表格事件委托（详情/删除）
        if (this.ui.docMgmtTableBody) {
            this.ui.docMgmtTableBody.addEventListener('click', (e) => this.handleDocMgmtTableClick(e));
        }
        // 自动轮询：当文档管理面板可见时每 10 秒刷新一次列表
        this._docMgmtPoll = setInterval(() => {
            try {
                if (this.ui.docMgmtPanel && this.ui.docMgmtPanel.style.display !== 'none') {
                    this.loadDocMgmtList();
                }
            } catch (e) {
                console.debug('docMgmt poll error', e);
            }
        }, 10000);
        // 绑定详情中的重建索引回调
        this.ui.bindReindexDocument(async (filename) => {
            if (!filename) return;
            try {
                this.ui.showLoading('重建索引中...');
                const res = await this.api.request('POST', `/documents/${encodeURIComponent(filename)}/reindex`);
                this.ui.hideLoading();
                if (res && res.message) {
                    this.ui.showNotification(res.message, 'success');
                    await this.loadStats();
                    await this.loadDocMgmtList();
                } else {
                    this.ui.showNotification('重建索引响应异常', 'error');
                }
            } catch (err) {
                this.ui.hideLoading();
                this.ui.showNotification('重建失败: ' + err.message, 'error');
            }
        });
    }

    async loadDocMgmtList() {
        try {
            const res = await this.api.listDocuments();
            // 后端返回 { files: [...] }
            this._docMgmtFiles = res.files || [];
            this.ui.renderDocMgmtTable(this._docMgmtFiles);
        } catch (err) {
            this.ui.renderDocMgmtTable([]);
            this.ui.showNotification('加载文档列表失败: ' + err.message, 'error');
        }
    }

    filterDocMgmtTable() {
        const keyword = this.ui.docSearchInput.value.trim().toLowerCase();
        if (!keyword) {
            this.ui.renderDocMgmtTable(this._docMgmtFiles || []);
            return;
        }
        const filtered = (this._docMgmtFiles || []).filter(f => f.name && f.name.toLowerCase().includes(keyword));
        this.ui.renderDocMgmtTable(filtered);
    }

    toggleSelectAllDocs(checked) {
        const checkboxes = this.ui.docMgmtTableBody.querySelectorAll('.doc-select');
        checkboxes.forEach(cb => { cb.checked = checked; });
    }

    async handleBatchDeleteDocs() {
        const selected = Array.from(this.ui.docMgmtTableBody.querySelectorAll('.doc-select:checked'))
            .map(cb => cb.dataset.filename);
        if (selected.length === 0) {
            this.ui.showNotification('请先选择要删除的文档', 'warning');
            return;
        }
        this.ui.showConfirmModal(`确定要批量删除 ${selected.length} 个文档吗？`, async (confirmed) => {
            if (!confirmed) return;
            let success = 0, fail = 0;
            for (const name of selected) {
                try {
                    await this.api.deleteDocument(name);
                    success++;
                } catch {
                    fail++;
                }
            }
            this.ui.showNotification(`批量删除完成，成功${success}，失败${fail}`,'info');
            await this.loadDocMgmtList();
        });
    }

    async handleDocMgmtTableClick(e) {
        const target = e.target;
        if (target.classList.contains('doc-delete-btn')) {
            const filename = target.dataset.filename;
            if (!filename) return;
            this.ui.showConfirmModal(`确定要删除文档 "${filename}" 吗？`, async (confirmed) => {
                if (!confirmed) return;
                try {
                    await this.api.deleteDocument(filename);
                    this.ui.showNotification('✓ 文档已删除', 'success');
                    await this.loadDocMgmtList();
                } catch (err) {
                    this.ui.showNotification('删除失败: ' + err.message, 'error');
                }
            });
        } else if (target.classList.contains('doc-detail-btn')) {
            const filename = target.dataset.filename;
            if (!filename) return;

            try {
                const res = await this.api.request('GET', `/documents/${encodeURIComponent(filename)}/detail`);
                if (res && res.file) {
                    this.ui.showDocumentDetail(res.file);
                } else {
                    this.ui.showNotification('获取详情失败', 'error');
                }
            } catch (err) {
                this.ui.showNotification('获取详情失败: ' + err.message, 'error');
            }
        }
    }

    async handleQuery() {
        const question = this.ui.getQuestion();
        if (!question) {
            this.ui.showNotification('请输入问题', 'warning');
            return;
        }

        this.ui.clearInput();
        this.ui.addUserMessage(question);
        this.ui.setSendButtonState(false);
        this.ui.stopBtn.style.display = 'inline-block';

        try {
            const useStream = this.ui.shouldUseStream();
            const topK = this.ui.getTopK();

            const requestData = {
                question: question,
                mode: this.conversationMode,
                use_stream: useStream,
                top_k: topK
            };

            if (useStream) {
                await this.handleStreamQuery(requestData);
            } else {
                await this.handleNormalQuery(requestData);
            }
        } catch (error) {
            console.error('查询失败:', error);
            this.ui.showNotification('查询失败: ' + error.message, 'error');
        } finally {
            this.ui.setSendButtonState(true);
            this.ui.stopBtn.style.display = 'none';
        }
    }

    async handleNormalQuery(requestData) {
        try {
            const response = await this.api.query(requestData);
            
            if (response.type === 'response') {
                const answer = response.answer;
                const sources = response.sources || [];
                
                let modeLabel = '';
                if (response.mode === 'kb') {
                    modeLabel = '📚 知识库';
                } else if (response.mode === 'llm') {
                    modeLabel = '🤖 直接AI';
                }
                
                const message = modeLabel ? `[${modeLabel}]\n${answer}` : answer;
                this.ui.addAssistantMessage(message, sources);
            }
        } catch (error) {
            throw error;
        }
    }

    async handleStreamQuery(requestData) {
        try {
            console.log('🚀 开始流式查询，模式:', this.conversationMode);  // ← 添加这行
            this.ui.addStreamMessage();

            const response = await this.api.queryStream(requestData);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let modeLabel = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('✅ 流式传输完成');  // ← 添加这行
                    break;
                }

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n').filter(line => line.trim());
                console.log(`📥 收到 ${lines.length} 行数据`);  // ← 添加这行

                for (const line of lines) {
                    try {
                        const data = JSON.parse(line);
                        console.log(`📋 数据类型: ${data.type}`);  // ← 看一下类型

                        if (data.type === 'start') {
                            // ✅ 只在这里打印 START 相关信息
                            console.log('✅ START 信号接收到:');
                            console.log('   sources:', data.sources);
                            console.log('   sources 类型:', typeof data.sources);
                            console.log('   sources[0]:', data.sources?.[0]);
                            console.log('   sources[0] 类型:', typeof data.sources?.[0]);

                            if (data.mode === 'kb') {
                                modeLabel = '📚 知识库';
                            } else if (data.mode === 'llm') {
                                modeLabel = '🤖 直接AI';
                            }
                            
                            if (modeLabel) {
                                this.ui.updateStreamMessage(`[${modeLabel}]\n`);
                            }

                            if (data.sources && data.sources.length > 0) {
                                this.ui.showSources(data.sources);
                            }
                        } else if (data.type === 'stream') {
                            console.log(`📝 收到流数据，长度: ${data.data.length}`);  // ← 可选
                            this.ui.updateStreamMessage(data.data);
                        } else if (data.type === 'done') {
                            console.log('✨ 完成信号');  // ← 可选
                        } else if (data.type === 'error') {
                            console.error('❌ 错误:', data.message);
                            this.ui.showNotification(data.message, 'error');
                        }
                    } catch (e) {
                        console.error('❌ 解析流数据失败:', e);
                        console.error('   原始行:', line);
                    }
                }
            }
        } catch (error) {
            console.error('❌ 流式查询异常:', error);
            throw error;
        }
    }


    async handleFileUpload(files) {
        // 检查文件是否选择
        if (!files || files.length === 0) {
            this.ui.showNotification('请选择文件', 'warning'); // 弹窗提示
            return;
        }

        // 调用 UI 层的方法，显示上传进度条
        this.ui.showUploadProgress();
        
        try {
            /*使用 API 层的方法，注册进度回调
            * 
            * await 表示等待异步操作完成
            * 
            * uploadFilesWithProgress 是 API 层的方法，接受文件数组和进度回调函数
            * 
            * 进度回调函数接受一个 progressData 对象作为参数
            * 
            * progressData表示一个包含上传进度信息的对象，例如：
            * {
            *   stage: "uploading", // 上传阶段，例如 "uploading"、"processing" 等
            *   progress: 50, // 上传进度，0-100
            *   message: "正在上传文件..." // 上传阶段的描述信息
            * }
            * 
            * result 是上传完成后的结果，例如：
            * {
            *   added_chunks: 123, // 添加的chunks数量
            *   other_info: "其他信息"
            * }
            */
            const result = await this.api.uploadFilesWithProgress(
                files,
                (progressData) => {
                    // 这里处理进度更新
                    console.log(`📊 ${progressData.stage}: ${progressData.progress}%`);
                    this.ui.updateUploadProgress(
                        progressData.progress,
                        progressData.message
                    );
                }
            );

            // 上传完成, 隐藏上传进度条
            this.ui.hideUploadProgress();
            
            // ✅ 检查 result 是否有效
            if (!result) {
                throw new Error('上传结果无效');
            }

            this.ui.showNotification(
                `✅ 成功上传！已添加 ${result.added_chunks} 个chunks`,
                'success'
            );
            
            // 刷新统计
            await this.loadStats();

        } catch (error) {
            console.error('❌ 上传失败:', error);
            this.ui.hideUploadProgress();
            this.ui.showNotification('❌ 上传失败: ' + error.message, 'error');
        }
    }

    async handleClearKB() {
        this.ui.showConfirmModal('确定要清空知识库吗？此操作不可撤销。', async (confirmed) => {
            if (confirmed) {
                this.ui.showLoading('清空中...');
                try {
                    await this.api.clearKB();
                    this.ui.hideLoading();
                    this.ui.showNotification('✓ 知识库已清空', 'success');
                    this.ui.clearChatHistory();
                    await this.loadStats();
                } catch (error) {
                    this.ui.hideLoading();
                    this.ui.showNotification('清空失败: ' + error.message, 'error');
                }
            }
        });
    }

    async handleDeleteDocument(filename) {
        this.ui.showConfirmModal(
            `确定要删除文档 "${filename}" 吗？`,
            async (confirmed) => {
                if (confirmed) {
                    this.ui.showLoading('删除中...');
                    try {
                        await this.api.deleteDocument(filename);
                        this.ui.hideLoading();
                        this.ui.showNotification('✓ 文档已删除', 'success');
                        await this.loadStats();
                    } catch (error) {
                        this.ui.hideLoading();
                        this.ui.showNotification('删除失败: ' + error.message, 'error');
                    }
                }
            }
        );
    }

    async loadStats() {
        try {
            const stats = await this.api.getStats();
            this.ui.updateStats(stats);
            this.ui.updateDocumentsList(stats.files || []);
        } catch (error) {
            console.error('加载统计失败:', error);
        }
    }

    setMode(mode) {
        this.conversationMode = mode;
        console.log('切换到模式:', mode);
    }
}

// 初始化应用
const app = new App();
