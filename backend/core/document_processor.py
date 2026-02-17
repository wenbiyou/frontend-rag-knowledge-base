"""
文档处理模块
负责解析各种格式的文档，并将其分割成适合检索的文本块
类比：这是一个智能切菜机，把整颗白菜切成适合入口的小块
"""
import re
from pathlib import Path
from typing import List, Dict
import markdown
from bs4 import BeautifulSoup
import requests
from pypdf import PdfReader
from config import CHUNK_SIZE, CHUNK_OVERLAP, SUPPORTED_EXTENSIONS


class TextChunker:
    """
    文本分块器
    将长文本分割成小块，同时保持语义连贯性
    """

    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        将文本分割成重叠的块

        策略：
        1. 优先按段落分割（保持语义完整）
        2. 如果段落太长，按句子分割
        3. 如果句子还太长，按固定长度强制分割
        """
        chunks = []

        # 先按段落分割
        paragraphs = text.split('\n\n')

        current_chunk = ""
        current_position = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果当前段落加入后不会超过限制，直接加入
            if len(current_chunk) + len(para) < self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "start_pos": current_position,
                        "end_pos": current_position + len(current_chunk),
                        "metadata": metadata or {}
                    })
                    current_position += len(current_chunk) - self.overlap

                # 如果单个段落就超过限制，需要进一步分割
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_long_text(para)
                    for sub in sub_chunks:
                        chunks.append({
                            "text": sub,
                            "start_pos": current_position,
                            "end_pos": current_position + len(sub),
                            "metadata": metadata or {}
                        })
                        current_position += len(sub) - self.overlap
                    current_chunk = ""
                else:
                    current_chunk = para + "\n\n"

        # 处理最后一块
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "start_pos": current_position,
                "end_pos": current_position + len(current_chunk),
                "metadata": metadata or {}
            })

        return chunks

    def _split_long_text(self, text: str) -> List[str]:
        """分割超长文本（按句子或固定长度）"""
        # 尝试按句子分割
        sentences = re.split(r'(?<=[。！？.!?])\s+', text)

        chunks = []
        current = ""

        for sent in sentences:
            if len(current) + len(sent) < self.chunk_size:
                current += sent + " "
            else:
                if current:
                    chunks.append(current.strip())
                current = sent + " "

        if current:
            chunks.append(current.strip())

        # 如果还有太长的，强制按长度切
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size:
                for i in range(0, len(chunk), self.chunk_size - self.overlap):
                    final_chunks.append(chunk[i:i + self.chunk_size])
            else:
                final_chunks.append(chunk)

        return final_chunks


class DocumentProcessor:
    """
    文档处理器
    支持多种格式：Markdown、PDF、纯文本、网页
    """

    def __init__(self):
        self.chunker = TextChunker()

    def process_file(self, file_path: str, metadata: Dict = None) -> List[Dict]:
        """根据文件类型选择对应的处理方法"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}")

        # 更新元数据
        meta = metadata or {}
        meta["filename"] = path.name
        meta["file_path"] = str(path)

        # 根据格式选择处理器
        if suffix in ['.md', '.markdown']:
            return self._process_markdown(path, meta)
        elif suffix == '.txt':
            return self._process_text(path, meta)
        elif suffix == '.pdf':
            return self._process_pdf(path, meta)
        else:
            raise ValueError(f"未实现的文件格式: {suffix}")

    def _process_markdown(self, path: Path, metadata: Dict) -> List[Dict]:
        """处理 Markdown 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取标题作为元数据
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1)

        # 将 Markdown 转为纯文本（去除格式符号，但保留内容）
        html = markdown.markdown(content)
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()

        return self.chunker.chunk_text(text, metadata)

    def _process_text(self, path: Path, metadata: Dict) -> List[Dict]:
        """处理纯文本文件"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        return self.chunker.chunk_text(content, metadata)

    def _process_pdf(self, path: Path, metadata: Dict) -> List[Dict]:
        """处理 PDF 文件"""
        reader = PdfReader(str(path))

        all_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                all_text.append(f"\n--- 第 {i+1} 页 ---\n{text}")

        full_text = "\n".join(all_text)
        metadata["total_pages"] = len(reader.pages)

        return self.chunker.chunk_text(full_text, metadata)

    def process_webpage(self, url: str, html_content: str, metadata: Dict = None) -> List[Dict]:
        """
        处理网页内容

        Args:
            url: 网页 URL
            html_content: HTML 原始内容
            metadata: 额外元数据
        """
        meta = metadata or {}
        meta["url"] = url
        meta["source"] = url

        soup = BeautifulSoup(html_content, 'html.parser')

        # 尝试提取标题
        title_tag = soup.find('title')
        if title_tag:
            meta["title"] = title_tag.get_text(strip=True)

        h1_tag = soup.find('h1')
        if h1_tag and "title" not in meta:
            meta["title"] = h1_tag.get_text(strip=True)

        # 移除脚本和样式标签
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()

        # 提取主要内容
        # 优先尝试 article、main 等语义化标签
        main_content = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile(r'content|main'))

        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            # 退而求其次，提取 body 中的文字
            text = soup.get_text(separator='\n', strip=True)

        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)

        return self.chunker.chunk_text(text, meta)

    def process_github_readme(self, repo: str, content: str, metadata: Dict = None) -> List[Dict]:
        """处理 GitHub README 内容"""
        meta = metadata or {}
        meta["source"] = f"github:{repo}"
        meta["repo"] = repo
        meta["type"] = "github_readme"

        # Markdown 处理逻辑
        html = markdown.markdown(content)
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()

        return self.chunker.chunk_text(text, meta)


# 单例模式
def get_document_processor() -> DocumentProcessor:
    """获取 DocumentProcessor 单例实例"""
    return DocumentProcessor()
