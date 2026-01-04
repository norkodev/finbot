"""LLM-based classification for transactions that don't match rules."""

import json
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import time


class LLMClassifier:
    """Classifier using local LLM via Ollama for fallback classification."""
    
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        timeout: int = 30,
        max_retries: int = 2
    ):
        """
        Initialize LLM classifier.
        
        Args:
            model: Ollama model name to use
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
            max_retries: Number of retries on failure
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache = {}  # Simple in-memory cache
    
    def classify_batch(
        self,
        transactions: List[Dict],
        max_batch_size: int = 20
    ) -> List[Tuple[Optional[str], Optional[str], float]]:
        """
        Classify a batch of transactions.
        
        Args:
            transactions: List of transaction dicts with 'id', 'description', 'amount'
            max_batch_size: Maximum transactions per batch
        
        Returns:
            List of tuples (category, subcategory, confidence) for each transaction
        """
        results = []
        
        # Process in batches
        for i in range(0, len(transactions), max_batch_size):
            batch = transactions[i:i + max_batch_size]
            batch_results = self._classify_batch_internal(batch)
            results.extend(batch_results)
        
        return results
    
    def _classify_batch_internal(
        self,
        transactions: List[Dict]
    ) -> List[Tuple[Optional[str], Optional[str], float]]:
        """Internal method to classify a single batch."""
        
        # Build prompt
        prompt = self._build_classification_prompt(transactions)
        
        # Check cache
        cache_key = self._get_cache_key(transactions)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Call LLM
        try:
            response = self._call_ollama(prompt)
            classifications = self._parse_response(response, len(transactions))
            
            # Cache results
            self._cache[cache_key] = classifications
            
            return classifications
        
        except Exception as e:
            print(f"LLM classification error: {e}")
            # Return None for all if LLM fails
            return [(None, None, 0.0) for _ in transactions]
    
    def _build_classification_prompt(self, transactions: List[Dict]) -> str:
        """Build prompt for transaction classification."""
        
        categories = {
            "alimentacion": ["supermercado", "restaurantes", "delivery", "cafe"],
            "transporte": ["rideshare", "gasolina", "peaje", "estacionamiento"],
            "entretenimiento": ["streaming", "cine", "eventos"],
            "salud": ["farmacia", "medico", "gym"],
            "servicios": ["telefonia", "internet", "agua", "luz", "gas"],
            "compras": ["ropa", "tiendas", "online", "departamental"],
            "gastos_hormiga": ["conveniencia"],
            "financiero": ["intereses", "comisiones", "retiro_efectivo"],
            "pagos": ["transferencia"]
        }
        
        # Build transaction list
        trans_list = []
        for idx, trans in enumerate(transactions, 1):
            desc = trans.get('description', 'N/A')
            amount = trans.get('amount', 0)
            trans_list.append(f"{idx}. {desc} - ${amount:,.2f}")
        
        prompt = f"""Clasifica estas transacciones bancarias en México.

CATEGORÍAS VÁLIDAS:
{json.dumps(categories, indent=2, ensure_ascii=False)}

TRANSACCIONES:
{chr(10).join(trans_list)}

INSTRUCCIONES:
1. Para cada transacción, determina la categoría y subcategoría más apropiada
2. Si no estás seguro, usa tu mejor juicio basado en el nombre del comercio
3. Responde SOLO con un JSON válido, sin explicaciones adicionales
4. Calidad del resultado: usa contexto mexicano (OXXO=gastos_hormiga, UBER=transporte, etc)

FORMATO DE RESPUESTA (JSON):
[
  {{"id": 1, "category": "categoria", "subcategory": "subcategoria", "confidence": 0.95}},
  {{"id": 2, "category": "categoria", "subcategory": "subcategoria", "confidence": 0.80}}
]

Responde SOLO el JSON array:"""
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API."""
        
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic output
                "num_predict": 500   # Limit response length
            }
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get('response', '')
            
            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception(f"Ollama timeout after {self.max_retries + 1} attempts")
            
            except requests.exceptions.RequestException as e:
                raise Exception(f"Ollama API error: {e}")
        
        raise Exception("Max retries exceeded")
    
    def _parse_response(
        self,
        response: str,
        expected_count: int
    ) -> List[Tuple[Optional[str], Optional[str], float]]:
        """Parse LLM JSON response."""
        
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON array found in response")
            
            json_str = response[start_idx:end_idx]
            classifications = json.loads(json_str)
            
            # Convert to tuples
            results = []
            for item in classifications:
                category = item.get('category')
                subcategory = item.get('subcategory')
                confidence = float(item.get('confidence', 0.5))
                results.append((category, subcategory, confidence))
            
            # Pad with None if needed
            while len(results) < expected_count:
                results.append((None, None, 0.0))
            
            return results[:expected_count]
        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Failed to parse LLM response: {e}")
            print(f"Response was: {response[:200]}")
            return [(None, None, 0.0) for _ in range(expected_count)]
    
    def _get_cache_key(self, transactions: List[Dict]) -> str:
        """Generate cache key for transactions."""
        # Use description + amount as key
        key_parts = [
            f"{t.get('description', '')}:{t.get('amount', 0)}"
            for t in transactions
        ]
        return "|".join(key_parts)
    
    def health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            # Try a simple generation
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": "Hola",
                "stream": False,
                "options": {"num_predict": 5}
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        
        except Exception:
            return False
