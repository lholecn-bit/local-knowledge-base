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

@app.route('/api/kb/stats', methods=['GET'])
def get_kb_stats():
    """获取知识库统计信息"""
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        stats = kb.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/upload', methods=['POST'])
def upload_documents():
    """上传文档到知识库"""
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        if 'files' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': '文件列表为空'}), 400
        
        print(f"\n📤 上传 {len(files)} 个文件...")
        result = kb.add_documents_from_upload(files)
        
        return jsonify(result), 200
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/kb/search', methods=['POST'])
def search_kb():
    """搜索知识库"""
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


@app.route('/api/kb/query', methods=['POST'])
def query_kb():
    """查询知识库"""
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
    """✅ 流式查询端点"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        mode = data.get('mode', 'auto')
        top_k = data.get('top_k', 3)
        use_stream = data.get('use_stream', True)
        
        if not question:
            return jsonify({'error': '问题不能为空'}), 400
        
        print(f"\n🔍 流式查询: {question}")
        print(f"   模式: {mode}, topK: {top_k}")
        
        # ✅ 使用生成器生成流式数据
        def generate():
            try:
                # 获取相关文档
                search_results = kb.search(question, top_k)
                sources = [doc['source'] for doc in search_results['results']]
                
                # 发送开始信号
                yield json.dumps({
                    'type': 'start',
                    'mode': mode,
                    'sources': sources
                }) + '\n'
                
                if mode == 'kb':
                    # 知识库模式：直接返回搜索结果
                    answer = "\n\n".join([
                        f"【{doc['source']}】\n{doc['content']}"
                        for doc in search_results['results']
                    ])
                    yield json.dumps({
                        'type': 'stream',
                        'data': answer or "知识库中未找到相关内容"
                    }) + '\n'
                
                elif mode == 'llm':
                    # LLM 模式：直接调用 LLM
                    from llm_client import LLMClient
                    
                    llm = LLMClient(
                        api_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                        api_key=os.getenv('OPENAI_API_KEY'),
                        model=os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
                    )
                    
                    # 同步调用 LLM（简单方式）
                    answer = llm.chat(question)
                    yield json.dumps({
                        'type': 'stream',
                        'data': answer
                    }) + '\n'
                
                else:  # auto 模式
                    # 如果有相关文档，先返回文档
                    if search_results['results']:
                        docs_answer = "\n\n".join([
                            f"【{doc['source']}】\n{doc['content']}"
                            for doc in search_results['results']
                        ])
                        yield json.dumps({
                            'type': 'stream',
                            'data': docs_answer
                        }) + '\n'
                    else:
                        # 没有相关文档，调用 LLM
                        from llm_client import LLMClient
                        
                        llm = LLMClient(
                            api_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                            api_key=os.getenv('OPENAI_API_KEY'),
                            model=os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
                        )
                        answer = llm.chat(question)
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
        
        # ✅ 返回流式响应
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


@app.route('/api/kb/clear', methods=['POST'])
def clear_kb():
    """清空知识库"""
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        kb.clear()
        return jsonify({'message': '知识库已清空'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/list', methods=['GET'])
def list_documents():
    """列出所有文档"""
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        stats = kb.get_stats()
        return jsonify({'files': stats.get('files', [])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    """删除文档"""
    if not kb:
        return jsonify({'error': '知识库未初始化'}), 500
    
    try:
        kb.delete_document(filename)
        return jsonify({'message': f'文档已删除: {filename}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
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
