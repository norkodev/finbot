"""Prompt templates and builders for financial RAG."""

from typing import List, Dict, Optional


SYSTEM_PROMPT = """Eres un asistente de finanzas personales para un usuario mexicano.
Tienes acceso a sus estados de cuenta, transacciones y compromisos financieros.

REGLAS IMPORTANTES:
1. Solo responde basándote en los documentos proporcionados en CONTEXTO
2. Si no tienes información suficiente, dilo claramente: "No tengo información sobre eso"
3. Siempre cita la fuente de tus datos entre corchetes: [Fuente: nombre del documento]
4. Usa formato mexicano para montos: $X,XXX.XX
5. Da recomendaciones accionables cuando sea apropiado
6. NO INVENTES números ni datos que no estén en el contexto

FORMATO DE RESPUESTA:
- Usa emojis apropiados para mejor lectura (📊 💰 📅 ⚠️ ✅)
- Sé conciso pero completo
- Usa listas cuando sea apropiado
- Termina con la cita de fuentes

CONTEXTO:
{context}

PREGUNTA DEL USUARIO:
{question}

RESPUESTA:"""


CLARIFICATION_PROMPT = """La pregunta del usuario es ambigua o no tengo suficiente contexto.

Pregunta: "{question}"

Documentos relevantes encontrados: {num_docs}

Por favor, responde amablemente pidiendo al usuario que sea más específico. 
Sugiere qué información adicional necesitas (mes, categoría, comercio, etc.)."""


OUT_OF_SCOPE_RESPONSE = """Lo siento, esa pregunta está fuera de mi alcance. 

Puedo ayudarte con:
- 📊 Gastos por categoría o comercio
- 📅 Compromisos financieros (MSI, suscripciones)
- 💰 Comparaciones entre meses
- 📈 Proyecciones de ahorro

No puedo ayudarte con:
- Inversiones en bolsa o criptomonedas
- Asesoría fiscal o contable
- Préstamos o créditos externos
- Recomendaciones de productos financieros"""


def build_rag_prompt(
    question: str,
    retrieved_docs: List[Dict],
    conversation_history: Optional[List[Dict]] = None
) -> str:
    """
    Build prompt for RAG with context from retrieved documents.
    
    Args:
        question: User question
        retrieved_docs: Documents retrieved from vector store
        conversation_history: Optional previous Q&A pairs
    
    Returns:
        Formatted prompt for LLM
    """
    if not retrieved_docs:
        return CLARIFICATION_PROMPT.format(
            question=question,
            num_docs=0
        )
    
    # Format context from retrieved documents
    context_parts = []
    
    for i, doc in enumerate(retrieved_docs, 1):
        # Extract metadata
        metadata = doc.get('metadata', {})
        month = metadata.get('month', 'N/A')
        doc_type = metadata.get('doc_type', 'documento')
        
        # Format document type in Spanish
        doc_type_map = {
            'summary': 'Resumen Mensual',
            'commitment': 'Compromisos',
            'merchant_profile': 'Perfil de Comercio'
        }
        doc_type_es = doc_type_map.get(doc_type, doc_type)
        
        # Add to context
        context_parts.append(
            f"--- Documento {i}: {doc_type_es} ({month}) ---\n"
            f"{doc['text']}\n"
        )
    
    context = "\n".join(context_parts)
    
    # Add conversation history if provided
    if conversation_history:
        history_str = "\n".join([
            f"Usuario: {turn['question']}\nAsistente: {turn['answer']}"
            for turn in conversation_history[-3:]  # Last 3 turns only
        ])
        context = f"HISTORIAL DE CONVERSACIÓN:\n{history_str}\n\n{context}"
    
    # Build final prompt
    return SYSTEM_PROMPT.format(
        context=context,
        question=question
    )


def detect_out_of_scope(question: str) -> bool:
    """
    Detect if question is outside the scope of the assistant.
    
    Args:
        question: User question
    
    Returns:
        True if out of scope, False otherwise
    """
    out_of_scope_keywords = [
        # Investments
        'inversion', 'invertir', 'acciones', 'bolsa', 'etf', 'cetes',
        'fondos de inversion', 'mercado de valores',
        
        # Crypto
        'crypto', 'criptomoneda', 'bitcoin', 'ethereum', 'nft',
        
        # Tax/Legal
        'impuesto', 'sat', 'declaracion', 'factura', 'rfc',
        'deduccion', 'fiscal',
        
        # External loans not in statements
        'credito hipotecario', 'prestamo personal', 'credito automotriz',
        
        # Insurance
        'seguro de vida', 'seguro de gastos',
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in out_of_scope_keywords)


def get_example_questions() -> List[str]:
    """Get list of example questions for help."""
    return [
        "¿Cuánto gasté en comida en diciembre?",
        "¿Qué compromisos terminan pronto?",
        "¿Cuánto gasto en OXXO al mes?",
        "¿Cuánto he pagado de intereses este año?",
        "¿En qué categoría gasto más?",
        "¿Cuántas suscripciones activas tengo?",
        "Compara mis gastos de noviembre vs diciembre",
    ]
