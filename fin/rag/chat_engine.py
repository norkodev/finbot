"""Chat engine with RAG for financial questions."""

from typing import List, Dict, Optional
import requests
import json

from .retrieval import RetrievalEngine
from .prompts import (
    build_rag_prompt,
    detect_out_of_scope,
    OUT_OF_SCOPE_RESPONSE,
    CLARIFICATION_PROMPT
)


class ChatEngine:
    """Chat engine with RAG for answering financial questions."""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        top_k: int = 5,
        timeout: int = 60
    ):
        """
        Initialize chat engine.
        
        Args:
            ollama_url: Ollama API URL
            model: LLM model name
            top_k: Number of documents to retrieve
            timeout: Timeout for LLM calls in seconds
        """
        self.ollama_url = ollama_url
        self.model = model
        self.top_k = top_k
        self.timeout = timeout
        self.retrieval = RetrievalEngine()
        self.conversation_history: List[Dict] = []
    
    def chat(
        self,
        question: str,
        use_history: bool = True
    ) -> Dict[str, any]:
        """
        Answer question using RAG.
        
        Args:
            question: User question
            use_history: Include conversation history in context
        
        Returns:
            {
                'answer': str,
                'sources': List[Dict],
                'confidence': float,
                'error': Optional[str]
            }
        """
        # 1. Check if out of scope
        if detect_out_of_scope(question):
            return {
                'answer': OUT_OF_SCOPE_RESPONSE,
                'sources': [],
                'confidence': 1.0,
                'error': None
            }
        
        # 2. Retrieve relevant documents
        try:
            docs = self.retrieval.retrieve(question, top_k=self.top_k)
        except Exception as e:
            return {
                'answer': f"Error al buscar documentos: {e}",
                'sources': [],
                'confidence': 0.0,
                'error': str(e)
            }
        
        if not docs:
            return {
                'answer': "No encontré información relevante sobre eso en tus estados de cuenta. ¿Podrías ser más específico?",
                'sources': [],
                'confidence': 0.0,
                'error': None
            }
        
        # 3. Build prompt with context
        history = self.conversation_history if use_history else None
        prompt = build_rag_prompt(question, docs, history)
        
        # 4. Call Ollama LLM
        try:
            answer = self._call_ollama(prompt)
        except requests.exceptions.Timeout:
            return {
                'answer': "La respuesta tardó demasiado. Por favor, intenta con una pregunta más simple.",
                'sources': docs,
                'confidence': 0.0,
                'error': 'timeout'
            }
        except Exception as e:
            return {
                'answer': f"Error al generar respuesta: {e}. Asegúrate de que Ollama esté corriendo.",
                'sources': docs,
                'confidence': 0.0,
                'error': str(e)
            }
        
        # 5. Calculate confidence
        confidence = self._estimate_confidence(docs)
        
        # 6. Save to conversation history
        self.conversation_history.append({
            'question': question,
            'answer': answer,
            'sources': docs
        })
        
        return {
            'answer': answer,
            'sources': docs,
            'confidence': confidence,
            'error': None
        }
    
    def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama API to generate response.
        
        Args:
            prompt: Full prompt with context
        
        Returns:
            Generated response text
        """
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower for more factual responses
                    "top_p": 0.9
                }
            },
            timeout=self.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result.get('response', '')
    
    def _estimate_confidence(self, docs: List[Dict]) -> float:
        """
        Estimate confidence based on retrieval scores.
        
        Args:
            docs: Retrieved documents with distance scores
        
        Returns:
            Confidence score between 0 and 1
        """
        if not docs:
            return 0.0
        
        # Average distance of retrieved docs
        distances = [doc.get('distance', 1.0) for doc in docs]
        avg_distance = sum(distances) / len(distances)
        
        # Convert distance to confidence
        # Assuming cosine distance in [0, 2], lower is better
        confidence = max(0.0, min(1.0, 1.0 - (avg_distance / 2.0)))
        
        return confidence
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_last_sources(self) -> List[Dict]:
        """Get sources from last response."""
        if self.conversation_history:
            return self.conversation_history[-1].get('sources', [])
        return []
    
    def health_check(self) -> bool:
        """
        Check if Ollama is available.
        
        Returns:
            True if Ollama is responsive, False otherwise
        """
        try:
            response = requests.get(
                f"{self.ollama_url}/api/version",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
