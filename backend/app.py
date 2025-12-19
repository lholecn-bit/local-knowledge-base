# backend/app.py

import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from knowledge_base import LocalKnowledgeBase
from pathlib import Path
import traceback
import json

"""
Python为脚本语言，写在前面的部分会被优先执行
和CPP不同，Python并没有main函数的概念，所有顶层代码都会被执行
所以，要确保初始化代码在这里执行 :load_dotenv()
"""
load_dotenv()

"""
Python 是 “脚本语言 + 模块语言”，一个 .py 文件既可以作为可执行脚本，也可以作为模块被其他脚本导入。例如：
如果你在另一个文件中写 import app，此时 app.py 会被当作模块加载，全局代码（如初始化 app、kb）仍会执行，
但 if __name__ == '__main__': 块会被跳过（因为 __name__ 此时是 app 而非 __main__）。
这种设计让代码既能独立运行，又能被复用（作为模块提供功能），比 C++ 单一的 main 入口更灵活。
所以，app = Flask(__name__)可以不在 main 函数中。
"""
# 初始化 Flask 应用 
app = Flask(__name__)

"""
 浏览器有一个 “同源策略” 安全机制：
 默认情况下，只有当前端（如 http://localhost:3000）和后端（如 http://localhost:5000）的协议、域名、端口完全一致时，前端才能正常调用后端 API。
 如果不一致（比如端口不同），浏览器会拦截请求，导致跨域错误。
 你的应用中，前端地址是 http://localhost:3000，后端是 http://localhost:5000，属于跨域场景，
 因此必须配置 CORS 允许跨域访问。
"""
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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '')

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


# 初始化 LLM 客户端
from llm_client import LLMClient

try:
    # 初始化 LLM 客户端（全局复用）
    llm_client = LLMClient(
        api_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        api_key=os.getenv('OPENAI_API_KEY'),
        model=os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
    )
    print("✅ LLM 客户端初始化成功！")
except Exception as e:
    print(f"❌ LLM 客户端初始化失败: {e}")
    llm_client = None



# ==================== API 端点 ====================

@app.route('/api/kb/stats', methods=['GET', 'OPTIONS'])  
def get_kb_stats():
    """获取知识库统计信息"""
    if request.method == 'OPTIONS':  
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

@app.route('/api/kb/search', methods=['POST', 'OPTIONS'])  
def search_kb():
    """搜索知识库"""
    if request.method == 'OPTIONS':  
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


@app.route('/api/kb/query', methods=['POST', 'OPTIONS'])  
def query_kb():
    """查询知识库"""
    if request.method == 'OPTIONS':  
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
    """OPTIONS 是浏览器的 “跨域权限询问”，返回 204 空响应是告诉浏览器 “允许该请求”，为后续实际请求铺路。"""
    if request.method == 'OPTIONS': 
        return '', 204
    """
    关于return的内容:
    HTTP 协议（IETF 制定）要求必须返回状态码，且如果有响应体，需通过 Content-Type 标识格式；
    jsonify() 自动加 Content-Type 头、return 内容, 状态码 符合 HTTP 响应格式
    """
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
                print(f"开始流式查询处理...")
                
                if not llm_client:
                    yield json.dumps({
                        'type': 'error',
                        'message': 'LLM 客户端未初始化'
                    }) + '\n'
                    return
                print(f"   ✅ LLM 客户端已初始化")
                
                # ✅ 关键改动：根据 mode 决定是否搜索
                sources = []
                actual_mode = mode
                
                if mode == 'llm':
                    # ✅ 优化：LLM 模式下不搜索知识库
                    print(f"   📋 模式: 直接 LLM，跳过知识库搜索")
                    yield json.dumps({
                        'type': 'start',
                        'mode': mode,
                        'sources': []
                    }) + '\n'
                    
                    answer = llm_client.chat(question)
                    actual_mode = 'llm'
                
                elif mode == 'kb':
                    # ✅ 知识库模式：必须搜索
                    print(f"   📚 模式: 知识库")
                    search_results = kb.search(question, top_k, use_reranking=True)
                    has_relevant_docs = search_results.get('has_results', False)
                    sources = [doc['source'] for doc in search_results['results']] if has_relevant_docs else []
                    sources = list(dict.fromkeys(sources))  # 去重
                    
                    print(f"   📊 搜索结果: {len(search_results['results'])} 个文档")
                    print(f"   📄 相关文档: {sources}")
                    
                    yield json.dumps({
                        'type': 'start',
                        'mode': mode,
                        'sources': sources
                    }) + '\n'
                    
                    if has_relevant_docs:
                        answer = _rag_query(question, search_results, llm_client)
                        actual_mode = 'kb'
                        print(f"   ✅ 知识库 RAG 模式")
                    else:
                        answer = llm_client.chat(question)
                        actual_mode = 'llm'
                        print(f"   ⚠️  知识库无相关文档，降级到 LLM")
                
                elif mode == 'auto':
                    # ✅ 自动模式：先搜索再判断
                    print(f"   🔄 模式: 自动")
                    search_results = kb.search(question, top_k, use_reranking=True)
                    has_relevant_docs = search_results.get('has_results', False)
                    sources = [doc['source'] for doc in search_results['results']] if has_relevant_docs else []
                    sources = list(dict.fromkeys(sources))  # 去重
                    
                    print(f"   📊 搜索结果: {len(search_results['results'])} 个文档")
                    print(f"   📄 相关文档: {sources}")
                    print(f"   ✅ 有相关文档: {has_relevant_docs}")
                    
                    yield json.dumps({
                        'type': 'start',
                        'mode': mode,
                        'sources': sources
                    }) + '\n'
                    
                    if has_relevant_docs:
                        answer = _rag_query(question, search_results, llm_client)
                        actual_mode = 'kb'
                        print(f"   🔄 自动模式：有相关文档，使用 RAG")
                    else:
                        answer = llm_client.chat(question)
                        actual_mode = 'llm'
                        print(f"   🔄 自动模式：无相关文档，使用纯 LLM")
                
                else:
                    answer = "未知的查询模式"
                    actual_mode = mode
                    yield json.dumps({
                        'type': 'start',
                        'mode': mode,
                        'sources': []
                    }) + '\n'
                
                # ✅ 流式发送答案 
                yield json.dumps({
                    'type': 'stream',
                    'data': answer,
                    'actual_mode': actual_mode
                }) + '\n'
                
                yield json.dumps({
                    'type': 'done',
                    'actual_mode': actual_mode
                }) + '\n'
                
                print(f"   ✅ 查询完成\n")
            
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
    
    Args:
        question: 用户问题
        search_results: 搜索结果（包含 results 列表）
        llm: LLM 客户端
    
    Returns:
        LLM 生成的答案
    """
    # 格式化知识库内容
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

@app.route('/api/clear', methods=['POST', 'OPTIONS']) 
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


@app.route('/api/documents/list', methods=['GET', 'OPTIONS'])  
def list_documents():
    """列出所有文档"""
    if request.method == 'OPTIONS':  
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        stats = kb.get_stats()
        return jsonify({'files': stats.get('files', [])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/documents/<filename>', methods=['DELETE', 'OPTIONS'])  
def delete_document(filename):
    """删除文档"""
    if request.method == 'OPTIONS':  
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        kb.delete_document(filename)
        return jsonify({'message': f'文档已删除: {filename}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET', 'OPTIONS'])  
def health_check():
    """健康检查"""
    if request.method == 'OPTIONS':  
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
        print("📍 后端地址: http://localhost:5000")
        print("="*60 + "\n")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("\n❌ 知识库初始化失败，无法启动应用")
        print("   请检查 .env 文件和依赖安装\n")
