"""
文档同步服务
负责自动同步和更新各种数据源
- 官方文档：React、Vue、TypeScript 等（每周自动更新）
- GitHub 文档：公司内部规范文档（实时同步）
- 手动上传的文档：PDF、Markdown 等

类比：这是一个智能图书采购员，定期去出版社和书店采购新书
"""
import os
import re
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from config import (
    OFFICIAL_SOURCES,
    GITHUB_REPO,
    GITHUB_TOKEN,
    DOCUMENTS_PATH
)
from database import get_vector_store
from document_processor import get_document_processor
from deepseek_client import get_embedding_client


class OfficialDocSyncer:
    """官方文档同步器"""

    def __init__(self):
        self.processor = get_document_processor()
        self.embedding_client = get_embedding_client()
        self.vector_store = get_vector_store()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def sync_source(self, source_key: str) -> Dict:
        """
        同步单个官方文档源

        Args:
            source_key: 文档源标识（如 'react', 'vue'）

        Returns:
            同步结果统计
        """
        if source_key not in OFFICIAL_SOURCES:
            return {"error": f"未知的文档源: {source_key}"}

        config = OFFICIAL_SOURCES[source_key]
        print(f"🔄 开始同步: {config['name']}")

        # 1. 获取页面列表
        urls = self._get_page_urls(config)

        if not urls:
            return {"error": "未找到可抓取的页面"}

        print(f"📄 发现 {len(urls)} 个页面")

        # 2. 清理旧数据
        self.vector_store.delete_by_source(source_key)
        print("🗑️ 已清理旧数据")

        # 3. 抓取并处理每个页面
        success_count = 0
        fail_count = 0

        for i, url in enumerate(urls, 1):
            try:
                print(f"  [{i}/{len(urls)}] 抓取: {url}")
                self._process_page(url, source_key, config)
                success_count += 1

                # 礼貌性延迟，避免请求过快
                time.sleep(0.5)

            except Exception as e:
                print(f"  ⚠️ 抓取失败: {url} - {e}")
                fail_count += 1

        return {
            "source": source_key,
            "name": config["name"],
            "total": len(urls),
            "success": success_count,
            "failed": fail_count,
            "synced_at": datetime.now().isoformat()
        }

    def _get_page_urls(self, config: Dict) -> List[str]:
        """
        获取文档站点的所有页面 URL

        策略：
        1. 先尝试 sitemap.xml
        2. 如果没有，尝试从首页抓取链接
        """
        base_url = config["base_url"]
        urls = []

        # 尝试获取 sitemap
        sitemap_url = config.get("sitemap")
        if sitemap_url:
            try:
                response = self.session.get(sitemap_url, timeout=30)
                if response.status_code == 200:
                    # 解析 XML sitemap
                    soup = BeautifulSoup(response.content, 'xml')
                    locs = soup.find_all('loc')
                    urls = [loc.text for loc in locs]
                    # 过滤只保留文档页面
                    urls = [u for u in urls if self._is_doc_page(u, base_url)]
            except Exception as e:
                print(f"  ⚠️ 获取 sitemap 失败: {e}")

        # 如果 sitemap 失败或为空，从首页抓取
        if not urls:
            try:
                response = self.session.get(base_url, timeout=30)
                soup = BeautifulSoup(response.content, 'html.parser')

                # 查找所有内部链接
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(base_url, href)

                    # 只保留文档页面
                    if self._is_doc_page(full_url, base_url):
                        urls.append(full_url)

                # 去重
                urls = list(set(urls))
            except Exception as e:
                print(f"  ⚠️ 从首页抓取失败: {e}")

        # 限制数量，避免抓取过多
        return urls[:100]  # 最多抓 100 页

    def _is_doc_page(self, url: str, base_url: str) -> bool:
        """判断 URL 是否是文档页面"""
        # 必须是同一域名下的页面
        if not url.startswith(base_url):
            return False

        # 排除非文档页面
        excluded_patterns = [
            r'/blog/',
            r'/community/',
            r'/about/',
            r'/team/',
            r'\.pdf$',
            r'\.png$',
            r'\.jpg$',
            r'\.gif$',
            r'#',  # 锚点
        ]

        for pattern in excluded_patterns:
            if re.search(pattern, url):
                return False

        return True

    def _process_page(self, url: str, source_key: str, config: Dict):
        """处理单个页面"""
        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        html_content = response.text

        # 使用文档处理器提取内容
        chunks = self.processor.process_webpage(
            url=url,
            html_content=html_content,
            metadata={"source_type": "official", "doc_source": source_key}
        )

        if not chunks:
            return

        # 提取文本和元数据
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                **chunk["metadata"],
                "source": url,
                "doc_source": source_key
            }
            for chunk in chunks
        ]

        # 生成 Embedding 并存入数据库
        embeddings = self.embedding_client.get_embeddings(texts)
        self.vector_store.add_documents(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            source_type="official"
        )

    def sync_all(self) -> List[Dict]:
        """同步所有配置的官方文档源"""
        results = []
        for source_key in OFFICIAL_SOURCES.keys():
            result = self.sync_source(source_key)
            results.append(result)
            time.sleep(1)  # 文档源之间延迟
        return results


class GitHubSyncer:
    """GitHub 文档同步器"""

    def __init__(self, repo: str = None, token: str = None):
        self.repo = repo or GITHUB_REPO
        self.token = token or GITHUB_TOKEN
        self.processor = get_document_processor()
        self.embedding_client = get_embedding_client()
        self.vector_store = get_vector_store()
        self.api_base = "https://api.github.com"

    def sync_repo_docs(self) -> Dict:
        """
        同步 GitHub 仓库中的文档

        策略：
        1. 获取仓库根目录下的 Markdown 文件
        2. 获取 docs/ 目录下的所有 Markdown 文件
        3. 处理并入库
        """
        if not self.repo:
            return {"error": "未配置 GITHUB_REPO"}

        if not self.token:
            print("⚠️ 未配置 GITHUB_TOKEN，可能会受到 API 速率限制")

        print(f"🔄 开始同步 GitHub 仓库: {self.repo}")

        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        # 获取需要同步的文件列表
        files_to_sync = []

        # 1. 根目录下的 Markdown
        root_files = self._list_directory("", headers)
        for f in root_files:
            if f["name"].endswith('.md'):
                files_to_sync.append(f)

        # 2. docs 目录下的 Markdown
        docs_files = self._list_directory("docs", headers)
        for f in docs_files:
            if f["name"].endswith('.md'):
                files_to_sync.append(f)

        if not files_to_sync:
            return {"error": "未找到 Markdown 文档"}

        print(f"📄 发现 {len(files_to_sync)} 个文档文件")

        # 清理旧数据
        self.vector_store.delete_by_source(f"github:{self.repo}")

        # 处理每个文件
        success_count = 0
        for f in files_to_sync:
            try:
                print(f"  📥 下载: {f['path']}")
                content = self._download_file(f["download_url"], headers)

                # 处理文档
                metadata = {
                    "filename": f["name"],
                    "path": f["path"],
                    "source": f"github:{self.repo}/{f['path']}"
                }

                chunks = self.processor.process_github_readme(
                    repo=self.repo,
                    content=content,
                    metadata=metadata
                )

                if chunks:
                    texts = [c["text"] for c in chunks]
                    metadatas = [c["metadata"] for c in chunks]
                    embeddings = self.embedding_client.get_embeddings(texts)

                    self.vector_store.add_documents(
                        documents=texts,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        source_type="github"
                    )
                    success_count += 1

                time.sleep(0.3)  # 避免触发 GitHub 速率限制

            except Exception as e:
                print(f"  ⚠️ 处理失败: {f['path']} - {e}")

        return {
            "repo": self.repo,
            "total_files": len(files_to_sync),
            "success": success_count,
            "synced_at": datetime.now().isoformat()
        }

    def _list_directory(self, path: str, headers: Dict) -> List[Dict]:
        """列出目录内容"""
        url = f"{self.api_base}/repos/{self.repo}/contents/{path}"

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 404:
            return []  # 目录不存在

        response.raise_for_status()
        return response.json()

    def _download_file(self, download_url: str, headers: Dict) -> str:
        """下载文件内容"""
        response = requests.get(download_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text


class DocumentImporter:
    """本地文档导入器"""

    def __init__(self):
        self.processor = get_document_processor()
        self.embedding_client = get_embedding_client()
        self.vector_store = get_vector_store()

    def import_file(self, file_path: str, metadata: Dict = None) -> Dict:
        """导入单个文件"""
        try:
            # 处理文件
            chunks = self.processor.process_file(file_path, metadata)

            if not chunks:
                return {"error": "未能从文件中提取内容"}

            # 提取文本和元数据
            texts = [c["text"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]

            # 生成 Embedding
            embeddings = self.embedding_client.get_embeddings(texts)

            # 存入数据库
            self.vector_store.add_documents(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                source_type="document"
            )

            return {
                "success": True,
                "file": file_path,
                "chunks": len(chunks),
                "total_chars": sum(len(t) for t in texts)
            }

        except Exception as e:
            return {"error": str(e), "file": file_path}

    def import_directory(self, dir_path: str) -> List[Dict]:
        """批量导入目录中的所有支持文件"""
        results = []
        path = Path(dir_path)

        for ext in ['.md', '.markdown', '.txt', '.pdf']:
            for file_path in path.rglob(f'*{ext}'):
                result = self.import_file(str(file_path))
                results.append(result)

        return results


# 便捷函数
def run_full_sync() -> Dict:
    """执行完整同步（官方文档 + GitHub）"""
    results = {
        "official": [],
        "github": None,
        "timestamp": datetime.now().isoformat()
    }

    # 同步官方文档
    print("\n" + "="*50)
    print("📚 同步官方文档")
    print("="*50)
    official_syncer = OfficialDocSyncer()
    results["official"] = official_syncer.sync_all()

    # 同步 GitHub
    print("\n" + "="*50)
    print("🐙 同步 GitHub 文档")
    print("="*50)
    github_syncer = GitHubSyncer()
    results["github"] = github_syncer.sync_repo_docs()

    return results


if __name__ == "__main__":
    # 测试运行
    result = run_full_sync()
    print("\n" + "="*50)
    print("✅ 同步完成")
    print(json.dumps(result, indent=2, ensure_ascii=False))
