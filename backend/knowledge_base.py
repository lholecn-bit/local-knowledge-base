# backend/knowledge_base.py

import os
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import hashlib
from datetime import datetime


from dotenv import load_dotenv
# 加载环境变量，默认情况下，load_dotenv() 会在当前目录查找 .env 文件
load_dotenv()

# 在最开始设置离线模式，优先使用本地缓存 # TODO 如何体现本地优先

project_root = Path(__file__).parent.parent  # 项目根目录
models_cache_path = project_root / 'models_cache'

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(models_cache_path.absolute())
os.environ['TRANSFORMERS_CACHE'] = str((models_cache_path / 'transformers').absolute())

# V2Ray 代理地址）
# os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"  # 浏览器代理端口
# os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"  # 注意：HTTPS 代理也填 http 开头（本地代理通用）
#

try:
    from langchain_community.document_loaders import PDFPlumberLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # ✅ 改这里
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
        
        # 1. 创建模型缓存目录 - 使用项目根目录的 models_cache
        # 注意：这与上面设置的 HF_HOME 环境变量必须一致
        project_root = Path(__file__).parent.parent
        self.models_cache = project_root / 'models_cache'
        self.models_cache.mkdir(parents=True, exist_ok=True)
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.metadata_file = self.db_path / "metadata.json"

        self.reranker = None
        self.reranker_model = 'light'
        
        # 2.改为延迟加载：不在 __init__ 中加载模型
        # 而是在 search() 方法中第一次需要时加载
        # 这样可以确保环境变量已经正确设置


                
        # 3. 添加相关性阈值配置
        self.relevance_threshold = 0.3  # 相关性阈值（可调整）

        # 4. OpenAI API Key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.api_key = openai_api_key

        if not self.api_key:
            raise ValueError(
                "❌ OPENAI_API_KEY 未设置！\n"
                "   请在 .env 文件中添加: OPENAI_API_KEY=sk-..."
            )
        
        # 初始化嵌入模型
        self.embeddings = None
        if LANGCHAIN_AVAILABLE:
            self.embeddings = self._init_embeddings()
            if not self.embeddings:
                print(f"⚠️ 警告：Embeddings 初始化失败，知识库功能将受限")
        else:
            print(f"⚠️ 警告：LangChain 不可用，知识库功能将受限")
        
        # 6. 初始化向量数据库
        self.vector_store = None
        if self.embeddings:
            self.load_vector_store()
        
        # 7. 加载文件元数据
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
                base_url=api_base
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
    
    def _clean_filename(self, filename: str) -> str:
        """清理文件名前缀（去掉如 '0_' 或 '123_' 的前缀）"""
        if '_' in filename:
            parts = filename.split('_', 1)
            if len(parts) == 2 and parts[0].isdigit():
                return parts[1]
        return filename
    
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

    def _rebuild_vector_store(self):
        """根据当前元数据重建向量索引（从磁盘文件加载所有文档并重建 FAISS）。
        说明：该方法只重建向量索引，不会修改 `file_metadata` 的时间等字段。
        """
        if not self.embeddings:
            print("⚠️ Embeddings 未初始化，无法重建索引")
            return False

        # 收集所有文件路径
        file_paths = []
        for fname, meta in self.file_metadata.items():
            path = meta.get('path')
            if path:
                p = Path(path)
                if p.exists():
                    file_paths.append(str(p))

        if not file_paths:
            print("⚠️ 未找到可用于重建的文档文件，清空向量库")
            self.vector_store = None
            # 删除已存在的 faiss_index 目录以避免不一致
            try:
                faiss_path = self.db_path / "faiss_index"
                if faiss_path.exists():
                    import shutil
                    shutil.rmtree(str(faiss_path))
            except Exception as e:
                print(f"⚠️ 删除旧向量库失败: {e}")
            return True

        try:
            print(f"🔧 重建向量库：将从 {len(file_paths)} 个文件创建索引...")

            all_documents = []
            for fp in file_paths:
                try:
                    docs, err = self._load_file(Path(fp))
                    if err:
                        print(f"  ⚠️ 加载文档失败: {fp} -> {err}")
                        continue
                    all_documents.extend(docs)
                except Exception as e:
                    print(f"  ❌ 读取文件 {fp} 失败: {e}")

            if not all_documents:
                print("⚠️ 没有可用文档内容来重建索引")
                self.vector_store = None
                return True

            # 分割文档
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            split_docs = splitter.split_documents(all_documents)
            print(f"✅ 分割完成，共 {len(split_docs)} 个 chunks，开始创建/替换 FAISS 索引...")

            # 使用 FAISS.from_documents 重新创建索引
            try:
                self.vector_store = FAISS.from_documents(split_docs, self.embeddings)
                # 保存到磁盘
                self.save_vector_store()
                print(f"✅ 向量库重建完成: {self.vector_store.index.ntotal} 个向量")
                return True
            except Exception as e:
                print(f"❌ 创建向量库失败: {e}")
                import traceback
                traceback.print_exc()
                return False

        except Exception as e:
            print(f"❌ 重建向量库错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def add_documents(self, file_paths: List[str], progress_callback=None) -> Dict:
        """添加文档 - 支持进度回调"""
        print(f"\n📂 开始处理 {len(file_paths)} 个文件...")
        
        if not self.embeddings:
            return {
                'added_chunks': 0,
                'files': [],
                'errors': [{'error': 'Embeddings 未初始化，无法添加文档'}]
            }
        
        all_documents = []
        processed_files = {}
        added_chunks = 0
        errors = []
        total_files = len(file_paths)
        
        # 第一步：加载所有文档
        print("\n📖 第一步：加载文档...")
        for idx, file_path in enumerate(file_paths):
            try:
                docs, error = self._load_file(Path(file_path))
                if error:
                    errors.append(error)
                else:
                    all_documents.extend(docs)
                    processed_files[file_path] = len(docs)
                    
                    # 📤 发送加载进度（0-40%）
                    progress = int((idx + 1) / total_files * 40)
                    if progress_callback:
                        progress_callback('loading', progress)
            
            except Exception as e:
                print(f"❌ 加载文件失败: {file_path}, {e}")
                errors.append({'file': str(file_path), 'error': str(e)})
        
        if not all_documents:
            print("⚠️ 没有有效的文档")
            return {
                'added_chunks': 0,
                'files': [],
                'errors': errors
            }
        
        # 第二步：分割文档
        print("\n✂️ 第二步：分割文档...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        split_docs = splitter.split_documents(all_documents)
        print(f"✅ 分割完成，共 {len(split_docs)} 个 chunks")
        # ===== 保存分块内容到元数据（按文件分组） =====
        try:
            chunks_by_file = {}
            for idx, doc in enumerate(split_docs):
                source = doc.metadata.get('source', 'unknown')
                entry = {
                    'id': idx,
                    'content': doc.page_content[:2000]  # 保存前2k字符用于预览
                }
                chunks_by_file.setdefault(source, []).append(entry)

            # 将分块详情合并到 file_metadata 中
            for file_path, doc_count in processed_files.items():
                file_name = self._clean_filename(Path(file_path).name)
                if file_name in chunks_by_file:
                    self.file_metadata.setdefault(file_name, {})
                    self.file_metadata[file_name]['chunks_detail'] = chunks_by_file[file_name]
                    # ensure chunks count recorded
                    self.file_metadata[file_name]['chunks'] = len(chunks_by_file[file_name])
        except Exception as e:
            print(f"⚠️ 保存分块详情失败: {e}")
        
        # 📤 发送分割进度（40-60%）
        if progress_callback:
            progress_callback('splitting', 60)
        
        # 第三步：生成向量（这是最耗时的步骤）
        print("\n🔢 第三步：生成向量（这可能需要一些时间）...")
        total_chunks = len(split_docs)
        
        try:
            # 批量处理 chunks，每批 10 个
            batch_size = 10
            for batch_idx in range(0, len(split_docs), batch_size):
                batch = split_docs[batch_idx:batch_idx + batch_size]
                
                try:
                    if self.vector_store is None:
                        # 第一批：创建向量库
                        self.vector_store = FAISS.from_documents(batch, self.embeddings)
                    else:
                        # 后续批：添加到现有向量库
                        self.vector_store.add_documents(batch)
                    
                    added_chunks += len(batch)
                    
                    # 📤 发送向量化进度（60-95%）
                    progress = 60 + int((batch_idx + len(batch)) / total_chunks * 35)
                    if progress_callback:
                        progress_callback('vectorizing', min(progress, 95))
                    
                    print(f"✅ 处理了 {added_chunks}/{total_chunks} chunks")
                
                except Exception as e:
                    print(f"❌ 向量化失败: {e}")
                    errors.append({'error': f'向量化失败: {e}'})
                    return {
                        'added_chunks': added_chunks,
                        'files': list(processed_files.keys()),
                        'errors': errors
                    }
            
            # 第四步：保存向量库
            print("\n💾 第四步：保存向量库...")
            self.save_vector_store()
            
            # 📤 发送保存进度（95-100%）
            if progress_callback:
                progress_callback('saving', 100)
            
            # 更新元数据
            for file_path, doc_count in processed_files.items():
                file_name = self._clean_filename(Path(file_path).name)
                # 不要覆盖已有 metadata（例如 chunks_detail），而是更新字段
                self.file_metadata.setdefault(file_name, {})
                # 如果之前已经计算了分块详情，则优先使用其长度作为 chunks
                existing_chunks = self.file_metadata[file_name].get('chunks')
                if existing_chunks is None:
                    # 如果没有，尝试使用 chunks_detail 长度
                    existing_chunks = len(self.file_metadata[file_name].get('chunks_detail', [])) or doc_count

                self.file_metadata[file_name].update({
                    'path': file_path,
                    'hash': self._calculate_file_hash(file_path),
                    'added_time': datetime.now().isoformat(),
                    'chunks': existing_chunks,
                    'size': Path(file_path).stat().st_size if Path(file_path).exists() else None,
                    'status': 'indexed'
                })
            
            self._save_metadata()
            
            print(f"✅ 完成！共添加 {added_chunks} 个 chunks\n")
            
            return {
                'added_chunks': added_chunks,
                'files': list(processed_files.keys()),
                'errors': errors
            }
        
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'added_chunks': added_chunks,
                'files': list(processed_files.keys()),
                'errors': [{'error': f'处理失败: {e}'}]
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
                doc.metadata['source'] = self._clean_filename(file_path.name)
            
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
    
    def search(self, query: str, top_k: int = 3, use_reranking: bool = True) -> Dict:
        """
        搜索知识库（支持重排序）
        
        Args:
            query: 查询文本
            top_k: 返回的结果数
            use_reranking: 是否使用重排序器
        """
        if not self.vector_store:
            print(f"知识库不存在或未加载")
            return {'question': query, 'results': [], 'has_results': False}
        else:
            print(f"🔍 开始搜索: '{query}' (Top {top_k}, 重排序: {'启用' if use_reranking else '禁用'})")
        
        try:
            # 第一步：向量检索（召回更多候选）
            candidates = self.vector_store.similarity_search_with_score(
                query, 
                k=top_k * 3  # 召回 3 倍的候选
            )

            # 使用提供的阈值或默认值
            threshold = self.relevance_threshold

            # 距离越小越相似，所以要用 1 / (1 + distance) 转换为相似度
            filtered_candidates = []
            for doc, distance in candidates:
                # ✅ 正确的相似度计算：距离 → 相似度
                # distance 范围：[0, ∞)
                # similarity 范围：(0, 1]
                # 使用公式：similarity = 1 / (1 + distance)
                similarity = 1 / (1 + distance)
                
                source_name = doc.metadata.get('source', 'Unknown')
                print(f"📊 搜索结果: {source_name} (距离: {distance:.3f}, 相似度: {similarity:.3f})")
                
                # ✅ 按相关性阈值过滤
                if similarity >= threshold:
                    filtered_candidates.append({
                        'content': doc.page_content, # 文档内容
                        'source': source_name, # 文档来源
                        'score': similarity, # 使用相似度作为分数
                        'distance': distance  # 保留原始距离用于调试
                    })
                else:
                    print(f"   ❌ 相似度过低，过滤掉")

            # ✅ 只返回 top_k 个结果
            filtered_candidates = filtered_candidates[:top_k]
            
            # 第二步：重排序
            if use_reranking:
                try:
                    # ✅ 延迟导入：在使用时才导入
                    from sentence_transformers import CrossEncoder
                    
                    # ✅ 第一次需要时才加载模型
                    if self.reranker is None:
                        # 定义模型映射
                        model_map = {
                            'light': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                            'medium': 'BAAI/bge-reranker-base',
                            'large': 'BAAI/bge-reranker-large'
                        }
                        
                        model_name = model_map.get(self.reranker_model, model_map['light'])
                        
                        try:
                            print(f"📦 [延迟加载] 加载重排序模型: {model_name}...")
                            # ✅ 明确指定缓存目录
                            cache_folder = str(self.models_cache.absolute())
                            
                            self.reranker = CrossEncoder(
                                model_name,
                                cache_folder=cache_folder  # ✅ 指定缓存位置
                            )
                            print(f"✅ 重排序器加载成功 (缓存: {cache_folder})")
                        except Exception as load_error:
                            print(f"⚠️ 重排序器加载失败: {load_error}")
                            print(f"   使用原始向量搜索")
                            self.reranker = None
                    
                    # ✅ 只有模型加载成功才执行重排序
                    if self.reranker is not None:
                        # 提取文档内容（从字典中获取）
                        doc_contents = [cand['content'] for cand in filtered_candidates]
                        
                        # 重排序
                        scores = self.reranker.predict([
                            (query, content) for content in doc_contents
                        ])
                        
                        # 组合候选文档和分数，并排序
                        ranked_pairs = list(zip(filtered_candidates, scores))
                        ranked_pairs.sort(key=lambda x: x[1], reverse=True)
                        
                        # 更新为排序后的结果
                        candidates = ranked_pairs
                        print(f"✅ 重排序完成: {len(candidates)} 个结果")
                    
                except Exception as e:
                    print(f"⚠️  Re-Ranking 失败，降级到向量相似度: {e}")
                    # 降级处理：继续使用向量相似度分数
                    pass
            
            # 第三步：格式化结果（不再需要硬阈值！）
            results = []
            for doc, score in candidates[:top_k]:
                results.append({
                    'content': doc.get('content') if isinstance(doc, dict) else doc.page_content,
                    'source': doc.get('source') if isinstance(doc, dict) else doc.metadata.get('source', 'Unknown'),
                    'score': float(score),  # 现在是重排序分数而不是向量距离
                })
            
            has_results = len(results) > 0
            
            print(f"✅ 搜索完成: {len(results)} 个结果")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['source']} (分数: {result['score']:.3f})")
            
            return {
                'question': query,
                'results': results,
                'has_results': has_results
            }
        
        except Exception as e:
            print(f"❌ 搜索错误: {e}")
            import traceback
            traceback.print_exc()
            return {
                'question': query,
                'results': [],
                'has_results': False
            }

    def query(self, question: str, top_k: int = 3) -> Dict:
        """
        查询知识库
        
        Returns:
            {
                'question': str,
                'answer': str,
                'sources': list,
                'has_sources': bool  # ✅ 新增字段，表示是否有相关文档
            }
        """
        search_results = self.search(question, top_k)
        results = search_results['results']
        has_sources = search_results['has_results']
        
        answer = "\n\n".join([
            f"【{doc['source']}】\n{doc['content']}"
            for doc in results
        ])
        
        sources = [doc['source'] for doc in results]
        
        # ✅ 去重 sources
        sources = list(dict.fromkeys(sources))
        
        return {
            'question': question,
            'answer': answer or "知识库中未找到相关内容",
            'sources': sources,
            'has_sources': has_sources  # ✅ 新增：是否有相关文档
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
                    'added_time': metadata.get('added_time', ''),
                    'upload_time': metadata.get('added_time', ''),
                    'size': metadata.get('size'),
                    'chunks': metadata.get('chunks') or metadata.get('doc_count') or 0,
                    'status': metadata.get('status', 'unknown')
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
            # 尝试删除物理文件
            try:
                path = Path(self.file_metadata[filename].get('path', ''))
                if path.exists():
                    path.unlink()
                    # 如果所在目录变空可选择删除目录，但这里不做额外删除
            except Exception as e:
                print(f"⚠️ 删除物理文件失败: {e}")

            # 从元数据中移除并保存
            del self.file_metadata[filename]
            self._save_metadata()

            # 重新构建向量库以移除该文档的向量（较重，但确保索引一致）
            rebuilt = self._rebuild_vector_store()
            if not rebuilt:
                print("⚠️ 重建向量库失败，尝试加载原有向量库")
                self.load_vector_store()
    
    def add_documents_from_upload(self, files) -> Dict:
        """从上传的文件添加文档"""
        import tempfile
        import shutil
        from pathlib import Path
        
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        processed_files = []
        
        try:
            print(f"\n📝 开始处理上传的文件，共 {len(files)} 个")
            
            for idx, file in enumerate(files):
                try:
                    filename = file.filename
                    if not filename:
                        print(f"  ⚠️  文件 {idx+1} 没有文件名，跳过")
                        continue
                    
                    print(f"  处理文件 {idx+1}: {filename}")
                    
                    # ✅ 使用临时目录保存文件
                    temp_path = Path(temp_dir) / filename
                    file.save(str(temp_path))
                    file_paths.append(str(temp_path))
                    processed_files.append(filename)
                    print(f"    ✅ 已保存到临时目录")
                    
                except Exception as e:
                    print(f"  ❌ 处理文件失败: {e}")
                    continue
            
            if not file_paths:
                print("❌ 没有有效的文件可以处理")
                return {
                    'added_chunks': 0,
                    'files': [],
                    'errors': ['没有有效的文件']
                }
            
            print(f"\n📚 开始处理文档向量化（{len(file_paths)} 个文件）...")
            result = self.add_documents(file_paths)
            
            # 保存文件到知识库目录
            print(f"\n💾 保存文件到知识库...")
            for file_path in file_paths:
                try:
                    path = Path(file_path)
                    dest_path = self.db_path / "documents" / path.name
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)
                    print(f"  ✅ {path.name}")
                    # 更新元数据中的路径和大小（如果存在）
                    clean_name = self._clean_filename(path.name)
                    if clean_name in self.file_metadata:
                        try:
                            self.file_metadata[clean_name]['path'] = str(dest_path)
                            self.file_metadata[clean_name]['size'] = dest_path.stat().st_size
                            # 保持 status 为 indexed（如果之前已设置）
                        except Exception as e:
                            print(f"  ⚠️ 更新元数据大小/路径失败: {e}")
                except Exception as e:
                    print(f"  ⚠️  保存失败: {e}")

            # 保存更新后的元数据
            try:
                self._save_metadata()
            except Exception as e:
                print(f"⚠️ 保存元数据失败: {e}")
            
            print(f"\n✅ 上传完成!\n")
            return result
        
        except Exception as e:
            print(f"\n❌ 上传处理失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'added_chunks': 0,
                'files': [],
                'errors': [str(e)]
            }
        
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
