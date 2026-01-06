from ..models import BodyChunk
from ..utils import sha256_bytes

class BodyChunker:
    CHUNK_SIZE = 64 * 1024
    
    def chunk_text(self, text: str) -> list[str]:
        if not text:
            return []
        
        chunks = []
        text_bytes = text.encode('utf-8')
        
        for i in range(0, len(text_bytes), self.CHUNK_SIZE):
            chunk_bytes = text_bytes[i:i + self.CHUNK_SIZE]
            try:
                chunk = chunk_bytes.decode('utf-8')
            except UnicodeDecodeError:
                for j in range(len(chunk_bytes) - 1, max(0, len(chunk_bytes) - 4), -1):
                    try:
                        chunk = chunk_bytes[:j].decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    chunk = chunk_bytes.decode('utf-8', errors='replace')
            chunks.append(chunk)
        
        return chunks
    
    def store_chunks(self, message, text: str, html: str):
        BodyChunk.objects.filter(message=message).delete()
        
        for idx, chunk_content in enumerate(self.chunk_text(text)):
            BodyChunk.objects.create(
                message=message,
                chunk_type='text',
                chunk_index=idx,
                content=chunk_content,
                content_hash=sha256_bytes(chunk_content.encode('utf-8')),
            )
        
        for idx, chunk_content in enumerate(self.chunk_text(html)):
            BodyChunk.objects.create(
                message=message,
                chunk_type='html',
                chunk_index=idx,
                content=chunk_content,
                content_hash=sha256_bytes(chunk_content.encode('utf-8')),
            )
    
    @staticmethod
    def reconstruct_body(message, chunk_type='text') -> str:
        chunks = BodyChunk.objects.filter(
            message=message,
            chunk_type=chunk_type
        ).order_by('chunk_index').values_list('content', flat=True)
        return ''.join(chunks)

chunker = BodyChunker()

