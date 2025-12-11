# backend/app.py

import os
from dotenv import load_dotenv

# 🔴 最重要：在最开始加载 .env 文件
load_dotenv()

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from knowledge_base import LocalKnowledgeBase
from pathlib import Path
import traceback
import json

# 初始化 Flask 应用
app = Flask(__name__)

# ✅ 改进的 CORS 配置 - 支持流式响应
CORS(app, 
     resources={r"/api/*": {
         "origins": "*",
         "methods": ["GET", "POST", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization"],
         "supports_credentials": True,
         "max_age": 3600
     }},
     expose_headers=["Content-Type", "X-Total-Count"],
     stream=True)  # ✅ 关键！支持流式响应

# 从环境变量读取配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# 初始化知识库
print("\n" + "="*60)
print("🚀 初始化本地知识库系统")
print("="*60)

try:
    kb = LocalKnowledgeBase()
    print("✅ 知识库初始化成功！\n")
except Exception as e:
    print(f"❌ 知识库初始化失败: {e}")
    print(f"   请检查 .env 文件中是否有 OPENAI_API_KEY")
    traceback.print_exc()
    kb = None


# ==================== API 端点 ====================

@app.route('/api/kb/stats', methods=['GET', 'OPTIONS'])  # ✅ 加 OPTIONS
def get_kb_stats():
    """获取知识库统计信息"""
    if request.method == 'OPTIONS':  # ✅ 加这个
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        stats = kb.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/upload', methods=['POST', 'OPTIONS'])
def upload_documents():
    """上传文档到知识库"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        print("\n" + "="*60)
        print("📤 收到上传请求")
        print("="*60)
        
        # 检查是否有文件
        if 'files' not in request.files:
            print("❌ 错误：request.files 中没有 'files' 键")
            print(f"   request.files 的键: {list(request.files.keys())}")
            return jsonify({'error': '没有上传文件'}), 400
        
        files = request.files.getlist('files')
        print(f"✅ 获取到 {len(files)} 个文件")
        
        if not files or all(f.filename == '' for f in files):
            print("❌ 错误：文件列表为空或文件名为空")
            return jsonify({'error': '文件列表为空'}), 400
        
        # 打印文件信息
        for idx, file in enumerate(files):
            print(f"  文件 {idx+1}: {file.filename} (类型: {type(file).__name__})")
        
        # ✅ 直接传递 FileStorage 列表
        result = kb.add_documents_from_upload(files)
        
        print("="*60)
        print(f"✅ 上传结果: {result}\n")
        return jsonify(result), 200
    
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        return jsonify({'error': str(e)}), 500



@app.route('/api/kb/search', methods=['POST', 'OPTIONS'])  # ✅ 加 OPTIONS
def search_kb():
    """搜索知识库"""
    if request.method == 'OPTIONS':  # ✅ 加这个
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', 3)
        
        if not query:
            return jsonify({'error': '查询内容不能为空'}), 400
        
        result = kb.search(query, top_k)
        return jsonify(result), 200
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/kb/query', methods=['POST', 'OPTIONS'])  # ✅ 加 OPTIONS
def query_kb():
    """查询知识库"""
    if request.method == 'OPTIONS':  # ✅ 加这个
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        top_k = data.get('top_k', 3)
        
        if not question:
            return jsonify({'error': '问题不能为空'}), 400
        
        result = kb.query(question, top_k)
        return jsonify(result), 200
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/stream-query', methods=['POST', 'OPTIONS'])
def stream_query():
    """✅ 流式查询端点 - 正确的 RAG 实现"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        mode = data.get('mode', 'auto')
        top_k = data.get('top_k', 3)
        
        if not question:
            return jsonify({'error': '问题不能为空'}), 400
        
        print(f"\n🔍 流式查询: {question}")
        print(f"   模式: {mode}, topK: {top_k}")
        
        def generate():
            try:
                from llm_client import LLMClient
                
                llm = LLMClient(
                    api_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                    api_key=os.getenv('OPENAI_API_KEY'),
                    model=os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
                )
                
                # ✅ 第一步：搜索知识库（无论什么模式都先搜索）
                search_results = kb.search(question, top_k)
                sources = [doc['source'] for doc in search_results['results']]
                
                # 发送开始信号
                yield json.dumps({
                    'type': 'start',
                    'mode': mode,
                    'sources': sources
                }) + '\n'
                
                # ✅ 第二步：根据模式构建提示词并调用 LLM
                if mode == 'kb':
                    # RAG 模式：知识库 + LLM
                    answer = _rag_query(question, search_results, llm)
                
                elif mode == 'llm':
                    # 直接 LLM 模式：忽略知识库
                    answer = llm.chat(question)
                
                elif mode == 'auto':
                    # 自动模式：有相关内容则 RAG，无则直接 LLM
                    if search_results['results']:
                        answer = _rag_query(question, search_results, llm)
                    else:
                        answer = llm.chat(question)
                
                else:
                    answer = "未知的查询模式"
                
                # ✅ 第三步：流式发送答案
                yield json.dumps({
                    'type': 'stream',
                    'data': answer
                }) + '\n'
                
                # 发送完成信号
                yield json.dumps({'type': 'done'}) + '\n'
            
            except Exception as e:
                print(f"❌ 流式查询错误: {e}")
                import traceback
                traceback.print_exc()
                yield json.dumps({
                    'type': 'error',
                    'message': str(e)
                }) + '\n'
        
        return Response(
            generate(),
            mimetype='application/x-ndjson',
            headers={
                'Content-Type': 'application/x-ndjson; charset=utf-8',
                'Cache-Control': 'no-cache',
                'Transfer-Encoding': 'chunked'
            }
        )
    
    except Exception as e:
        print(f"❌ 流式查询失败: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _rag_query(question, search_results, llm):
    """
    RAG 查询：将知识库内容和问题一起发给 LLM
    """
    # ✅ 格式化知识库内容
    context_parts = []
    for doc in search_results['results']:
        context_parts.append(f"【{doc['source']}】\n{doc['content']}")
    context = "\n\n".join(context_parts)
    
    # ✅ 构建 RAG 提示词
    rag_prompt = f"""你是一个专业的助手。请根据以下知识库中的内容，回答用户的问题。

【知识库内容】
{context}

【用户问题】
{question}

请求解释：
1. 优先使用知识库中的信息回答
2. 如果知识库中没有相关信息，请明确说明
3. 保持回答清晰、准确、有条理
4. 必要时可以引用知识库的具体内容

回答："""
    
    # ✅ 调用 LLM
    answer = llm.chat(rag_prompt)
    return answer



@app.route('/api/clear', methods=['POST', 'OPTIONS'])  # ✅ 改这里！改为 /api/clear
def clear_kb():
    """清空知识库"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        print("\n" + "="*60)
        print("🗑️  清空知识库")
        print("="*60)
        
        kb.clear()
        
        print("✅ 知识库已清空\n")
        return jsonify({'message': '知识库已清空'}), 200
    except Exception as e:
        print(f"❌ 清空失败: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/list', methods=['GET', 'OPTIONS'])  # ✅ 加 OPTIONS
def list_documents():
    """列出所有文档"""
    if request.method == 'OPTIONS':  # ✅ 加这个
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        stats = kb.get_stats()
        return jsonify({'files': stats.get('files', [])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/documents/<filename>', methods=['DELETE', 'OPTIONS'])  # ✅ 加 OPTIONS
def delete_document(filename):
    """删除文档"""
    if request.method == 'OPTIONS':  # ✅ 加这个
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        kb.delete_document(filename)
        return jsonify({'message': f'文档已删除: {filename}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET', 'OPTIONS'])  # ✅ 加 OPTIONS
def health_check():
    """健康检查"""
    if request.method == 'OPTIONS':  # ✅ 加这个
        return '', 204
    
    return jsonify({
        'status': 'ok',
        'kb_initialized': kb is not None
    }), 200


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '端点不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '内部服务器错误'}), 500


if __name__ == '__main__':
    if kb:
        print("\n" + "="*60)
        print("🌐 Flask 应用启动成功！")
        print("📍 访问地址: http://localhost:3000")
        print("📍 前端地址: http://localhost:5000")
        print("="*60 + "\n")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("\n❌ 知识库初始化失败，无法启动应用")
        print("   请检查 .env 文件和依赖安装\n")
