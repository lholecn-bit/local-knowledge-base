#!/usr/bin/env python3
"""修复 metadata.json 中每个文件的 chunks 字段

用法:
    python fix_metadata_chunks.py

行为:
 - 备份原始 metadata.json 到 metadata.json.bak.<ts>
 - 对每个条目:
     * 如果存在 chunks_detail，则使用其长度作为 chunks
     * 否则尝试根据记录的 path 或在 uploads/ 与 knowledge_db/documents/ 中查找文件
       并对文本内容进行分割计数（优先使用 langchain 的 RecursiveCharacterTextSplitter，如果不可用则按字符长度估算）
 - 将更新写回 metadata.json
"""
import json
import shutil
import time
from pathlib import Path
import os
import sys

HERE = Path(__file__).parent
METADATA_PATH = HERE / 'knowledge_db' / 'metadata.json'

def backup(path: Path):
    ts = int(time.time())
    bak = path.with_suffix(f'.json.bak.{ts}')
    shutil.copy2(path, bak)
    return bak

def simple_split_count(text, chunk_size=1000, overlap=200):
    if not text:
        return 0, []
    step = chunk_size - overlap if chunk_size > overlap else chunk_size
    chunks = []
    for i in range(0, len(text), step):
        chunks.append(text[i:i+chunk_size])
    return len(chunks), chunks

def try_load_and_split(file_path: Path, chunk_size=1000, overlap=200):
    # Only handle text-like files (.md, .txt, .html). For others, return 1 as fallback.
    suffix = file_path.suffix.lower()
    try:
        if suffix in ('.md', '.txt', '.html'):
            text = file_path.read_text(encoding='utf-8', errors='ignore')
            # try langchain splitter if available
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
                docs = splitter.split_text(text)
                # split_text may not exist; fallback to simple
                if isinstance(docs, list) and docs:
                    return len(docs), [d[:2000] for d in docs]
            except Exception:
                pass

            return simple_split_count(text, chunk_size, overlap)
        else:
            # For binary or unsupported types, return 1 as conservative value
            return 1, []
    except Exception:
        return 1, []

def find_candidate_path(filename: str):
    # search uploads and knowledge_db/documents
    candidates = []
    uploads_dir = HERE / 'uploads'
    if uploads_dir.exists():
        for p in uploads_dir.iterdir():
            if p.is_file() and (p.name == filename or p.name.endswith('_' + filename) or p.name.endswith(filename)):
                candidates.append(p)
    docs_dir = HERE / 'knowledge_db' / 'documents'
    if docs_dir.exists():
        for p in docs_dir.iterdir():
            if p.is_file() and (p.name == filename or p.name.endswith('_' + filename) or p.name.endswith(filename)):
                candidates.append(p)
    return candidates[0] if candidates else None

def main():
    if not METADATA_PATH.exists():
        print('metadata.json not found at', METADATA_PATH)
        sys.exit(1)

    data = json.loads(METADATA_PATH.read_text(encoding='utf-8'))
    bak = backup(METADATA_PATH)
    print('Backup saved to', bak)

    updated = {}
    stats_before = {k: v.get('chunks') for k, v in data.items()}

    for name, meta in data.items():
        print(f'Processing {name}...')
        chunks = None
        chunks_detail = meta.get('chunks_detail')
        if chunks_detail:
            chunks = len(chunks_detail)
            print(f'  using chunks_detail length {chunks}')
        else:
            # try metadata path
            p = meta.get('path')
            candidate = None
            if p and os.path.exists(p):
                candidate = Path(p)
            else:
                candidate = find_candidate_path(name)

            if candidate:
                cnt, cdetail = try_load_and_split(candidate)
                chunks = cnt
                if cdetail:
                    meta['chunks_detail'] = [{'id': i, 'content': cdetail[i][:2000]} for i in range(len(cdetail))]
                    print(f'  generated chunks_detail with {chunks} chunks')
                else:
                    print(f'  estimated chunks: {chunks} (no preview)')
            else:
                # fallback: use existing chunks or 1
                chunks = meta.get('chunks') or 1
                print(f'  file not found, fallback chunks={chunks}')

        meta['chunks'] = chunks
        updated[name] = chunks

    # write back
    METADATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\nSummary:')
    for k, v in updated.items():
        print(f'  {k}: chunks={v} (before={stats_before.get(k)})')

if __name__ == '__main__':
    main()
