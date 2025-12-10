# backend/knowledge_base.py

import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from datetime import datetime

try:
    from langchain_community.document_loaders import PDFPlumberLoader, TextLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: langchain components not fully installed: {e}")
    LANGCHAIN_AVAILABLE = False


class LocalKnowledgeBase:
    """本地知识库管理类"""
    
    def __init__(self, 
                 db_path: str = "./knowledge_db",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 openai_api_key: Optional[str] = None):
        """
        初始化知识库
        Args:
            db_path: 知识库数据库路径
            chunk_size: 文本块大小
            chunk_overlap: 文本块重叠
            openai_api_key: OpenAI API Key (如果为None，则从环境变量读取)
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.metadata_file = self.db_path / "metadata.json"
        
        # 获取 OpenAI API Key
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "❌ OPENAI_API_KEY 未设置！\n"
                "   请在 .env 文件中添加: OPENAI_API_KEY=sk-..."
            )
        
        # 初始化嵌入模型
        self.embeddings = None
        if LANGCHAIN_AVAILABLE:
            self.embeddings = self._init_embeddings()
        
        # 初始化向量数据库
        self.vector_store = None
        if self.embeddings:
            self.load_vector_store()
        
        # 加载文件元数据
        self.file_metadata = self._load_metadata()
    
    def _init_embeddings(self):
        """初始化 OpenAI Embeddings"""
        try:
            print(f"📦 初始化 OpenAI Embeddings (模型: text-embedding-3-small)...")
            
            # 🔴 清除代理环境变量，因为 OpenAI 不支持 SOCKS 代理
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            os.environ.pop('all_proxy', None)
            os.environ.pop('ALL_PROXY', None)
            
            # 读取自定义 API 端点
            api_base = os.getenv('OPENAI_BASE_URL')
            
            embeddings = OpenAIEmbeddings(
                api_key=self.api_key,
                model="text-embedding-3-small",
                api_base=api_base
            )
            print(f"✅ OpenAI Embeddings 初始化成功！")
            if api_base:
                print(f"   API 端点: {api_base}")
            return embeddings
        except Exception as e:
            print(f"❌ OpenAI Embeddings 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _load_metadata(self) -> Dict:
        """加载文件元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告：无法加载元数据: {e}")
        return {}
    
    def _save_metadata(self):
        """保存文件元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"错误：无法保存元数据: {e}")
    
    def load_vector_store(self):
        """加载向量数据库"""
        faiss_path = self.db_path / "faiss_index"
        
        if faiss_path.exists() and self.embeddings:
            try:
                self.vector_store = FAISS.load_local(
                    str(faiss_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"✅ 向量库已加载: {self.vector_store.index.ntotal} 个向量")
            except Exception as e:
                print(f"⚠️ 向量库加载失败: {e}")
                self.vector_store = None
    
    def save_vector_store(self):
        """保存向量数据库"""
        if not self.vector_store:
            print(f"⚠️ 向量库为空，无法保存")
            return False
        
        faiss_path = self.db_path / "faiss_index"
        try:
            self.vector_store.save_local(str(faiss_path))
            print(f"✅ 向量库已保存: {self.vector_store.index.ntotal} 个向量")
            return True
        except Exception as e:
            print(f"❌ 向量库保存失败: {e}")
            return False
    
    def add_documents(self, file_paths: List[str]) -> Dict:
        """添加文档到知识库"""
        if not self.embeddings:
            return {
                'added_chunks': 0,
                'files': [],
                'errors': [{'error': 'Embeddings 未初始化，无法添加文档'}]
            }
        
        all_documents = []
        processed_files = {}
        errors = []
        
        print(f"\n📂 开始处理 {len(file_paths)} 个文件...")
        
        for file_path in file_paths:
            path = Path(file_path)
            
            if path.is_file():
                docs, error = self._load_file(path)
                if error:
                    errors.append(error)
                else:
                    all_documents.extend(docs)
                    processed_files[str(path)] = len(docs)
            elif path.is_dir():
                for ext in ['*.pdf', '*.txt', '*.md']:
                    for file_path in path.glob(f"**/{ext}"):
                        docs, error = self._load_file(file_path)
                        if error:
                            errors.append(error)
                        else:
                            all_documents.extend(docs)
                            processed_files[str(file_path)] = len(docs)
        
        if not all_documents:
            return {
                'added_chunks': 0,
                'files': [],
                'errors': errors
            }
        
        # 分割文本
        print(f"✂️ 分割 {len(all_documents)} 个文档...")
        chunks = self._split_documents(all_documents)
        added_chunks = len(chunks)
        print(f"✅ 分割完成: {added_chunks} 个块")
        
        # 添加到向量数据库
        try:
            if self.vector_store is None:
                print(f"🆕 创建新向量库...")
                self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            else:
                print(f"➕ 向现有向量库添加文档...")
                self.vector_store.add_documents(chunks)
            
            print(f"✅ 向量库更新成功: 现在共 {self.vector_store.index.ntotal} 个向量")
            
            # 保存向量库
            self.save_vector_store()
        except Exception as e:
            print(f"❌ 添加到向量库失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'added_chunks': 0,
                'files': [],
                'errors': [{'error': f'向量库操作失败: {e}'}]
            }
        
        # 更新元数据
        for file_path, doc_count in processed_files.items():
            file_name = Path(file_path).name
            self.file_metadata[file_name] = {
                'path': file_path,
                'hash': self._calculate_file_hash(file_path),
                'added_time': datetime.now().isoformat(),
                'doc_count': doc_count,
                'chunks': added_chunks
            }
        
        self._save_metadata()
        print(f"💾 元数据已保存\n")
        
        return {
            'added_chunks': added_chunks,
            'files': list(processed_files.keys()),
            'errors': errors
        }
    
    def _load_file(self, file_path: Path) -> tuple:
        """加载单个文件"""
        try:
            if file_path.suffix.lower() == '.pdf':
                loader = PDFPlumberLoader(str(file_path))
                docs = loader.load()
            elif file_path.suffix.lower() in ['.txt', '.md']:
                loader = TextLoader(str(file_path), encoding='utf-8')
                docs = loader.load()
            else:
                return [], {'file': str(file_path), 'error': f'不支持的格式: {file_path.suffix}'}
            
            for doc in docs:
                doc.metadata['source'] = file_path.name
            
            print(f"  ✅ {file_path.name}: {len(docs)} 个文档")
            return docs, None
        
        except Exception as e:
            print(f"  ❌ {file_path.name}: {e}")
            return [], {'file': str(file_path), 'error': str(e)}
    
    def _split_documents(self, documents: List) -> List:
        """分割文档"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "，", " ", ""]
        )
        return splitter.split_documents(documents)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""
    
    def search(self, query: str, top_k: int = 3) -> Dict:
        """搜索知识库"""
        if not self.vector_store:
            return {'question': query, 'results': []}
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            documents = [
                {
                    'content': doc.page_content,
                    'source': doc.metadata.get('source', 'Unknown'),
                    'score': float(score)
                }
                for doc, score in results
            ]
            return {'question': query, 'results': documents}
        except Exception as e:
            print(f"Search error: {e}")
            return {'question': query, 'results': []}
    
    def query(self, question: str, top_k: int = 3) -> Dict:
        """查询知识库"""
        results = self.search(question, top_k)
        answer = "\n\n".join([
            f"【{doc['source']}】\n{doc['content']}"
            for doc in results['results']
        ])
        
        return {
            'question': question,
            'answer': answer or "知识库中未找到相关内容",
            'sources': [doc['source'] for doc in results['results']]
        }
    
    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        try:
            self.load_vector_store()
            
            total_chunks = self.vector_store.index.ntotal if self.vector_store else 0
            files = [
                {
                    'name': filename,
                    'path': metadata.get('path', ''),
                    'added_time': metadata.get('added_time', '')
                }
                for filename, metadata in self.file_metadata.items()
            ]
            
            return {
                'total_chunks': total_chunks,
                'total_files': len(files),
                'files': files
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {'total_chunks': 0, 'total_files': 0, 'files': []}
    
    def clear(self):
        """清空知识库"""
        try:
            import shutil
            if self.db_path.exists():
                shutil.rmtree(self.db_path)
                self.db_path.mkdir(parents=True, exist_ok=True)
            
            self.vector_store = None
            self.file_metadata = {}
            self._save_metadata()
            print("✅ 知识库已清空")
        except Exception as e:
            print(f"❌ 清空失败: {e}")
    
    def delete_document(self, filename: str):
        """删除指定文档"""
        if filename in self.file_metadata:
            del self.file_metadata[filename]
            self._save_metadata()
            self.load_vector_store()
    
    def add_documents_from_upload(self, files) -> Dict:
        """从上传的文件添加文档"""
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        try:
            for file in files:
                temp_path = Path(temp_dir) / file.filename
                with open(temp_path, 'wb') as f:
                    f.write(file.file.read())
                file_paths.append(str(temp_path))
            
            result = self.add_documents(file_paths)
            
            # 保存文件到知识库目录
            for file_path in file_paths:
                path = Path(file_path)
                dest_path = self.db_path / "documents" / path.name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                print(f"  📄 文件已保存: {dest_path}")
            
            return result
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
