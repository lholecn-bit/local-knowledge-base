// frontend/js/api.js
const API_BASE = 'http://localhost:5000/api';

class API {
    constructor() {
        this.baseURL = API_BASE;
    }

    /**
     * 发送 HTTP 请求
     */
    async request(method, endpoint, data = null, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
            ...options,
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API 错误:', error);
            throw error;
        }
    }

    /**
     * 健康检查
     */
    async health() {
        return this.request('GET', '/health');
    }

    /**
     * 获取知识库统计信息
     */
    async getStats() {
        return this.request('GET', '/kb/stats');
    }

    /**
     * 清空知识库
     */
    async clearKB() {
        return this.request('POST', '/clear');
    }

    /**
     * 上传文档（单个）
     */
    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('files', file);  // ✅ 改为 'files'（复数）

        const url = `${this.baseURL}/documents/upload`;
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    /**
     * 上传多个文档
     */
    async uploadFiles(files) {
        const formData = new FormData();

        // ✅ 改进：一次性上传所有文件，而不是逐个上传
        for (const file of files) {
            formData.append('files', file);  // 多个文件都用 'files' 字段名
        }

        const url = `${this.baseURL}/documents/upload`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('上传文件失败:', error);
            throw error;
        }
    }

    /**
     * 列出文档
     */
    async listDocuments() {
        return this.request('GET', '/documents/list');
    }

    /**
     * 删除文档
     */
    async deleteDocument(filename) {
        return this.request('DELETE', `/documents/${encodeURIComponent(filename)}`);
    }

    /**
     * 搜索相关文档
     */
    async search(query, topK = 3) {
        return this.request('POST', '/search', {
            query,
            top_k: topK,
        });
    }

    /**
     * 查询知识库（普通查询）
     */
    async query(requestData) {
        return this.request('POST', '/stream-query', requestData);
    }

    /**
     * 流式查询
     */
    async queryStream(requestData) {
        const url = `${this.baseURL}/stream-query`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        return response;
    }

    /**
     * 上传文件（带进度条）- 流式传输
     * @param {FileList} files 文件列表
     * @param {Function} onProgress 进度回调：(progress, message) => {}
     * @returns {Promise} 上传完成结果
     */
    async uploadFilesWithProgress(files, onProgress = null) {
        // 上传文件时，使用 FormData 传递文件
        // formData是一个特殊的对象，用于构建 HTTP POST 请求的 body，可以包含文件和其他表单数据
        const formData = new FormData();

        // 将所有文件添加到 formData 中
        for (const file of files) {
            formData.append('files', file);
        }

        // 设置后端的上传进度接口
        const url = `${this.baseURL}/documents/upload-with-progress`;

        /*
        * 发送 POST 请求，上传文件

        * 常用的HTTP method包括
        - GET：获取资源
        - POST：创建或更新资源
        - PUT：更新资源
        - DELETE：删除资源
        - PATCH：部分更新资源
        - HEAD：获取资源的元数据
        - OPTIONS：获取服务器支持的 HTTP method
        - TRACE：回显服务器接收到的请求
        - CONNECT：用于代理服务器建立隧道连接

        * fetch 是一个用于发起 HTTP 请求的 API，它返回一个 Promise，当请求完成时，Promise 会被 resolve(意思是完成)或 reject(意思是出错)

        * fetch 的第二个参数是一个配置对象，用于指定 HTTP method、headers、body 等信息

        * fetch 的第一个参数是 URL，即要请求的服务器地址

        * response 是 fetch 的返回值，它是一个 Response 对象，包含服务器的响应信息
        * 如果 response.ok 为 true，表示请求成功；否则，表示请求失败
        * 如果 response.ok 为 false，可以使用 response.json() 解析响应体中的 JSON 数据，获取错误信息
        */
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // ✅ 核心：处理流式响应
        return this._handleStreamResponse(response, onProgress);
    }

    /**
     * 通用流式响应处理
     * @param {Response} response 流式响应对象
     * @param {Function} onProgress 进度回调：(progress, message) => {}
     * @returns {Promise} 处理结果
     */
    async _handleStreamResponse(response, onProgress = null) {
        // reader是一个 ReadableStreamDefaultReader 对象，用于从流中读取数据
        // decoder是一个 TextDecoder 对象，用于将二进制数据解码为文本
        // buffer是一个字符串，用于缓存从流中读取的不完整行
        // result是一个对象，用于存储最终的处理结果
        // hasError是一个布尔值，用于标记是否发生了错误
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let result = null;
        let hasError = false;

        try {
            while (true) {
                // 从流中读取数据,返回一个 Promise，当数据可用时，Promise 会被 resolve(意思是完成)或 reject(意思是出错)
                // Promise 的 resolve 值是一个包含 done 和 value 的对象，其中 done 表示流是否结束，value 表示读取到的数据
                const { done, value } = await reader.read();
                if (done) break;

                // 将二进制数据解码为文本并追加到缓冲区
                const text = decoder.decode(value);
                buffer += text;

                // 将缓冲区按行分割,其中最后一个元素是可能的不完整行,返回一个数组，其中每个元素是一个完整的行
                const lines = buffer.split('\n');

                // 处理所有完整的行
                for (let i = 0; i < lines.length - 1; i++) {
                    // 如果行不为空，尝试解析为 JSON
                    if (lines[i].trim()) {
                        try {
                            const data = JSON.parse(lines[i]);
                            // 为什么这个json里面自带了 type 字段？因为后端在处理流式上传时，会根据不同的阶段发送不同的 JSON 对象，其中 type 字段用于标识消息的类型
                            if (data.type === 'progress') {
                                // 进度更新
                                if (onProgress) {
                                    onProgress({
                                        progress: data.progress,
                                        stage: data.stage,
                                        message: data.message
                                    });
                                }
                            } else if (data.type === 'complete') {
                                // 上传完成 ✅
                                result = {
                                    success: true,
                                    added_chunks: data.added_chunks,
                                    files: data.files,
                                    errors: data.errors
                                };
                            } else if (data.type === 'error') {
                                // 错误信息 ❌
                                hasError = true;
                                throw new Error(data.message);
                            }
                        } catch (e) {
                            console.error('解析响应失败:', e);
                            console.error('   原始行:', lines[i]);
                            hasError = true;
                            throw e;
                        }
                    }
                }

                // 保存不完整的行到缓冲区
                buffer = lines[lines.length - 1];
            }

            // ✅ 重要：检查是否收到了 complete 消息
            if (!result && !hasError) {
                throw new Error('上传异常：未收到完成信号');
            }

            if (hasError && !result) {
                throw new Error('上传失败');
            }

            return result;

        } catch (error) {
            console.error('流式响应处理失败:', error);
            throw error;
        }
    }

}


// 创建全局 API 实例
const api = new API();
