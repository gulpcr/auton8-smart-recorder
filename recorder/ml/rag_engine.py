"""RAG (Retrieval Augmented Generation) engine for statement verification."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pickle

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# Optional PDF support
try:
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False
        logger.info("PDF support not available. Install pypdf or PyPDF2 for PDF ingestion.")


@dataclass
class Document:
    """Document in the knowledge base."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


@dataclass
class RetrievalResult:
    """Result of document retrieval."""
    document: Document
    score: float
    relevance_type: str  # "dense", "sparse", "hybrid"


@dataclass
class VerificationResult:
    """Result of statement verification."""
    is_verified: bool
    confidence: float
    supporting_documents: List[RetrievalResult]
    citations: List[str]
    explanation: str


class RAGEngine:
    """
    Retrieval-Augmented Generation engine for verifying statements
    against SOP/FAQ/compliance documents.
    Uses FAISS for dense retrieval and BM25 for sparse retrieval.
    """
    
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",  # Smaller, faster model
        index_path: Optional[Path] = None
    ):
        self.embedding_model_name = embedding_model_name
        self.embedding_model: Optional[SentenceTransformer] = None
        self.faiss_index: Optional[faiss.Index] = None
        self.bm25_index: Optional[BM25Okapi] = None
        self.documents: List[Document] = []
        self.index_path = (
            Path(index_path).resolve()
            if index_path
            else Path(__file__).resolve().parent.parent.parent / "data" / "rag_index"
        )
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self._initialize_embedding_model()
    
    def _initialize_embedding_model(self):
        """Load embedding model for dense retrieval."""
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            # Fallback to smaller model
            try:
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded fallback embedding model: all-MiniLM-L6-v2")
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {e2}")
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32
    ):
        """
        Add documents to the knowledge base.
        
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
            batch_size: Batch size for embedding generation
        """
        if not self.embedding_model:
            logger.error("Embedding model not available")
            return
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Generate embeddings
            contents = [doc["content"] for doc in batch]
            try:
                embeddings = self.embedding_model.encode(
                    contents,
                    convert_to_numpy=True,
                    show_progress_bar=True
                )
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                continue
            
            # Create document objects
            for doc_dict, embedding in zip(batch, embeddings):
                doc = Document(
                    id=doc_dict["id"],
                    content=doc_dict["content"],
                    metadata=doc_dict.get("metadata", {}),
                    embedding=embedding
                )
                self.documents.append(doc)
        
        logger.info(f"Added {len(documents)} documents to knowledge base")
        self._build_indices()
    
    def _build_indices(self):
        """Build FAISS and BM25 indices from documents."""
        if not self.documents:
            logger.warning("No documents to index")
            return
        
        # Build FAISS index (dense retrieval)
        embeddings = np.array([doc.embedding for doc in self.documents])
        dimension = embeddings.shape[1]
        
        # Use IVF (Inverted File) index for large collections
        if len(self.documents) > 1000:
            n_clusters = int(np.sqrt(len(self.documents)))
            quantizer = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
            self.faiss_index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
            
            # Train the index
            self.faiss_index.train(embeddings)
        else:
            # Flat index for small collections
            self.faiss_index = faiss.IndexFlatIP(dimension)
        
        # Add embeddings to FAISS
        faiss.normalize_L2(embeddings)  # Normalize for cosine similarity
        self.faiss_index.add(embeddings)
        
        logger.info(f"Built FAISS index with {len(self.documents)} documents")
        
        # Build BM25 index (sparse retrieval)
        tokenized_docs = [doc.content.lower().split() for doc in self.documents]
        self.bm25_index = BM25Okapi(tokenized_docs)
        
        logger.info("Built BM25 index")
    
    def retrieve_dense(
        self,
        query: str,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Dense retrieval using FAISS (semantic search).
        """
        if not self.embedding_model or not self.faiss_index:
            return []
        
        # Generate query embedding
        try:
            query_embedding = self.embedding_model.encode(
                query,
                convert_to_numpy=True
            )
            query_embedding = query_embedding.reshape(1, -1)
            faiss.normalize_L2(query_embedding)
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return []
        
        # Search FAISS index
        scores, indices = self.faiss_index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                results.append(RetrievalResult(
                    document=self.documents[idx],
                    score=float(score),
                    relevance_type="dense"
                ))
        
        return results
    
    def retrieve_sparse(
        self,
        query: str,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Sparse retrieval using BM25 (keyword matching).
        """
        if not self.bm25_index:
            return []
        
        # Tokenize query
        query_tokens = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(RetrievalResult(
                    document=self.documents[idx],
                    score=float(scores[idx]),
                    relevance_type="sparse"
                ))
        
        return results
    
    def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.7
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval combining dense and sparse methods.
        
        Args:
            query: Query string
            top_k: Number of results to return
            dense_weight: Weight for dense scores (0-1), sparse gets (1-dense_weight)
        """
        # Get results from both methods
        dense_results = self.retrieve_dense(query, top_k * 2)
        sparse_results = self.retrieve_sparse(query, top_k * 2)
        
        # Normalize scores
        if dense_results:
            max_dense = max(r.score for r in dense_results)
            for r in dense_results:
                r.score = r.score / max_dense if max_dense > 0 else 0.0
        
        if sparse_results:
            max_sparse = max(r.score for r in sparse_results)
            for r in sparse_results:
                r.score = r.score / max_sparse if max_sparse > 0 else 0.0
        
        # Combine scores
        doc_scores: Dict[str, Tuple[float, Document]] = {}
        
        for result in dense_results:
            doc_id = result.document.id
            score = result.score * dense_weight
            doc_scores[doc_id] = (score, result.document)
        
        sparse_weight = 1.0 - dense_weight
        for result in sparse_results:
            doc_id = result.document.id
            if doc_id in doc_scores:
                doc_scores[doc_id] = (
                    doc_scores[doc_id][0] + result.score * sparse_weight,
                    result.document
                )
            else:
                doc_scores[doc_id] = (
                    result.score * sparse_weight,
                    result.document
                )
        
        # Sort by combined score
        sorted_results = sorted(
            doc_scores.items(),
            key=lambda x: x[1][0],
            reverse=True
        )[:top_k]
        
        return [
            RetrievalResult(
                document=doc,
                score=score,
                relevance_type="hybrid"
            )
            for _, (score, doc) in sorted_results
        ]
    
    def verify_statement(
        self,
        statement: str,
        context: Optional[str] = None,
        top_k: int = 5
    ) -> VerificationResult:
        """
        Verify a statement against the knowledge base.
        
        Args:
            statement: Statement to verify
            context: Optional context for the statement
            top_k: Number of documents to retrieve
        
        Returns:
            Verification result with confidence and supporting docs
        """
        # Build query
        query = statement
        if context:
            query = f"{context} {statement}"
        
        # Retrieve relevant documents
        results = self.retrieve_hybrid(query, top_k=top_k)
        
        if not results:
            return VerificationResult(
                is_verified=False,
                confidence=0.0,
                supporting_documents=[],
                citations=[],
                explanation="No relevant documents found"
            )
        
        # Calculate verification confidence
        # In production, use cross-encoder for re-ranking
        avg_score = sum(r.score for r in results) / len(results)
        
        # Extract citations
        citations = [
            f"{r.document.metadata.get('source', 'Unknown')}: {r.document.content[:100]}..."
            for r in results[:3]
        ]
        
        # Determine verification
        threshold = 0.6
        is_verified = avg_score >= threshold
        
        explanation = (
            f"Statement verified with {avg_score:.2f} confidence based on "
            f"{len(results)} supporting documents"
            if is_verified
            else f"Statement could not be verified (confidence: {avg_score:.2f})"
        )
        
        return VerificationResult(
            is_verified=is_verified,
            confidence=avg_score,
            supporting_documents=results,
            citations=citations,
            explanation=explanation
        )
    
    def save_index(self):
        """Save FAISS index and documents to disk."""
        if not self.faiss_index or not self.documents:
            logger.warning("No index to save")
            return
        
        # Save FAISS index
        faiss_path = self.index_path / "faiss.index"
        faiss.write_index(self.faiss_index, str(faiss_path))
        
        # Save documents
        docs_path = self.index_path / "documents.pkl"
        with open(docs_path, "wb") as f:
            pickle.dump(self.documents, f)
        
        # Save BM25 index
        bm25_path = self.index_path / "bm25.pkl"
        with open(bm25_path, "wb") as f:
            pickle.dump(self.bm25_index, f)
        
        logger.info(f"Saved index to {self.index_path}")
    
    def load_index(self):
        """Load FAISS index and documents from disk."""
        faiss_path = self.index_path / "faiss.index"
        docs_path = self.index_path / "documents.pkl"
        bm25_path = self.index_path / "bm25.pkl"

        if not faiss_path.exists() or not docs_path.exists():
            logger.warning(f"Index not found at {self.index_path}")
            return

        # Validate paths don't escape project directory
        import os
        for p in [faiss_path, docs_path, bm25_path]:
            resolved = p.resolve()
            if ".." in os.path.relpath(str(resolved), os.getcwd()):
                logger.warning(f"Refusing to load index from outside project: {p}")
                return

        try:
            # Load FAISS index
            self.faiss_index = faiss.read_index(str(faiss_path))

            # Load documents
            with open(docs_path, "rb") as f:
                self.documents = pickle.load(f)

            # Load BM25 index
            if bm25_path.exists():
                with open(bm25_path, "rb") as f:
                    self.bm25_index = pickle.load(f)

            logger.info(f"Loaded index from {self.index_path} ({len(self.documents)} documents)")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
    
    def chunk_document(
        self,
        content: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[str]:
        """
        Chunk large document into smaller pieces with overlap.
        """
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def ingest_documents_from_directory(
        self,
        directory: Path,
        extensions: List[str] = [".txt", ".md", ".pdf"]
    ):
        """
        Ingest documents from a directory.
        """
        directory = Path(directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return
        
        documents = []
        
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                try:
                    # Read file
                    if ext == ".pdf":
                        content = self._read_pdf(file_path)
                        if not content:
                            continue
                    else:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    
                    # Chunk document
                    chunks = self.chunk_document(content)
                    
                    # Create document entries
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{file_path.stem}_chunk_{i}"
                        documents.append({
                            "id": doc_id,
                            "content": chunk,
                            "metadata": {
                                "source": str(file_path),
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            }
                        })
                
                except Exception as e:
                    logger.error(f"Failed to ingest {file_path}: {e}")
        
        if documents:
            self.add_documents(documents)
            logger.info(f"Ingested {len(documents)} document chunks from {directory}")

    def _read_pdf(self, file_path: Path) -> Optional[str]:
        """
        Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text or None if failed
        """
        if not PDF_AVAILABLE:
            logger.warning(f"PDF support not available, skipping: {file_path}")
            return None

        try:
            text_parts = []

            with open(file_path, 'rb') as f:
                # Try pypdf first (newer API)
                if hasattr(pypdf, 'PdfReader'):
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                else:
                    # Fallback to PyPDF2 API
                    reader = pypdf.PdfFileReader(f)
                    for page_num in range(reader.numPages):
                        page = reader.getPage(page_num)
                        page_text = page.extractText()
                        if page_text:
                            text_parts.append(page_text)

            content = "\n\n".join(text_parts)

            if not content.strip():
                logger.warning(f"No text extracted from PDF: {file_path}")
                return None

            logger.debug(f"Extracted {len(content)} chars from PDF: {file_path}")
            return content

        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the RAG engine.

        Returns:
            Dictionary with document count, index status, etc.
        """
        stats = {
            "total_documents": len(self.documents),
            "embedding_model": self.embedding_model_name,
            "embedding_model_loaded": self.embedding_model is not None,
            "faiss_index_ready": self.faiss_index is not None,
            "bm25_index_ready": self.bm25_index is not None,
            "index_path": str(self.index_path),
        }

        if self.documents:
            # Calculate average document length
            avg_length = sum(len(doc.content) for doc in self.documents) / len(self.documents)
            stats["avg_document_length"] = round(avg_length, 1)

            # Get unique sources
            sources = set()
            for doc in self.documents:
                source = doc.metadata.get("source", "unknown")
                sources.add(source)
            stats["unique_sources"] = len(sources)

        if self.faiss_index is not None:
            stats["faiss_index_size"] = self.faiss_index.ntotal

        return stats

    def clear(self):
        """Clear all documents and indices."""
        self.documents = []
        self.faiss_index = None
        self.bm25_index = None
        logger.info("RAG engine cleared")

    def is_ready(self) -> bool:
        """Check if the RAG engine is ready for queries."""
        return (
            self.embedding_model is not None and
            self.faiss_index is not None and
            len(self.documents) > 0
        )
