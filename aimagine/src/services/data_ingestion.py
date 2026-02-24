from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Protocol, Optional, Tuple
import re
from pathlib import Path
import markdown
from bs4 import BeautifulSoup

@dataclass
class ChunkingConfig:
    """Configuration for text chunking"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    split_on_headings: bool = True
    preserve_hierarchy: bool = True
    min_chunk_size: int = 100
    max_chunk_size: int = 2000

class ChunkingStrategy(Enum):
    """Available chunking strategies"""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    HEADING = "heading"

class DocumentParser(Protocol):
    """Protocol for document parsers"""
    def parse(self, file_path: Path) -> Tuple[str, Dict]:
        """Parse document and return raw text and metadata"""
        pass

class MarkdownParser:
    def parse(self, file_path: Path) -> Tuple[str, Dict]:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse markdown and extract structure
        html = markdown.markdown(content, extensions=['toc'])
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract headers and their hierarchy
        headers = []
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(header.name[1])
            headers.append({
                'text': header.get_text(),
                'level': level,
                'position': len(str(soup).split(str(header))[0])
            })
        
        metadata = {
            'headers': headers,
            'structure': self._extract_document_structure(soup)
        }
        
        return soup.get_text(), metadata

    def _extract_document_structure(self, soup: BeautifulSoup) -> Dict:
        """Extract document structure including sections and subsections"""
        structure = {}
        current_section = None
        
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
            if tag.name.startswith('h'):
                level = int(tag.name[1])
                if level == 1:
                    current_section = tag.get_text()
                    structure[current_section] = {'subsections': {}, 'content': []}
                elif level == 2 and current_section:
                    subsection = tag.get_text()
                    structure[current_section]['subsections'][subsection] = []
            elif tag.name == 'p' and current_section:
                structure[current_section]['content'].append(tag.get_text())
        
        return structure

class DataIngestionService:
    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.processed_documents: Dict[str, Dict] = {}
        self.parsers = {
            '.md': MarkdownParser(),
        }
        self.config = config or ChunkingConfig()

    def _process_content(self, content: str, metadata: Dict, file_path: Path) -> Dict:
        """Process the raw content into a structured format with chunks."""
        cleaned_text = self._clean_text(content)
        
        # Create chunks based on document structure
        chunks = self._create_structured_chunks(cleaned_text, metadata)
        
        return {
            'file_path': str(file_path),
            'file_type': file_path.suffix.lower(),
            'content': cleaned_text,
            'chunks': chunks,
            'metadata': {
                **metadata,
                'size': file_path.stat().st_size,
                'modified': file_path.stat().st_mtime,
                'created': file_path.stat().st_ctime,
                'num_chunks': len(chunks)
            }
        }

    def _create_structured_chunks(self, text: str, metadata: Dict) -> List[Dict]:
        """Create chunks while preserving document structure and hierarchy"""
        chunks = []
        
        if self.config.split_on_headings and metadata.get('headers'):
            # Split on headers while preserving hierarchy
            chunks.extend(self._split_on_headers(text, metadata['headers']))
        else:
            # Fall back to basic chunking
            chunks.extend(self._create_basic_chunks(text))
        
        # Post-process chunks to ensure size constraints
        chunks = self._normalize_chunk_sizes(chunks)
        
        return chunks

    def _split_on_headers(self, text: str, headers: List[Dict]) -> List[Dict]:
        """Split text into chunks based on header positions"""
        chunks = []
        headers = sorted(headers, key=lambda x: x['position'])
        
        for i, header in enumerate(headers):
            # Determine chunk end position
            end_pos = headers[i + 1]['position'] if i < len(headers) - 1 else len(text)
            start_pos = header['position']
            
            chunk_text = text[start_pos:end_pos].strip()
            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'start_idx': start_pos,
                    'end_idx': end_pos,
                    'metadata': {
                        'header': header['text'],
                        'level': header['level'],
                        'hierarchy': self._get_chunk_hierarchy(header, headers)
                    }
                })
        
        return chunks

    def _get_chunk_hierarchy(self, current_header: Dict, headers: List[Dict]) -> List[str]:
        """Build hierarchy path for a chunk based on its headers"""
        hierarchy = []
        current_level = current_header['level']
        
        for header in reversed(headers):
            if header['position'] < current_header['position'] and header['level'] < current_level:
                hierarchy.append(header['text'])
                current_level = header['level']
        
        return list(reversed(hierarchy))

    def _create_basic_chunks(self, text: str) -> List[Dict]:
        """Create basic overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.config.chunk_size
            
            if end < len(text):
                # Find natural break points
                break_points = [
                    text.rfind('.', start, end),
                    text.rfind('!', start, end),
                    text.rfind('?', start, end),
                    text.rfind('\n', start, end)
                ]
                natural_break = max(point for point in break_points if point != -1)
                if natural_break != -1:
                    end = natural_break + 1
            else:
                end = len(text)
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'start_idx': start,
                    'end_idx': end,
                    'metadata': {
                        'type': 'basic_chunk'
                    }
                })
            
            start = end - self.config.chunk_overlap
        
        return chunks

    def _normalize_chunk_sizes(self, chunks: List[Dict]) -> List[Dict]:
        """Ensure chunks meet size constraints"""
        normalized_chunks = []
        
        for chunk in chunks:
            text = chunk['text']
            if len(text) > self.config.max_chunk_size:
                # Split large chunks
                sub_chunks = self._create_basic_chunks(text)
                for sub_chunk in sub_chunks:
                    sub_chunk['metadata'].update(chunk['metadata'])
                normalized_chunks.extend(sub_chunks)
            elif len(text) < self.config.min_chunk_size and normalized_chunks:
                # Merge small chunks with previous chunk if possible
                if normalized_chunks:
                    prev_chunk = normalized_chunks[-1]
                    combined_text = prev_chunk['text'] + ' ' + text
                    if len(combined_text) <= self.config.max_chunk_size:
                        prev_chunk['text'] = combined_text
                        prev_chunk['end_idx'] = chunk['end_idx']
                        continue
            
            normalized_chunks.append(chunk)
        
        return normalized_chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove multiple newlines while preserving paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove special characters while preserving meaningful punctuation
        text = re.sub(r'[^\w\s\n.,!?;:()\-–—""\']+', '', text)
        return text.strip()

    def process_file(self, file_path: Path) -> Dict:
        """Process any supported file type and extract content."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file extension and corresponding parser
        extension = file_path.suffix.lower()
        parser = self.parsers.get(extension)
        
        if not parser:
            raise ValueError(f"Unsupported file type: {extension}")

        try:
            # Parse the document
            raw_text, metadata = parser.parse(file_path)
            
            # Process the content
            processed_content = self._process_content(raw_text, metadata, file_path)
            
            # Store the processed content
            self.processed_documents[str(file_path)] = processed_content
            
            return processed_content

        except Exception as e:
            raise Exception(f"Error processing file {file_path}: {str(e)}")

    def get_processed_documents(self) -> Dict[str, Dict]:
        """Return all processed documents."""
        return self.processed_documents

    def add_parser(self, extension: str, parser: DocumentParser):
        """Add a new parser for a file type."""
        self.parsers[extension.lower()] = parser 