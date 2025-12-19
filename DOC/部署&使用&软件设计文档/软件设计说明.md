### 知识库回答时序图

```mermaid
sequenceDiagram
    participant User as 👤 用户
    participant Frontend as 🌐 前端<br/>(app.js)
    participant FrontendUI as 🎨 UI<br/>(ui.js)
    participant AJAX as 📡 HTTP<br/>(api.js)
    participant Backend as 🔙 后端<br/>(app.py)
    participant KB as 📚 知识库<br/>(knowledge_base.py)
    participant LLM as 🤖 LLM<br/>(llm_client.py)

    User->>Frontend: 1️⃣ 选择「📚 知识库」模式
    Frontend->>Frontend: conversationMode = 'kb'
    
    User->>FrontendUI: 2️⃣ 输入问题 + 点击发送
    FrontendUI->>Frontend: 触发 handleQuery()
    
    Frontend->>FrontendUI: 3️⃣ 显示用户消息
    FrontendUI->>FrontendUI: addUserMessage(question)
    
    Frontend->>FrontendUI: 4️⃣ 创建流式消息容器
    FrontendUI->>FrontendUI: addStreamMessage()<br/>currentMessageEl = <div>
    
    Frontend->>AJAX: 5️⃣ 发起流式请求
    AJAX->>AJAX: POST /api/stream-query
    Note over AJAX: {<br/>  question: "问题",<br/>  mode: "kb",<br/>  top_k: 3,<br/>  use_stream: true<br/>}
    
    AJAX->>Backend: 6️⃣ HTTP 请求到后端
    
    Backend->>Backend: 7️⃣ stream_query() 接收请求
    Backend->>Backend: 解析 data.get('mode') = 'kb'
    
    alt mode == 'kb' (知识库模式)
        Backend->>KB: 8️⃣ kb.search(question, top_k=3)
        KB->>KB: 向量搜索 + 相似度匹配
        KB-->>Backend: 返回搜索结果列表
        
        Backend->>Backend: 9️⃣ 格式化搜索结果
        Backend->>Backend: answer = "【文件1】\n内容1\n\n【文件2】\n内容2"
        
        Backend->>AJAX: 🔟 yield start 信号
        Note over Backend: {<br/>  "type": "start",<br/>  "mode": "kb",<br/>  "sources": [...]<br/>}
        
        Backend->>AJAX: 1️⃣1️⃣ yield stream 数据
        Note over Backend: {<br/>  "type": "stream",<br/>  "data": "【文件1】\n..."<br/>}
        
        Backend->>AJAX: 1️⃣2️⃣ yield done 信号
        Note over Backend: {"type": "done"}
    else mode == 'auto' && 无相关文档
        Backend->>LLM: 调用 llm.chat(question)
        LLM->>LLM: 调用 OpenAI API
        LLM-->>Backend: 返回 AI 回答
        Backend->>AJAX: yield stream 数据
    end
    
    AJAX->>AJAX: 1️⃣3️⃣ 接收响应流
    
    loop 处理每一行 JSON 数据
        AJAX->>AJAX: 解析 JSON 行
        
        alt type == 'start'
            AJAX->>FrontendUI: 1️⃣4️⃣ 显示来源信息
            FrontendUI->>FrontendUI: showSources(sources)
        else type == 'stream'
            AJAX->>FrontendUI: 1️⃣5️⃣ 更新流式内容
            FrontendUI->>FrontendUI: updateStreamMessage(data)
            FrontendUI->>FrontendUI: contentDiv.textContent += data
            FrontendUI->>FrontendUI: 延迟 300ms 后处理
            FrontendUI->>FrontendUI: _scheduleHighlight()
            FrontendUI->>FrontendUI: markdownToHtml(文本)
            FrontendUI->>FrontendUI: _highlightCode()
            FrontendUI->>FrontendUI: hljs.highlightElement()
        else type == 'done'
            AJAX->>Frontend: 1️⃣6️⃣ 流结束
        else type == 'error'
            AJAX->>FrontendUI: 1️⃣7️⃣ 显示错误提示
            FrontendUI->>FrontendUI: showNotification(error)
        end
    end
    
    FrontendUI->>FrontendUI: 1️⃣8️⃣ 消息显示完成
    FrontendUI->>User: 💬 在聊天窗口显示回答

```

---

## 📝 流程说明

### 核心步骤

| 步骤 | 发生位置 | 具体操作 |
|------|---------|---------|
| 1️⃣-2️⃣ | 前端 | 用户选择模式 + 输入问题 |
| 3️⃣-4️⃣ | 前端 UI | 显示用户消息 + 创建助手消息容器 |
| 5️⃣-6️⃣ | HTTP 请求 | 发送流式请求到后端 |
| 7️⃣-9️⃣ | 后端逻辑 | 根据模式调用对应函数（知识库/LLM） |
| 🔟-1️⃣2️⃣ | 后端响应 | 流式发送 start → stream → done |
| 1️⃣3️⃣-1️⃣8️⃣ | 前端处理 | 接收流数据 → 转换 Markdown → 高亮代码 |

### 知识库模式的关键函数

```
前端:  app.js handleStreamQuery()
       └─ api.js queryStream()
          └─ POST /api/stream-query

后端:  app.py stream_query()
       └─ if mode == 'kb':
          └─ kb.search()  ← 🔑 调用知识库搜索
             └─ 返回搜索结果
```

---

## 🎯 对比：三种模式

如果你改成 **auto** 或 **llm** 模式，只有这一块不同：

```mermaid
graph TD
    A["Backend: stream_query()"]
    A -->|mode='kb'| B["kb.search<br/>返回知识库结果"]
    A -->|mode='llm'| C["llm.chat<br/>调用 OpenAI"]
    A -->|mode='auto'| D{有相关文档?}
    D -->|有| B
    D -->|无| C
    
    B --> E["格式化结果"]
    C --> E
    E --> F["流式发送给前端"]
```