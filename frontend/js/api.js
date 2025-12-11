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
}


// 创建全局 API 实例
const api = new API();
