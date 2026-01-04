"""Guardrails and validation for RAG responses."""

import re
from typing import List, Dict, Tuple


class ResponseValidator:
    """Validate LLM responses to prevent hallucinations."""
    
    def validate_response(
        self,
        question: str,
        answer: str,
        sources: List[Dict]
    ) -> Dict:
        """
        Validate response quality and factual accuracy.
        
        Args:
            question: Original user question
            answer: LLM generated answer
            sources: Retrieved source documents
        
        Returns:
            {
                'is_valid': bool,
                'issues': List[str],
                'warnings': List[str]
            }
        """
        issues = []
        warnings = []
        
        # Check minimum length
        if len(answer.strip()) < 20:
            issues.append("Respuesta muy corta")
        
        # Check for citation
        if not self._has_citation(answer):
            warnings.append("Respuesta no cita fuentes explícitamente")
        
        # Check for number hallucination
        answer_numbers = self._extract_numbers(answer)
        source_numbers = []
        for source in sources:
            source_numbers.extend(self._extract_numbers(source['text']))
        
        for num in answer_numbers:
            # Only check significant numbers (> 100)
            if num > 100 and num not in source_numbers:
                # Allow some tolerance for rounding
                if not any(abs(num - src_num) / src_num < 0.05 for src_num in source_numbers if src_num > 0):
                    warnings.append(f"Número ${num:,.2f} no aparece exactamente en las fuentes")
        
        # Check for generic "no sé" responses
        no_info_phrases = [
            'no tengo información',
            'no encuentro',
            'no puedo ayudarte',
            'fuera de mi alcance'
        ]
        
        answer_lower = answer.lower()
        if any(phrase in answer_lower for phrase in no_info_phrases):
            # This is acceptable, just flag it
            warnings.append("Respuesta indica falta de información")
        
        is_valid = len(issues) == 0
        
        return {
            'is_valid': is_valid,
            'issues': issues,
            'warnings': warnings
        }
    
    def _has_citation(self, text: str) -> bool:
        """Check if text has source citation."""
        citation_markers = [
            '[fuente:',
            '[fuente ',
            'según',
            'de acuerdo',
            'basado en'
        ]
        
        text_lower = text.lower()
        return any(marker in text_lower for marker in citation_markers)
    
    def _extract_numbers(self, text: str) -> List[float]:
        """
        Extract monetary amounts from text.
        
        Args:
            text: Text to extract from
        
        Returns:
            List of numerical values
        """
        # Pattern for Mexican format: $1,234.56 or 1,234.56
        pattern = r'\$?\s?[\d,]+\.?\d*'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            try:
                # Clean and convert
                clean = match.replace('$', '').replace(',', '').replace(' ', '').strip()
                if clean:
                    num = float(clean)
                    numbers.append(num)
            except ValueError:
                continue
        
        return numbers
    
    def detect_hallucination_indicators(self, answer: str) -> List[str]:
        """
        Detect common hallucination patterns.
        
        Args:
            answer: LLM response
        
        Returns:
            List of detected hallucination indicators
        """
        indicators = []
        answer_lower = answer.lower()
        
        # Overly confident without sources
        confidence_without_source = [
            'definitivamente',
            'sin duda',
            'estoy seguro',
            'es claro que'
        ]
        
        if any(phrase in answer_lower for phrase in confidence_without_source):
            if not self._has_citation(answer):
                indicators.append("Alta confianza sin citar fuentes")
        
        # Specific financial advice (out of scope)
        advice_phrases = [
            'te recomiendo invertir',
            'deberías comprar',
            'es mejor vender',
            'te conviene'
        ]
        
        if any(phrase in answer_lower for phrase in advice_phrases):
            indicators.append("Dando consejos específicos de inversión (fuera de alcance)")
        
        # Made-up dates
        if 'próximo' in answer_lower or 'siguiente' in answer_lower:
            # Check if there's a specific date
            date_pattern = r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
            if re.search(date_pattern, answer):
                indicators.append("Fecha específica futura (posible alucinación)")
        
        return indicators


def check_ollama_availability(url: str = "http://localhost:11434") -> Tuple[bool, str]:
    """
    Check if Ollama is available and responsive.
    
    Args:
        url: Ollama API URL
    
    Returns:
        (is_available, message)
    """
    import requests
    
    try:
        response = requests.get(f"{url}/api/version", timeout=5)
        if response.status_code == 200:
            return True, "Ollama está disponible"
        else:
            return False, f"Ollama respondió con código {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "No se puede conectar a Ollama. ¿Está corriendo?"
    except requests.exceptions.Timeout:
        return False, "Timeout al conectar con Ollama"
    except Exception as e:
        return False, f"Error al verificar Ollama: {e}"
