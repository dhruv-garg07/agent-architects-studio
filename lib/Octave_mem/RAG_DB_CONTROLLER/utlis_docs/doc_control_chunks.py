import os
import re
import pdfplumber
import docx
import csv
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import hashlib
from dataclasses import dataclass

# ==================== CONFIGURATION ====================
@dataclass
class ChunkingConfig:
    """Advanced configuration for semantic chunking"""
    target_chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    max_chunk_size: int = 800
    sentence_split_patterns: Tuple[str, ...] = (
        r'(?<=[.!?])\s+(?=[A-Z])',  # Sentence endings
        r'\n\s*\n',  # Paragraph breaks
        r'(?<=\n)\d+[\.\)]\s',  # Numbered items
        r'Q\d+[:\.]',  # Question patterns
        r'Solution[:\.]',  # Solution markers
    )
    semantic_boundary_patterns: Tuple[str, ...] = (
        r'^(CHAPTER|SECTION|PART)\s+[IVXLCDM0-9]+',
        r'^\d+\.\s+[A-Z]',  # Numbered headings
        r'^[A-Z][A-Za-z\s]{3,}:$',  # Heading-like text
        r'^Abstract:|^Introduction:|^Conclusion:',
        r'^References?$|^Bibliography$',
        r'^Figure\s+\d+:|^Table\s+\d+:',
        r'^Algorithm\s+\d+:|^Theorem\s+\d+:',
    )
    preserve_patterns: Tuple[str, ...] = (
        r'\$\$.*?\$\$',  # LaTeX math blocks
        r'```.*?```',  # Code blocks
        r'\[.*?\]\(.*?\)',  # Links
        r'\b(?:Figure|Table|Algorithm)\s+\d+\b',
    )
    stopwords: set = frozenset({
        'the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with', 'as', 'by',
        'an', 'at', 'from', 'this', 'that', 'it', 'be', 'are', 'was', 'were', 'or',
        'but', 'not', 'have', 'has', 'had', 'can', 'will', 'would', 'should', 'could'
    })

# ==================== TEXT PREPROCESSOR ====================
class AdvancedTextPreprocessor:
    """Enhanced text cleaning with PDF artifact removal"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text while preserving important formatting"""
        if not text:
            return ""
        
        # Step 1: Remove all CID codes and font encoding artifacts FIRST
        text = re.sub(r'\(cid:\d+\)', ' ', text)
        text = re.sub(r'\ufffd', '', text)  # Remove replacement characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)  # Remove control chars
    
        # Step 2: Fix common PDF artifacts
        text = AdvancedTextPreprocessor._fix_pdf_artifacts(text)
        
        # Step 3: Normalize whitespace (preserve meaningful newlines)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Step 4: Fix hyphenated words across lines
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # Step 5: Protect special patterns before further processing
        protected_areas = []
        for i, pattern in enumerate(ChunkingConfig().preserve_patterns):
            matches = list(re.finditer(pattern, text, re.DOTALL | re.IGNORECASE))
            for match in matches:
                placeholder = f"__PROTECTED_{i}_{len(protected_areas)}__"
                protected_areas.append((placeholder, match.group()))
                text = text[:match.start()] + placeholder + text[match.end():]
        
        # Step 6: Clean remaining text
        text = AdvancedTextPreprocessor._basic_cleaning(text)
        
        # Step 7: Restore protected areas
        for placeholder, original in protected_areas:
            text = text.replace(placeholder, original)
        
        return text.strip()
    
    @staticmethod
    @staticmethod
    def _fix_pdf_artifacts(text: str) -> str:
        """Fix common PDF extraction issues"""
        artifacts = [
            # ... existing patterns ...
            (r'\(cid:\d+\)', ' '),  # Remove CID codes
            (r'\s+', ' '),  # Normalize spaces
            (r'\n\s+', '\n'),  # Remove leading spaces on lines
            (r'', '•'),  # Convert weird bullet
            (r'●', '•'),  # Standardize bullet
            (r'\uf0b7', '•'),  # Unicode bullet
            (r'Page\s+\d+\s+of\s+\d+', ''),  # Remove page numbers
            (r'-\s*\n\s*', ''),  # Fix line-end hyphens
        ]
        
        for pattern, replacement in artifacts:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def _basic_cleaning(text: str) -> str:
        """Basic text normalization"""
        # Remove excessive punctuation but preserve important markers
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Normalize quotes
        text = re.sub(r'[«»"“”]', '"', text)
        text = re.sub(r'[‘’]', "'", text)
        
        # Fix multiple punctuation
        text = re.sub(r'([.!?]){2,}', r'\1', text)
        
        return text

# ==================== SEMANTIC SEGMENTER ====================
class SemanticSegmenter:
    """Advanced segmentation based on semantic boundaries"""
    
    def __init__(self, config: ChunkingConfig = None):
        self.config = config or ChunkingConfig()
        self.boundary_cache = {}
    
    def identify_boundaries(self, text: str) -> List[Tuple[int, str, int]]:
        """
        Identify semantic boundaries in text.
        Returns list of (position, boundary_type, hierarchy_level)
        """
        boundaries = []
        lines = text.split('\n')
        
        current_pos = 0
        hierarchy_stack = [0]  # Track heading levels
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                current_pos += len(line) + 1
                continue
            
            # Check for hierarchical boundaries
            boundary_found = False
            boundary_type = None
            level = 0
            
            # Pattern 1: Numbered sections (1., 1.1, 1.1.1)
            numbered_match = re.match(r'^(\d+(?:\.\d+)*)\.\s+(.+)$', line_stripped)
            if numbered_match:
                numbers = numbered_match.group(1).split('.')
                level = len(numbers)
                boundary_type = f"heading_{level}"
                boundary_found = True
            
            # Pattern 2: Roman numerals or capitalized headings
            elif re.match(self.config.semantic_boundary_patterns[0], line_stripped, re.IGNORECASE):
                boundary_type = "major_section"
                level = 1
                boundary_found = True
            
            # Pattern 3: Question patterns
            elif re.match(r'^(Q|Question)\s*\d+[:\.]', line_stripped, re.IGNORECASE):
                boundary_type = "question"
                level = 2
                boundary_found = True
            
            # Pattern 4: Solution/Answer patterns
            elif re.match(r'^(Solution|Answer|Proof)[:\.]', line_stripped, re.IGNORECASE):
                boundary_type = "solution"
                level = 3
                boundary_found = True
            
            # Pattern 5: List items
            elif re.match(r'^[•\-*]\s+', line_stripped) or re.match(r'^\d+[\.\)]\s+', line_stripped):
                boundary_type = "list_item"
                level = 4
                boundary_found = True
            
            if boundary_found:
                boundaries.append((current_pos, boundary_type, level))
                hierarchy_stack.append(level)
            
            current_pos += len(line) + 1
        
        # Add paragraph boundaries (soft boundaries)
        para_pattern = r'\n\s*\n'
        for match in re.finditer(para_pattern, text):
            boundaries.append((match.start(), "paragraph", 5))
        
        # Sort by position
        boundaries.sort(key=lambda x: x[0])
        
        return boundaries
    
    def calculate_semantic_density(self, text_segment: str) -> float:
        """
        Calculate semantic density to determine chunk size.
        Higher density = smaller chunks.
        """
        if not text_segment:
            return 0.0
        
        # Count technical indicators
        technical_indicators = 0
        
        # Formula density
        formula_patterns = [
            r'\$[^$]+\$',  # Inline math
            r'\\[a-zA-Z]+\{',  # LaTeX commands
            r'\b(?:algorithm|theorem|lemma|corollary)\b',
            r'\b(?:function|method|procedure)\b',
            r'[A-Z][a-z]+\s+et al\.',  # Citations
            r'\[?\d+(?:,\s*\d+)*\]?',  # References
        ]
        
        for pattern in formula_patterns:
            technical_indicators += len(re.findall(pattern, text_segment, re.IGNORECASE))
        
        # Code block density
        code_blocks = len(re.findall(r'```.*?```', text_segment, re.DOTALL))
        technical_indicators += code_blocks * 5
        
        # Entity density (proper nouns, acronyms)
        entities = len(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text_segment))
        technical_indicators += entities * 0.5
        
        # Normalize by length
        length = len(text_segment)
        if length == 0:
            return 0.0
        
        density = technical_indicators / (length / 100)  # Per 100 chars
        
        # Cap density
        return min(density, 10.0)

# ==================== ADVANCED CHUNKER ====================
class AdvancedChunker:
    """Main chunking engine with semantic awareness"""
    
    def __init__(self, config: ChunkingConfig = None):
        self.config = config or ChunkingConfig()
        self.preprocessor = AdvancedTextPreprocessor()
        self.segmenter = SemanticSegmenter(config)
    
    def create_chunks(self, text: str) -> List[Dict[str, any]]:
        """
        Create semantically coherent chunks from text.
        Returns list of dictionaries with metadata.
        """
        # Step 1: Clean and preprocess
        cleaned_text = self.preprocessor.clean_text(text)
        
        # Step 2: Identify semantic boundaries
        boundaries = self.segmenter.identify_boundaries(cleaned_text)
        
        # Step 3: Segment into preliminary chunks at boundaries
        preliminary_segments = self._segment_at_boundaries(cleaned_text, boundaries)
        
        # Step 4: Refine segments based on semantic cohesion
        refined_chunks = self._refine_segments(preliminary_segments)
        
        # Step 5: Apply size constraints and create final chunks
        final_chunks = self._apply_size_constraints(refined_chunks)
        
        # Step 6: Add metadata
        return self._add_metadata(final_chunks, cleaned_text)
    
    def _segment_at_boundaries(self, text: str, boundaries: List[Tuple[int, str, int]]) -> List[Dict]:
        """Create initial segments at identified boundaries"""
        segments = []
        boundaries.sort(key=lambda x: x[0])
        
        # Add start and end boundaries
        all_boundaries = [(0, "start", 0)] + boundaries + [(len(text), "end", 0)]
        
        for i in range(len(all_boundaries) - 1):
            start_pos, start_type, start_level = all_boundaries[i]
            end_pos, end_type, end_level = all_boundaries[i + 1]
            
            segment_text = text[start_pos:end_pos].strip()
            if not segment_text:
                continue
            
            # Calculate segment properties
            density = self.segmenter.calculate_semantic_density(segment_text)
            
            segments.append({
                'text': segment_text,
                'start': start_pos,
                'end': end_pos,
                'start_type': start_type,
                'end_type': end_type,
                'level': start_level,
                'density': density,
                'length': len(segment_text),
                'sentences': self._count_sentences(segment_text)
            })
        
        return segments
    
    def _refine_segments(self, segments: List[Dict]) -> List[Dict]:
        """Refine segments based on semantic cohesion"""
        refined = []
        
        for segment in segments:
            # If segment is too small, consider merging with next
            if segment['length'] < self.config.min_chunk_size and refined:
                last_segment = refined[-1]
                
                # Check if merging is semantically appropriate
                if self._should_merge(last_segment, segment):
                    refined[-1] = self._merge_segments(last_segment, segment)
                    continue
            
            # If segment has high density and is large, split it
            elif segment['density'] > 3.0 and segment['length'] > 300:
                split_segments = self._split_dense_segment(segment)
                refined.extend(split_segments)
                continue
            
            refined.append(segment)
        
        return refined
    
    def _apply_size_constraints(self, segments: List[Dict]) -> List[Dict]:
        """Apply size constraints with intelligent splitting"""
        final_chunks = []
        
        for segment in segments:
            if segment['length'] <= self.config.max_chunk_size:
                final_chunks.append(segment)
                continue
            
            # Need to split this segment
            sub_segments = self._split_by_semantic_units(segment['text'])
            
            for sub_text in sub_segments:
                if not sub_text.strip():
                    continue
                
                density = self.segmenter.calculate_semantic_density(sub_text)
                
                final_chunks.append({
                    'text': sub_text.strip(),
                    'start': segment['start'],
                    'end': segment['end'],
                    'start_type': segment['start_type'],
                    'end_type': segment['end_type'],
                    'level': segment['level'],
                    'density': density,
                    'length': len(sub_text.strip()),
                    'sentences': self._count_sentences(sub_text)
                })
        
        return final_chunks
    
    def _split_by_semantic_units(self, text: str) -> List[str]:
        """Split text at natural semantic boundaries"""
        units = []
        
        # Try splitting by sentences first
        sentences = self._split_sentences(text)
        current_unit = ""
        
        for sentence in sentences:
            if len(current_unit) + len(sentence) <= self.config.target_chunk_size:
                current_unit += sentence
            else:
                if current_unit:
                    units.append(current_unit)
                current_unit = sentence
        
        if current_unit:
            units.append(current_unit)
        
        # If units are still too large, split by clauses
        refined_units = []
        for unit in units:
            if len(unit) <= self.config.max_chunk_size:
                refined_units.append(unit)
            else:
                clauses = self._split_clauses(unit)
                refined_units.extend(clauses)
        
        return refined_units
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences preserving special patterns"""
        # Protect special patterns
        protected = []
        for i, pattern in enumerate(self.config.preserve_patterns):
            matches = list(re.finditer(pattern, text, re.DOTALL))
            for match in matches:
                placeholder = f"__SENT_PROTECT_{i}_{len(protected)}__"
                protected.append((placeholder, match.group()))
                text = text[:match.start()] + placeholder + text[match.end():]
        
        # Split sentences
        sentences = []
        pattern = self.config.sentence_split_patterns[0]
        chunks = re.split(pattern, text)
        
        # Restore protected patterns
        for chunk in chunks:
            for placeholder, original in protected:
                chunk = chunk.replace(placeholder, original)
            if chunk.strip():
                sentences.append(chunk.strip())
        
        return sentences
    
    def _split_clauses(self, text: str) -> List[str]:
        """Split long sentences into clauses"""
        clauses = []
        
        # Common clause separators
        separators = [
            r',\s+(?:and|or|but)\s+',
            r';\s+',
            r',\s+(?=which|that|who|where|when)',
            r'\s+—\s+',
        ]
        
        current = text
        for separator in separators:
            if len(current) <= self.config.max_chunk_size:
                break
            parts = re.split(separator, current, maxsplit=1)
            if len(parts) > 1:
                if parts[0]:
                    clauses.append(parts[0])
                current = parts[1] if len(parts) > 1 else ""
        
        if current:
            clauses.append(current)
        
        return clauses if clauses else [text]
    
    def _should_merge(self, segment1: Dict, segment2: Dict) -> bool:
        """Determine if two segments should be merged semantically"""
        # Don't merge if combined would be too large
        if segment1['length'] + segment2['length'] > self.config.max_chunk_size:
            return False
        
        # Don't merge across major boundaries
        if segment1['end_type'] in ['major_section', 'question'] and segment2['start_type'] != segment1['end_type']:
            return False
        
        # Don't merge if density difference is too high
        if abs(segment1['density'] - segment2['density']) > 5.0:
            return False
        
        # Merge if they share similar hierarchy level
        if abs(segment1['level'] - segment2['level']) <= 1:
            return True
        
        return False
    
    def _merge_segments(self, seg1: Dict, seg2: Dict) -> Dict:
        """Merge two segments"""
        merged_text = seg1['text'] + '\n\n' + seg2['text']
        
        return {
            'text': merged_text,
            'start': seg1['start'],
            'end': seg2['end'],
            'start_type': seg1['start_type'],
            'end_type': seg2['end_type'],
            'level': min(seg1['level'], seg2['level']),
            'density': (seg1['density'] * seg1['length'] + seg2['density'] * seg2['length']) / 
                      (seg1['length'] + seg2['length']),
            'length': seg1['length'] + seg2['length'],
            'sentences': seg1['sentences'] + seg2['sentences']
        }
    
    def _split_dense_segment(self, segment: Dict) -> List[Dict]:
        """Split a dense segment into smaller chunks"""
        text = segment['text']
        chunks = []
        
        # For dense technical content, split by lines or specific markers
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            line_length = len(line)
            
            # Technical lines (formulas, code) get their own chunks or small groups
            if re.search(r'\$|\\[a-zA-Z]|```', line):
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Very dense lines might need to be standalone
                if line_length > 100 and re.search(r'\$\$.*\$\$|```', line):
                    chunks.append(line)
                else:
                    current_chunk.append(line)
                    current_length += line_length
            else:
                if current_length + line_length > 200 and current_chunk:  # Smaller chunks for dense content
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = [line]
                    current_length = line_length
                else:
                    current_chunk.append(line)
                    current_length += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # Convert to segment format
        segments = []
        for chunk_text in chunks:
            density = self.segmenter.calculate_semantic_density(chunk_text)
            segments.append({
                'text': chunk_text,
                'start': segment['start'],
                'end': segment['end'],
                'start_type': segment['start_type'],
                'end_type': segment['end_type'],
                'level': segment['level'],
                'density': density,
                'length': len(chunk_text),
                'sentences': self._count_sentences(chunk_text)
            })
        
        return segments
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text"""
        # Simple sentence counting
        sentences = re.split(r'[.!?]+', text)
        return len([s for s in sentences if s.strip()])
    
    def _add_metadata(self, chunks: List[Dict], full_text: str) -> List[Dict[str, any]]:
        """Add comprehensive metadata to chunks"""
        final_chunks = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(chunk['text'].encode()).hexdigest()[:16]
            
            # Extract title/heading
            title = self._extract_title(chunk['text'], chunk['start_type'])
            
            # Extract tags
            tags = self._extract_tags(chunk['text'])
            
            # Estimate token count (approx 4 chars per token)
            token_estimate = len(chunk['text']) // 4
            
            # Create header
            header = f"[CHUNK {i+1} — {tags}]"
            
            # Combine header with text
            full_chunk_text = f"{header}\n{chunk['text']}"
            
            final_chunks.append({
                'chunk_id': f"chunk_{i+1:03d}_{chunk_id}",
                'title': title,
                'level': chunk['level'],
                'text': full_chunk_text,
                'original_text': chunk['text'],
                'tokens': token_estimate,
                'density': chunk['density'],
                'sentences': chunk['sentences'],
                'start_type': chunk['start_type'],
                'end_type': chunk['end_type'],
                'tags': tags,
                'char_length': chunk['length']
            })
        
        return final_chunks
    
    def _extract_title(self, text: str, start_type: str) -> str:
        """Extract or infer title for chunk"""
        lines = text.split('\n')
        
        # Look for heading-like lines
        for line in lines[:3]:  # Check first 3 lines
            line_stripped = line.strip()
            if len(line_stripped) < 100 and re.search(r'^[A-Z][^a-z]*$|^[A-Z].*[:]$', line_stripped):
                return line_stripped[:100]
        
        # Infer from content
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        if words:
            return ' '.join(words[:3])
        
        # Use start type as fallback
        return start_type.replace('_', ' ').title()
    
    def _extract_tags(self, text: str, max_tags: int = 5) -> str:
        """Extract meaningful tags from text"""
        # Remove common patterns first
        cleaned = re.sub(r'\$.*?\$', '', text)  # Remove math
        cleaned = re.sub(r'`.*?`', '', cleaned)  # Remove code
        
        # Get words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned.lower())
        
        # Filter and count
        filtered = [w for w in words if w not in self.config.stopwords]
        freq = Counter(filtered)
        
        # Prioritize nouns and technical terms
        top_words = freq.most_common(max_tags * 2)
        
        # Score words (simple heuristic)
        scored_words = []
        for word, count in top_words:
            score = count
            # Boost technical sounding words
            if len(word) > 5 and re.search(r'[tion|ment|ity|ism|logy]$', word):
                score *= 1.5
            if word and word[0].isupper() and word in text:  # Proper noun
                score *= 2.0
            scored_words.append((word, score))
        
        # Sort by score and take top
        scored_words.sort(key=lambda x: x[1], reverse=True)
        top_tags = [word for word, score in scored_words[:max_tags]]
        
        return ', '.join(top_tags) if top_tags else "general"

# ==================== FILE PROCESSOR ====================
class AdvancedFileProcessor:
    """Enhanced file processor with chunking capabilities"""
    
    def __init__(self):
        self.chunker = AdvancedChunker()
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from various file formats"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self._extract_from_pdf(file_path)
        elif ext == '.docx':
            return self._extract_from_docx(file_path)
        elif ext == '.txt':
            return self._extract_from_txt(file_path)
        elif ext == '.csv':
            return self._extract_from_csv(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF with better handling of font encoding"""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract with multiple strategies
                page_text = page.extract_text(x_tolerance=1, y_tolerance=1)
                
                # Fix CID codes (font encoding issues)
                if page_text:
                    # Remove or convert CID codes
                    page_text = re.sub(r'\(cid:\d+\)', ' ', page_text)
                    page_text = re.sub(r'\uf0b7', '•', page_text)  # Replace bullet chars
                    
                    # Clean up excessive whitespace but preserve structure
                    page_text = re.sub(r'\s+', ' ', page_text)
                    
                    # Add page marker for boundaries
                    text_parts.append(f"\n\n--- Page {page_num} ---\n\n")
                    text_parts.append(page_text)
                else:
                    # Try alternative extraction for scanned pages
                    try:
                        page_text = page.extract_text(layout=True)
                        if page_text:
                            text_parts.append(f"\n\n--- Page {page_num} (layout) ---\n\n")
                            text_parts.append(page_text)
                    except:
                        pass
        
        full_text = ''.join(text_parts)
        
        # Additional cleaning for PDF artifacts
        full_text = re.sub(r'\x00', '', full_text)  # Remove null bytes
        full_text = re.sub(r'\s*\n\s*\n\s*', '\n\n', full_text)  # Normalize line breaks
        
        return full_text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX with structure"""
        doc = docx.Document(file_path)
        paragraphs = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # Preserve heading styles
                if para.style.name.startswith('Heading'):
                    level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                    paragraphs.append(f"\n{'#' * level} {text}\n")
                else:
                    paragraphs.append(text)
        
        return '\n'.join(paragraphs)
    
    def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _extract_from_csv(self, file_path: str) -> str:
        """Extract text from CSV file"""
        text_lines = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row in reader:
                text_lines.append(' | '.join(row))
        return '\n'.join(text_lines)
    
    def process_file(self, file_path: str) -> List[Dict[str, any]]:
        """Process file and return optimized chunks"""
        # Extract text
        raw_text = self.extract_text(file_path)
        
        # Create chunks
        chunks = self.chunker.create_chunks(raw_text)
        
        # Format output as requested
        formatted_chunks = []
        for chunk in chunks:
            formatted_chunks.append(chunk['text'])
        
        return formatted_chunks

# ==================== MAIN EXECUTION ====================
def process_file(file_path: str):
    """
    Main function to process file and return optimized chunks.
    """
    processor = AdvancedFileProcessor()
    
    try:
        # Use the debug version or regular version
        chunks = processor.process_file(file_path)
        
        # Validate chunks
        if not chunks or len(chunks) < 3:
            print(f"Warning: Only {len(chunks)} chunks created. Check PDF extraction.")
            
        return chunks
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error details: {error_details}")
        return [f"Error processing file: {str(e)}\nDebug info saved to debug_*.txt files"]



# Basic English stopwords list (can be expanded)
STOPWORDS = {
    'the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with', 'as', 'by',
    'an', 'at', 'from', 'this', 'that', 'it', 'be', 'are', 'was', 'were', 'or',
    'but', 'not', 'have', 'has', 'had', 'can', 'will', 'would', 'should', 'could'
}

def fast_tag_extractor(text_chunk: str, top_n: int = 3) -> str:
    """
    Quickly extracts tags from a text chunk using regex and frequency analysis.

    Args:
        text_chunk (str): The input text.
        top_n (int): Number of top tags to return.

    Returns:
        List[str]: A list of relevant tags.
    """
    # Normalize text: lowercase and remove punctuation
    text = re.sub(r'[^\w\s]', '', text_chunk.lower())

    # Tokenize and filter
    tokens = text.split()
    filtered = [word for word in tokens if word not in STOPWORDS and len(word) > 2]

    # Frequency count
    freq = Counter(filtered)

    # Return top N tags as comma-separated string
    return ', '.join([word for word, _ in freq.most_common(top_n)])

# The system is ready to use. Call process_file(file_path) to get optimized chunks.