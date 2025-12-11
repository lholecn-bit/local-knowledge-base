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
        if (files.length === 0) return;

        this.ui.showLoading('上传中...');
        try {
            const result = await this.api.uploadFiles(files);
            this.ui.hideLoading();
            this.ui.showNotification(
                `✓ 成功上传 ${result.added_chunks} 个文本块`,
                'success'
            );
            await this.loadStats();
        } catch (error) {
            this.ui.hideLoading();
            this.ui.showNotification('上传失败: ' + error.message, 'error');
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
