🐳 **Docker 是最佳方案，我给你完整的教程！**

---

## 📚 Docker 基础概念

Docker 简单理解：

- **镜像（Image）**: 应用的"蓝图"，包含所有依赖
- **容器（Container）**: 运行中的镜像实例，隔离的环境
- **Dockerfile**: 定义如何构建镜像的文件

优势：

- ✅ 一致的开发/测试/生产环境
- ✅ 不需要担心依赖版本冲突
- ✅ 易于扩展和部署
- ✅ 容易迁移到其他服务器

---

## 🏗️ 完整的 Docker 方案

### Step 1：创建后端 Dockerfile

在 `backend/` 目录下创建 `Dockerfile`：

```dockerfile
# ===== 构建阶段（Builder Stage） =====
FROM python:3.10-slim as builder

WORKDIR /app

# 安装构建工具
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ===== 运行阶段（Runtime Stage） =====
FROM python:3.10-slim

WORKDIR /app

# 从 builder 阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads knowledge_db logs

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# 启动应用
CMD ["gunicorn", \
     "-w", "4", \
     "-b", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
```

**Dockerfile 说明：**

- 使用多阶段构建（Builder + Runtime），减小最终镜像大小
- `PYTHONUNBUFFERED=1` 使 Python 日志实时输出
- `HEALTHCHECK` 定期检查应用是否正常
- `gunicorn` 参数优化：
  - `-w 4`: 4 个 worker 进程
  - `--timeout 120`: 120 秒超时
  - `--access-logfile -`: 日志输出到 stdout

---

### Step 2：创建前端 Dockerfile

在 `frontend/` 目录下创建 `Dockerfile`：

```dockerfile
# ===== 使用 Nginx 作为 Web 服务器 =====
FROM nginx:alpine

# 复制前端文件到 Nginx 根目录
COPY . /usr/share/nginx/html/

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
```

---

### Step 3：创建 Nginx 配置

在 `frontend/` 目录下创建 `nginx.conf`：

```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 100M;

    root /usr/share/nginx/html;
    index index.html;

    # 前端资源
    location / {
        try_files $uri $uri/ /index.html;
        # 缓存配置
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    # 静态资源（CSS、JS、图片）
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

    # 后端 API 代理
    location /api/ {
        # 这里改成你的后端 URL
        proxy_pass http://backend:5000;
      
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
      
        # 流式响应支持
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Connection "keep-alive";
      
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # 健康检查端点
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

### Step 4：创建 Docker Compose 配置

在项目根目录创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  # 后端服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: knowledge-base-backend
    ports:
      - "5000:5000"
    environment:
      # ⚠️ 重要：从 .env 文件读取敏感信息
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://api.openai.com/v1}
      - LLM_MODEL=${LLM_MODEL:-gpt-3.5-turbo}
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
    volumes:
      # 数据持久化
      - ./backend/knowledge_db:/app/knowledge_db
      - ./backend/uploads:/app/uploads
      - ./backend/logs:/app/logs
    networks:
      - knowledge-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: knowledge-base-frontend
    ports:
      - "80:80"
    environment:
      - BACKEND_URL=http://backend:5000
    depends_on:
      - backend
    networks:
      - knowledge-network
    restart: unless-stopped

networks:
  knowledge-network:
    driver: bridge
```

**docker-compose.yml 说明：**

- `services`: 定义两个服务（前端 + 后端）
- `volumes`: 持久化数据（知识库、上传的文件）
- `networks`: 让两个容器可以通信
- `depends_on`: 前端依赖后端启动
- `restart: unless-stopped`: 自动重启（除非手动停止）

---

### Step 5：更新前端 API 配置

修改 `frontend/js/api.js`，使用环境变量：

```javascript
// frontend/js/api.js
// 从环境获取后端 URL，默认为 localhost
const API_BASE = window.location.origin.includes('localhost') 
    ? 'http://localhost:5000/api'  // 本地开发
    : '/api';  // Docker 中通过 Nginx 代理

class API {
    constructor() {
        this.baseURL = API_BASE;
        console.log('API 基础 URL:', this.baseURL);
    }
    // ... 其他代码保持不变
}
```

---

### Step 6：创建 .env 文件

在项目根目录创建 `.env`：

```bash
# OpenAI 配置
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 模型配置
LLM_MODEL=gpt-3.5-turbo

# Flask 配置
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-in-production

# 日志级别
LOG_LEVEL=INFO
```

⚠️ **重要**：`.env` 文件包含敏感信息，添加到 `.gitignore`：

```bash
# .gitignore
.env
.env.local
*.pyc
__pycache__/
.DS_Store
node_modules/
dist/
build/
```

---

## 🚀 使用 Docker 的命令

### 构建镜像

```bash
# 构建后端镜像
docker build -t knowledge-base-backend:latest ./backend

# 构建前端镜像
docker build -t knowledge-base-frontend:latest ./frontend

# 或使用 Docker Compose 一键构建所有
docker-compose build
```

### 启动服务

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看特定服务的日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止服务
docker-compose down

# 停止并删除数据
docker-compose down -v
```

### 常用命令

```bash
# 进入容器内部
docker-compose exec backend bash
docker-compose exec frontend sh

# 查看运行中的容器
docker-compose ps

# 重启服务
docker-compose restart backend

# 查看资源使用情况
docker stats

# 查看容器网络
docker network ls
docker network inspect knowledge_network

# 删除未使用的镜像和容器
docker system prune
docker system prune -a  # 删除所有未使用的
```

---

## 📁 最终项目结构

```
local-knowledge-base/
├── backend/
│   ├── Dockerfile                 # ✅ 后端镜像定义
│   ├── requirements.txt
│   ├── app.py
│   ├── config.py
│   ├── knowledge_base.py
│   ├── llm_client.py
│   ├── utils.py
│   ├── embeddings.py
│   ├── uploads/                   # 上传文件目录
│   ├── knowledge_db/              # 知识库数据
│   └── logs/                      # 应用日志
│
├── frontend/
│   ├── Dockerfile                 # ✅ 前端镜像定义
│   ├── nginx.conf                 # ✅ Nginx 配置
│   ├── index.html
│   ├── js/
│   │   ├── api.js
│   │   ├── ui.js
│   │   └── app.js
│   └── css/
│       └── style.css
│
├── docker-compose.yml             # ✅ Docker Compose 配置
├── .env                           # ✅ 环境变量（不上传到 Git）
├── .env.example                   # 环境变量示例（供参考）
├── .gitignore
└── README.md
```

---

## 🌍 部署到远程服务器

### 方案 A：传输 Docker 镜像

```bash
# 在本地保存镜像
docker save knowledge-base-backend:latest -o backend.tar
docker save knowledge-base-frontend:latest -o frontend.tar

# 传输到服务器
scp backend.tar user@server:/tmp/
scp frontend.tar user@server:/tmp/

# 在服务器上加载镜像
ssh user@server
docker load -i /tmp/backend.tar
docker load -i /tmp/frontend.tar
```

### 方案 B：在服务器上构建（推荐）

```bash
# 1. 登录服务器
ssh user@server

# 2. 克隆项目
git clone https://github.com/your-repo/local-knowledge-base.git
cd local-knowledge-base

# 3. 创建 .env 文件
cat > .env << EOF
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
FLASK_ENV=production
EOF

# 4. 构建并启动
docker-compose build
docker-compose up -d

# 5. 验证
docker-compose ps
curl http://localhost/  # 前端
curl http://localhost/api/health  # 后端
```

---

## 📊 监控和日志

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 查看最后 100 行
docker-compose logs --tail=100

# 只看后端日志
docker-compose logs -f backend

# 导出日志到文件
docker-compose logs > logs.txt
```

### 容器内查看文件

```bash
# 查看知识库数据
docker-compose exec backend ls -la knowledge_db/

# 查看上传的文件
docker-compose exec backend ls -la uploads/

# 进入容器调试
docker-compose exec backend python
```

---

## 🔧 常见问题

**Q: 前端访问不了后端 API？**

- A: 检查 `nginx.conf` 中的 `proxy_pass` 是否指向 `http://backend:5000`（服务名）
- 确保两个服务在同一个网络（`networks` 配置）

**Q: API Key 暴露怎么办？**

- A: 确保 `.env` 在 `.gitignore` 中，从不上传到 Git
- 在生产环境使用 Docker Secrets 或云平台的密钥管理服务

**Q: 如何清理旧的镜像和容器？**

```bash
docker system prune -a
docker volume prune
```

**Q: 如何限制容器资源使用？**

修改 `docker-compose.yml`：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## ✅ Docker 部署检查清单

- [ ] 已安装 Docker 和 Docker Compose
- [ ] 创建了 `backend/Dockerfile`
- [ ] 创建了 `frontend/Dockerfile` 和 `nginx.conf`
- [ ] 创建了 `docker-compose.yml`
- [ ] 创建了 `.env` 文件（包含 OPENAI_API_KEY）
- [ ] 更新了 `.gitignore`
- [ ] 运行 `docker-compose build` 成功
- [ ] 运行 `docker-compose up -d` 成功
- [ ] 验证前端访问：`http://localhost`
- [ ] 验证后端 API：`http://localhost/api/health`

---

## 🎯 下一步

Docker 部署后，可以考虑：

1. **CI/CD 流程**：使用 GitHub Actions 自动构建和部署
2. **容器编排**：使用 Kubernetes 管理多个容器
3. **日志收集**：ELK Stack（Elasticsearch + Logstash + Kibana）
4. **监控告警**：Prometheus + Grafana
5. **备份策略**：定期备份知识库数据

现在可以开始用 Docker 部署了！🚀
