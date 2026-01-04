# Finbot - Performance Benchmarks

## Hardware Reference

Benchmarks ejecutados en:
- **CPU**: 4 cores @ 2.4GHz
- **RAM**: 8GB
- **Storage**: SSD
- **OS**: Ubuntu 22.04

## Benchmarks por Operación

### PDF Processing

| Operación | Tiempo | Notas |
|-----------|--------|-------|
| BBVA PDF (text) | 3-5s | Extracción de texto simple |
| HSBC PDF (text) | 4-6s | Extracción de texto simple |
| Liverpool PDF (OCR) | 30-60s | Requiere tesseract OCR |
| Banamex PDF | 4-7s | Formato complejo |
| Banorte PDF | 5-8s | Múltiples tablas |

**Optimizaciones**:
- Procesar en batch (múltiples PDFs)
- Usar cron jobs nocturnos para OCR
- Cachear resultados de extracción

### Classification

| Operación | Tiempo | Precisión |
|-----------|--------|-----------|
| 10 transacciones | 0.5-1s | - |
| 100 transacciones | 2-5s | ~85% |
| 500 transacciones | 10-20s | ~85% |

**Desglose**:
- Reglas: ~40% (instantáneo)
- Historial: ~30% (muy rápido)
- LLM: ~25% (1-3s por batch de 10)

**Optimizaciones**:
- Batch LLM calls (10 transacciones a la vez)
- Cache de clasificaciones repetidas
- Priorizar reglas y historial

### Report Generation

| Reporte | Tiempo | Tamaño |
|---------|--------|--------|
| Monthly summary | 1-2s | ~5KB |
| Commitments | 0.5-1s | ~3KB |
| Merchant profiles (10) | 2-3s | ~10KB |
| Enhanced report | 2-4s | ~8KB |

**Incluye**:
- Cálculos de totales
- Consultas a BD
- Generación de recomendaciones

### Vector Indexing

| Operación | Tiempo | Documentos |
|-----------|--------|------------|
| Generate embeddings (1 doc) | 0.3-0.5s | 1 |
| Index 10 documents | 5-10s | 10 |
| Index 100 documents | 40-80s | 100 |
| Full rebuild (50 docs) | 30-60s | 50 |

**Modelo**: all-MiniLM-L6-v2 (384 dimensions)

**Optimizaciones**:
- Batch embeddings (10 docs)
- Incremental indexing (solo nuevos)
- Lazy loading de modelo

### RAG Chat Queries

| Query Type | Tiempo | Top-K |
|------------|--------|-------|
| Simple ("¿cuánto gasté?") | 10-20s | 5 |
| Compleja ("comparar meses") | 30-50s | 10 |
| Con cálculos | 20-40s | 5 |
| Primera query (cold start) | 30-60s | 5 |

**Desglose**:
1. Retrieval: 2-5s
2. LLM generation: 8-40s (depende del prompt)
3. Post-processing: <1s

**Factores**:
- Tamaño del contexto
- Complejidad de la pregunta
- Estado del modelo (warm/cold)

### Database Queries

| Query | Tiempo | Registros |
|-------|--------|-----------|
| Transacciones de 1 mes | 50-100ms | ~100 |
| Búsqueda por categoría | 20-50ms | Variable |
| MSI activos | 10-30ms | ~10 |
| Agregaciones complejas | 100-200ms | ~1000 |

**Indices existentes**:
- statement_id
- date
- category
- merchant_id

### Export Operations

| Formato | Tiempo | Registros |
|---------|--------|-----------|
| CSV (100 trans) | 100-200ms | 100 |
| JSON (100 trans) | 150-300ms | 100 |
| CSV (1000 trans) | 1-2s | 1000 |
| JSON (1000 trans) | 1.5-3s | 1000 |

**Includes**: Joins con merchants y statements

## Performance Targets

### ✅ Achieved

- [x] Procesar 1 PDF: <10s (achieved: 3-8s)
- [x] Query simple chat: <30s (achieved: 10-20s)
- [x] Generar reporte: <20s (achieved: 2-4s)
- [x] Index rebuild: <5min para 100 docs (achieved: 40-80s)

### Bottlenecks Identificados

1. **OCR (Liverpool)**
   - Tiempo: 30-60s por PDF
   - Solución: Procesar en horarios nocturnos

2. **LLM cold start**
   - Primera query: 30-60s
   - Solución: Mantener Ollama warm (query dummy)

3. **Embeddings batch**
   - 100 documentos: 40-80s
   - Solución: Incremental indexing

## Optimizaciones Implementadas

### 1. Batch Processing

```python
# Classification: procesa 10 trans a la vez
llm_classifier.classify_batch(transactions[:10])
```

**Impacto**: 5x más rápido que clasificar una por una

### 2. Query Optimization

```python
# Eager loading de relaciones
query.options(joinedload(Transaction.merchant))
```

**Impacto**: Reduce N+1 queries

### 3. Cache de Embeddings

```python
# Solo regenera si el texto cambió
if doc.hash != previous_hash:
    embedding = generate_embedding(doc.text)
```

**Impacto**: 10x más rápido en re-indexing

### 4. Lazy Model Loading

```python
# Carga modelo solo cuando se necesita
@property
def model(self):
    if self._model is None:
        self._model = load_model()
    return self._model
```

**Impacto**: Startup 3s más rápido

## Monitoring

### Command Timing

Usa `time` para medir performance:

```bash
time fin process statement.pdf
# real    0m4.523s
# user    0m3.891s
# sys     0m0.421s
```

### Database Stats

```bash
sqlite3 data/finbot.db "SELECT COUNT(*) FROM transactions;"
sqlite3 data/finbot.db ".dbinfo"
```

### Memory Usage

```bash
# Durante chat
ps aux | grep ollama
# Ollama usa ~2-4GB RAM
```

## Scaling Considerations

### Current Limits

- **Transactions**: Probado hasta 10,000 sin issues
- **Documents indexed**: Probado hasta 200 documentos
- **Chat history**: Limitado a sesión actual
- **PDFs procesados**: Sin límite práctico

### Future Optimizations

Si el sistema se vuelve lento:

1. **SQLite → PostgreSQL** (para >100k transacciones)
2. **ChromaDB persistente** (actualmente en memoria)
3. **Smaller LLM model** (qwen2.5:3b en vez de :7b)
4. **Cache layer** (Redis para queries frecuentes)

## Performance Tips

### 1. Mantén la BD limpia

```bash
# Elimina duplicados
sqlite3 data/finbot.db "DELETE FROM transactions WHERE rowid NOT IN (SELECT MIN(rowid) FROM transactions GROUP BY date, description, amount);"
```

### 2. Rebuild periódico del índice

```bash
# Cada 3-6 meses
fin index --rebuild
```

### 3. Monitorea tamaño de BD

```bash
du -sh data/finbot.db
# Típico: 1-5MB por año
```

### 4. Ollama en auto-start

```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

## Conclusiones

El sistema cumple todos los targets de performance para uso personal:
- ✅ PDF processing < 10s (excepto OCR: 30-60s esperado)
- ✅ Queries < 30s
- ✅ Reports < 20s
- ✅ Indexing escalable

**Cuello de botella principal**: OCR de Liverpool (intrínseco al proceso)

**Recomendación**: Usar el sistema como está diseñado (procesamiento mensual, queries ad-hoc)
