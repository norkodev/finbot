# Backlog MVP - Sistema de Inteligencia Financiera Personal

## Información del Proyecto

| Campo | Valor |
|-------|-------|
| **Duración** | 12 semanas |
| **Dedicación** | 2 hrs/día (~10 hrs/semana) |
| **Desarrollador** | 1 persona |
| **Entregables** | Cada 2 semanas |

---

## Épicas

| ID | Épica | Sprints | Prioridad |
|----|-------|---------|-----------|
| E1 | Ingesta y Extracción | 1-2 | 🔴 Crítica |
| E2 | Clasificación Inteligente | 3 | 🔴 Crítica |
| E3 | Documentos Derivados y Vectorización | 4 | 🔴 Crítica |
| E4 | RAG y Chat | 5 | 🔴 Crítica |
| E5 | Reportes y Análisis | 6 | 🟡 Alta |
| E6 | Refinamiento y Estabilización | 6 | 🟡 Alta |

---

## Sprint 1 (Semanas 1-2): Setup + Parser BBVA

### Objetivo
Tener el ambiente funcional y poder extraer transacciones de un estado de cuenta BBVA.

---

### E1-US01: Setup del ambiente de desarrollo
**Como** desarrollador  
**Quiero** tener el ambiente de desarrollo configurado  
**Para** poder comenzar a implementar el sistema

**Criterios de Aceptación:**
- [x] Repositorio git inicializado con estructura de carpetas
- [x] Virtual environment de Python creado
- [x] Dependencias instaladas (pdfplumber, pandas, click, etc.)
- [x] SQLite database inicializada con esquema base
- [x] Comando `fin --version` funciona y muestra versión
- [x] README con instrucciones de setup

**Tareas:**
1. Crear estructura de carpetas del proyecto
2. Crear requirements.txt y setup.py
3. Implementar CLI base con Click
4. Crear esquema inicial de SQLite
5. Documentar proceso de instalación

**Estimación:** 4 horas

---

### E1-US02: Modelo de datos para transacciones y MSI
**Como** desarrollador  
**Quiero** tener el modelo de datos definido  
**Para** almacenar transacciones y compromisos de forma estructurada

**Criterios de Aceptación:**
- [x] Tabla `statements` creada (metadata del estado de cuenta)
- [x] Tabla `transactions` creada con todos los campos necesarios
- [x] Tabla `installment_plans` creada para MSI (meses sin intereses)
- [x] Tabla `merchants` creada para catálogo de comercios
- [x] Tabla `processing_log` para tracking de archivos procesados
- [x] Índices creados para queries frecuentes
- [x] Migraciones versionadas

**Modelo `transactions`:**
```
id, statement_id, date, post_date, description, description_normalized,
amount, currency, transaction_type, has_interest, category, subcategory,
merchant_id, classification_source, classification_confidence,
is_recurring, is_installment_payment, installment_plan_id,
raw_data, created_at, updated_at
```

**Modelo `installment_plans` (MSI):**
```
id, statement_id, description, original_amount, pending_balance,
monthly_payment, current_installment, total_installments,
start_date, end_date_calculated, has_interest, interest_rate,
source_bank, status, raw_data, created_at
```

**Estimación:** 6 horas

---

### E1-US03: Parser de PDF BBVA - Resumen
**Como** usuario  
**Quiero** extraer el resumen del estado de cuenta BBVA  
**Para** conocer saldos, fechas de corte y límites de pago

**Criterios de Aceptación:**
- [x] Extrae período (fecha inicio - fecha fin)
- [x] Extrae fecha de corte
- [x] Extrae fecha límite de pago
- [x] Extrae saldo anterior
- [x] Extrae pago para no generar intereses
- [x] Extrae pago mínimo
- [x] Extrae saldo deudor total
- [x] Extrae límite de crédito
- [x] Extrae crédito disponible
- [x] Extrae número de cuenta (últimos 4 dígitos)
- [x] Maneja errores gracefully si falta algún campo

**Estimación:** 4 horas

---

### E1-US04: Parser de PDF BBVA - Transacciones regulares
**Como** usuario  
**Quiero** extraer las transacciones regulares (no a meses) de BBVA  
**Para** ver mis compras y pagos del período

**Criterios de Aceptación:**
- [x] Extrae fecha de operación
- [x] Extrae fecha de cargo
- [x] Extrae descripción del movimiento
- [x] Extrae monto con signo correcto (+ cargo, - abono)
- [x] Identifica pagos (PAGO INTERBANCARIO, etc.)
- [x] Identifica cargos de intereses (* INTERESES EFI *)
- [x] Identifica pagos de MSI (05 DE 12 SPORT CITY...)
- [x] Maneja transacciones en múltiples páginas
- [x] Parsea correctamente montos con formato mexicano

**Estimación:** 6 horas

---

### E1-US05: Parser de PDF BBVA - MSI sin intereses
**Como** usuario  
**Quiero** extraer mis compras a meses sin intereses  
**Para** saber qué compromisos tengo y cuándo terminan

**Criterios de Aceptación:**
- [x] Extrae fecha de operación
- [x] Extrae descripción
- [x] Extrae monto original
- [x] Extrae saldo pendiente
- [x] Extrae pago requerido (mensualidad)
- [x] Extrae número de pago actual (ej: "5 de 12")
- [x] Extrae total de pagos
- [x] Calcula fecha de término
- [x] Tasa de interés = 0%
- [x] Flag has_interest = false

**Estimación:** 4 horas

---

### E1-US06: Parser de PDF BBVA - MSI con intereses
**Como** usuario  
**Quiero** extraer mis compras/disposiciones a meses CON intereses  
**Para** saber cuánto me está costando mi deuda

**Criterios de Aceptación:**
- [x] Extrae todos los campos de MSI sin intereses
- [x] Extrae intereses del período
- [x] Extrae IVA de intereses del período
- [x] Extrae tasa de interés aplicable
- [x] Flag has_interest = true
- [x] Identifica EFECTIVO INMEDIATO como tipo especial

**Estimación:** 3 horas

---

### E1-US07: CLI para procesar estados de cuenta
**Como** usuario  
**Quiero** un comando para procesar PDFs desde una carpeta  
**Para** extraer toda la información automáticamente

**Criterios de Aceptación:**
- [x] Comando: `fin process <carpeta>`
- [x] Detecta archivos PDF nuevos (no procesados antes)
- [x] Detecta banco automáticamente (7 bancos soportados)
- [x] Procesa y guarda en base de datos
- [x] Muestra progreso en consola
- [x] Muestra resumen al finalizar (X archivos, Y transacciones)
- [x] Registra archivos procesados para no reprocesar
- [x] Flag `--force` para reprocesar todo

**Ejemplo de uso:**
```bash
$ fin process ./estados-de-cuenta/
Procesando: BBVA_TDC_Dic2025.pdf
  ✓ Resumen extraído
  ✓ 18 transacciones regulares
  ✓ 5 planes MSI sin intereses
  ✓ 2 planes MSI con intereses

Resumen: 1 archivo procesado, 25 registros creados
```

**Estimación:** 4 horas

---

### E1-US08: Tests unitarios Sprint 1
**Como** desarrollador  
**Quiero** tests para los parsers  
**Para** asegurar que no se rompa con cambios futuros

**Criterios de Aceptación:**
- [x] Test de extracción de resumen BBVA
- [x] Test de extracción de transacciones BBVA
- [x] Test de extracción de MSI BBVA
- [x] Test de detección de banco
- [x] Test de idempotencia (no duplica al reprocesar)
- [x] Fixtures con datos de ejemplo (anonimizados)

**Estimación:** 3 horas

---

## Sprint 2 (Semanas 3-4): Parser HSBC + Consultas Básicas

### Objetivo
Agregar soporte para HSBC y poder consultar datos básicos via CLI.

---

### E1-US09: Parser de PDF HSBC - Completo
**Como** usuario  
**Quiero** extraer información de mis estados de cuenta HSBC  
**Para** tener visión completa de mis finanzas

**Criterios de Aceptación:**
- [x] Extrae resumen (mismos campos que BBVA)
- [x] Extrae transacciones regulares
- [x] Extrae MSI con intereses (Transferencias de saldo)
- [x] Identifica comisiones (PENALIZACION POR PAGO TARDIO)
- [x] Identifica intereses desglosados (SUJETOS/NO SUJETOS A IVA)
- [x] Extrae información de pagos SPEI recibidos

**Notas técnicas:**
- HSBC tiene formato diferente a BBVA
- Los intereses aparecen como líneas separadas
- Las transferencias de saldo son el equivalente a MSI

**Estimación:** 8 horas

---

### E1-US10: Normalización de descripciones
**Como** sistema  
**Quiero** normalizar las descripciones de transacciones  
**Para** facilitar matching y clasificación

**Criterios de Aceptación:**
- [x] Convierte a mayúsculas
- [x] Remueve acentos
- [x] Colapsa espacios múltiples
- [x] Extrae información de tarjeta digital (***3141)
- [x] Extrae número de pago MSI de descripción
- [x] Limpia caracteres especiales

**Ejemplos:**
```
"AMAZON ; Tarjeta Digital ***3141" → "AMAZON"
"05 DE 12 SPORT CITY UNIVERSITY" → "SPORT CITY UNIVERSITY" + installment_info
"OXXO HDA DEL VALLETLC" → "OXXO"
```

**Estimación:** 3 horas

---

### E1-US11: CLI para consultas básicas
**Como** usuario  
**Quiero** consultar mis transacciones desde la línea de comandos  
**Para** verificar que los datos se extrajeron correctamente

**Criterios de Aceptación:**
- [x] `fin transactions --month 2025-12` lista transacciones
- [x] `fin transactions --category comida` filtra por categoría
- [x] `fin summary --month 2025-12` muestra resumen del mes
- [x] `fin msi` lista todos los MSI activos
- [x] `fin msi --ending-soon 3` muestra MSI que terminan en 3 meses
- [x] Output formateado en tabla legible

**Estimación:** 4 horas

---

### E1-US12: Detección de duplicados y reversiones
**Como** sistema  
**Quiero** detectar transacciones duplicadas o reversiones  
**Para** no contar doble ni mostrar datos incorrectos

**Criterios de Aceptación:**
- [x] Detecta mismo monto + misma fecha + mismo comercio
- [x] Detecta pares cargo/abono que se cancelan
- [x] Flag `is_reversal` para transacciones canceladas
- [x] No suma reversiones en totales

**Estimación:** 3 horas

---

## Sprint 3 (Semanas 5-6): Clasificación Inteligente + Cobertura de Bancos

### Objetivo
Clasificar transacciones automáticamente y completar extractores para todos los bancos (Banamex, Banorte, Liverpool).

---

### E1-US13: Parser de PDF Banamex - Joy
**Como** usuario  
**Quiero** extraer información de mis estados de cuenta Banamex Joy  
**Para** soportar este producto

**Criterios de Aceptación:**
- [x] Extrae resumen, transacciones y MSI
- [x] Formato específico Joy identificado

**Estimación:** 3 horas

---

### E1-US14: Parser de PDF Banamex - Clásica
**Como** usuario  
**Quiero** extraer información de mis estados de cuenta Banamex Clásica  
**Para** soportar este producto

**Criterios de Aceptación:**
- [x] Extrae resumen, transacciones y MSI
- [x] Integrado con extractor unificado Banamex

**Estimación:** 3 horas

---

### E1-US15: Parser de PDF Banorte
**Como** usuario  
**Quiero** extraer información de mis estados de cuenta Banorte  
**Para** tener visión completa

**Criterios de Aceptación:**
- [x] Extracción 100% de datos (la más completa)
- [x] Soporte detallado para Balance Transfers (intereses, IVA, tasa)
- [x] Soporte para Convenience Checks

**Estimación:** 3 horas

---

### E1-US16: Parser de PDF Liverpool TDC (OCR)
**Como** usuario  
**Quiero** procesar estados de cuenta de Liverpool Crédito  
**Para** gestionar mi tarjeta departamental

**Criterios de Aceptación:**
- [x] Solución OCR implementada (pytesseract)
- [x] Maneja codificación no estándar del PDF
- [x] Extrae transacciones y MSI

**Estimación:** 4 horas

---

### E1-US17: Parser de PDF Liverpool TDD (OCR)
**Como** usuario  
**Quiero** procesar estados de cuenta de Liverpool Débito  
**Para** gestionar mi cuenta de nómina/débito

**Criterios de Aceptación:**
- [x] Solución OCR implementada
- [x] Extrae depósitos, retiros y saldos

**Estimación:** 2 horas

---

### E2-US01: Motor de reglas de clasificación
**Como** sistema  
**Quiero** clasificar transacciones usando reglas determinísticas  
**Para** categorizar rápido y con alta precisión los casos conocidos

**Criterios de Aceptación:**
- [x] Reglas definidas en archivo YAML
- [x] Matching por regex en descripción normalizada
- [x] Soporte para múltiples patrones por categoría
- [x] Prioridad de reglas (más específica gana)
- [x] Categorías: alimentación, transporte, entretenimiento, etc.
- [x] Subcategorías: supermercado, restaurantes, delivery, etc.
- [x] Reglas especiales para intereses, comisiones, pagos

**Estructura de regla:**
```yaml
rules:
  - pattern: "UBER EATS|DIDI FOOD|RAPPI"
    category: alimentacion
    subcategory: delivery
    priority: 10
    
  - pattern: "UBER|DIDI|CABIFY"
    category: transporte
    subcategory: rideshare
    priority: 5  # menor prioridad que delivery
```

**Estimación:** 5 horas

---

### E2-US02: Catálogo de comercios (merchants)
**Como** sistema  
**Quiero** mantener un catálogo de comercios conocidos  
**Para** clasificar consistentemente y aprender de correcciones

**Criterios de Aceptación:**
- [x] Tabla `merchants` con: name, normalized_name, category, subcategory
- [x] Aliases para variaciones (OXXO, OXXO HDA, OXXO EXPRESS)
- [ ] Flag `is_subscription` para suscripciones
- [ ] Flag `is_recurring` para gastos recurrentes
- [x] Actualización automática al corregir clasificación

**Estimación:** 3 horas

---

### E2-US03: Setup de Ollama + modelo local
**Como** desarrollador  
**Quiero** tener Ollama configurado con un modelo de lenguaje  
**Para** clasificar transacciones que no matchean reglas

**Criterios de Aceptación:**
- [x] Ollama instalado y funcionando
- [x] Modelo descargado (qwen2.5:7b)
- [x] Script de prueba que hace una query simple  
- [x] Documentación de instalación en README
- [x] Configuración de timeout y reintentos

**Guía de Uso Ollama:**
1. **Iniciar Servicio**: 
   - Linux: `sudo systemctl start ollama`
   - Manual: `ollama serve` (en terminal separada)
2. **Verificar Estado**: 
   - `systemctl status ollama`
   - `curl http://localhost:11434/api/version`
3. **Detener Servicio**: `sudo systemctl stop ollama`
4. **Descargar Modelo**: `ollama pull qwen2.5:7b`
5. **Ver Modelos**: `ollama list`

**Nota Técnica**:
- El bot usa timeout de 30s para no bloquear procesamiento.
- El modelo se carga en memoria en la primera petición (puede tardar unos segundos).
- Se recomienda GPU para mayor velocidad.

**Instalación del CLI (`fin`):**
Si el comando `fin` no se encuentra, asegúrate de instalar el paquete en modo editable:
```bash
pip install -e .
```
Esto creará el ejecutable `fin` en tu path.

**Estimación:** 2 horas

---

### E2-US04: Clasificación con LLM (fallback)
**Como** sistema  
**Quiero** usar LLM para clasificar transacciones no reconocidas  
**Para** categorizar casos nuevos o ambiguos

**Criterios de Aceptación:**
- [x] Solo se invoca si reglas no matchean
- [x] Prompt optimizado para clasificación
- [x] Respuesta parseada a categoría/subcategoría
- [x] Confidence score estimado
- [x] Batch de transacciones para eficiencia (max 20)
- [x] Cache de clasificaciones para no repetir
- [x] Timeout de 30 segundos por batch

**Prompt ejemplo:**
```
Clasifica estas transacciones bancarias mexicanas.
Categorías válidas: [lista]

Transacciones:
1. CANTIA SA DE CV - $811.55
2. PAST SAN70PECADO - $105.00

Responde en JSON:
[{"id": 1, "category": "...", "subcategory": "..."}]
```

**Estimación:** 5 horas

---

### E2-US05: CLI para corrección de clasificaciones
**Como** usuario  
**Quiero** corregir clasificaciones incorrectas via chat  
**Para** entrenar al sistema con mis preferencias

**Criterios de Aceptación:**
- [x] Comando: `fin correct`
- [x] Muestra transacciones sin clasificar o baja confianza
- [x] Permite asignar categoría manualmente
- [x] Guarda corrección en merchant catalog
- [x] Aplica a transacciones futuras del mismo comercio

**Flujo:**
```
$ fin correct

Transacciones por revisar (5):

1. CANTIA SA DE CV - $811.55 [sin clasificar]
   Categoría: > comida
   Subcategoría: > restaurantes
   ✓ Guardado. Se aplicará a futuras transacciones de CANTIA.

2. T 211 DJU TOWN SQUARE - $2,014.60 [baja confianza: entretenimiento]
   ¿Es correcto? (s/n): > n
   Categoría: > compras
   ...
```

**Estimación:** 4 horas

---

### E2-US06: Detección de suscripciones
**Como** sistema  
**Quiero** detectar suscripciones automáticamente  
**Para** mostrar compromisos recurrentes al usuario

**Criterios de Aceptación:**
- [x] Detecta mismo comercio + monto similar + periodicidad mensual
- [x] Mínimo 2 ocurrencias para marcar como suscripción
- [x] Lista de suscripciones conocidas (Netflix, Spotify, etc.)
- [x] Flag `is_subscription = true` en transacción
- [x] Comando `fin subscriptions` para listar

**Estimación:** 3 horas

---

## Sprint 4 (Semanas 7-8): Documentos Derivados + Vectorización

### Objetivo
Crear documentos estructurados para el RAG y vectorizarlos.

---

### E3-US01: Generador de documento "Resumen Mensual"
**Como** sistema  
**Quiero** generar un documento de resumen por cada mes  
**Para** que el RAG pueda responder preguntas sobre períodos

**Criterios de Aceptación:**
- [x] Un documento por mes procesado
- [x] Incluye: total ingresos, total gastos, ahorro
- [x] Incluye: desglose por categoría (top 5)
- [x] Incluye: gastos con intereses vs sin intereses
- [x] Incluye: total intereses + comisiones pagados
- [x] Incluye: comparación vs mes anterior (si existe)
- [x] Formato estructurado para chunking

**Template:**
```
# Resumen Financiero - Diciembre 2025

## Totales
- Ingresos: $45,000
- Gastos: $38,500
- Ahorro: $6,500 (14.4%)

## Gastos por Categoría
1. Vivienda: $15,000 (39%)
2. Alimentación: $8,500 (22%)
...

## Costo de Deuda
- Intereses pagados: $1,026
- Comisiones pagadas: $509
- Total costo financiero: $1,535

## Comparación vs Noviembre
- Gastos: +5% ($1,925 más)
- Categoría con mayor aumento: Alimentación (+18%)
```

**Estimación:** 4 horas

---

### E3-US02: Generador de documento "Compromisos Futuros"
**Como** sistema  
**Quiero** generar un documento con todos los MSI activos  
**Para** responder preguntas sobre pagos futuros

**Criterios de Aceptación:**
- [x] Lista todos los MSI activos con fecha de término
- [x] Agrupa por mes de término
- [x] Calcula total mensual comprometido
- [x] Identifica MSI que terminan pronto (próximos 3 meses)
- [x] Incluye suscripciones como compromisos recurrentes
- [x] Se actualiza al procesar nuevos estados de cuenta

**Template:**
```
# Compromisos Financieros - Actualizado Dic 2025

## Resumen
- Total comprometido mensual: $12,489
- MSI activos: 7 planes
- Suscripciones: 5 servicios

## MSI por Fecha de Término

### Terminan en Enero 2026
- MERCADO PAGO: $339/mes (6 de 6) - Termina
- ABONO POR TRASP: $551/mes (6 de 6) - Termina
  → Liberarás $890/mes

### Terminan en Julio 2026
- SPORT CITY: $1,875/mes (5 de 12)
...

## Suscripciones Activas
- AMAZON PRIME: $99/mes
- Google One: $395/mes
- SMARTFIT: $599/mes
- Netflix: $199/mes (estimado)
Total suscripciones: $1,292/mes
```

**Estimación:** 4 horas

---

### E3-US03: Generador de documento "Perfil de Comercio"
**Como** sistema  
**Quiero** generar un perfil por cada comercio frecuente  
**Para** responder preguntas sobre hábitos de gasto

**Criterios de Aceptación:**
- [x] Un documento por comercio con >3 transacciones
- [x] Incluye: categoría asignada, total histórico, frecuencia
- [x] Incluye: ticket promedio, último gasto
- [x] Incluye: variaciones de nombre (aliases)
- [x] Flag si es suscripción

**Template:**
```
# Perfil: OXXO

## Clasificación
- Categoría: Gastos Hormiga
- Subcategoría: Tienda de conveniencia
- Es suscripción: No

## Estadísticas (últimos 6 meses)
- Total gastado: $2,450
- Número de visitas: 18
- Ticket promedio: $136
- Frecuencia: 3 veces/mes

## Últimas transacciones
- 21-nov-2025: $145
- 05-nov-2025: $89
...
```

**Estimación:** 3 horas

---

### E3-US04: Setup de embeddings locales
**Como** desarrollador  
**Quiero** configurar modelo de embeddings local  
**Para** vectorizar documentos sin depender de APIs externas

**Criterios de Aceptación:**
- [x] sentence-transformers instalado
- [x] Modelo descargado (all-MiniLM-L6-v2)
- [x] Función para generar embedding de texto
- [x] Test de similaridad entre documentos
- [x] Benchmark de velocidad (docs/segundo)

**Estimación:** 2 horas

---

### E3-US05: Setup de vector store (ChromaDB)
**Como** desarrollador  
**Quiero** configurar ChromaDB para almacenar embeddings  
**Para** hacer búsqueda semántica eficiente

**Criterios de Aceptación:**
- [x] ChromaDB instalado y configurado (persistente)
- [x] Colección creada para documentos financieros
- [x] Metadata schema definido (month, year, doc_type, etc.)
- [x] Función para insertar documento + embedding
- [x] Función para buscar por similaridad
- [x] Función para buscar con filtros de metadata

**Estimación:** 3 horas

---

### E3-US06: Pipeline de vectorización
**Como** sistema  
**Quiero** un pipeline que genere y vectorice documentos  
**Para** mantener el índice actualizado automáticamente

**Criterios de Aceptación:**
- [x] Se ejecuta después de procesar nuevos PDFs
- [x] Genera documentos derivados (resumen, compromisos, perfiles)
- [x] Aplica chunking apropiado (300-800 tokens)
- [x] Genera embeddings por chunk
- [x] Almacena en ChromaDB con metadata
- [x] Actualiza documentos existentes (no duplica)
- [x] Comando: `fin index --rebuild` para reindexar todo
- [x] Comando: `fin reports --month YYYY-MM` para generar reportes

**Estimación:** 5 horas

---

## Sprint 5 (Semanas 9-10): RAG y Chat

### Objetivo
Implementar el chat que responde preguntas sobre finanzas.

---

### E4-US01: Motor de retrieval híbrido
**Como** sistema  
**Quiero** recuperar documentos relevantes para una pregunta  
**Para** dar contexto al LLM

**Criterios de Aceptación:**
- [x] Búsqueda por similaridad semántica
- [x] Filtros por metadata (mes, tipo de documento)
- [x] Extracción de entidades de la pregunta (fechas, categorías)
- [x] Reranking de resultados
- [x] Top-K configurable (default 5)
- [x] Incluye score de relevancia

**Ejemplos:**
```
Query: "¿Cuánto gasté en comida en noviembre?"
→ Filtro: month=2025-11, doc_type=monthly_summary
→ Busca: "gasto comida alimentación"

Query: "¿Qué pagos terminan pronto?"
→ Filtro: doc_type=commitments
→ Busca: "MSI terminan próximo vencer"
```

**Estimación:** 5 horas

---

### E4-US02: Prompt engineering para RAG financiero
**Como** sistema  
**Quiero** prompts optimizados para consultas financieras  
**Para** obtener respuestas precisas y útiles

**Criterios de Aceptación:**
- [x] System prompt con contexto de finanzas personales
- [x] Instrucciones para citar fuentes (mes, documento)
- [x] Instrucciones para no inventar datos
- [x] Formato de respuesta estructurado
- [x] Manejo de preguntas fuera de scope
- [x] Templates para diferentes tipos de consulta

**System Prompt (borrador):**
```
Eres un asistente de finanzas personales. Tienes acceso a los
estados de cuenta y transacciones del usuario.

REGLAS:
1. Solo responde basándote en los documentos proporcionados
2. Si no tienes información, dilo claramente
3. Cita el mes/fuente de los datos
4. Da recomendaciones accionables cuando sea apropiado
5. Usa formato mexicano para montos ($X,XXX.XX)

CONTEXTO:
{retrieved_documents}

PREGUNTA DEL USUARIO:
{user_question}
```

**Estimación:** 3 horas

---

### E4-US03: CLI de chat interactivo
**Como** usuario  
**Quiero** un chat en la terminal para hacer preguntas  
**Para** consultar mis finanzas en lenguaje natural

**Criterios de Aceptación:**
- [x] Comando: `fin chat`
- [x] Loop interactivo de pregunta/respuesta
- [x] Muestra fuentes usadas para la respuesta
- [x] Historial de conversación en sesión
- [x] Comandos especiales: /exit, /clear, /sources, /examples, /help
- [x] Indicador de "pensando..." mientras procesa
- [x] Timeout de 60 segundos con mensaje amigable

**Ejemplo de sesión:**
```
$ fin chat

💬 Asistente Financiero (escribe /exit para salir)

> ¿Cuánto gasté en comida el mes pasado?

📊 En diciembre 2025 gastaste $8,543.35 en alimentación:
- Supermercado (SUPERCENTER SANTIN): $2,154.30
- Restaurantes: $2,676.75
- Delivery y otros: $3,712.30

Esto representa el 22% de tus gastos del mes.

[Fuente: Resumen Diciembre 2025]

> ¿Qué pagos a meses terminan pronto?

📅 Tienes 2 MSI que terminan en los próximos 3 meses:

Enero 2026:
- MERCADO PAGO: última mensualidad $339
- ABONO POR TRASP: última mensualidad $551

Esto liberará $890/mes a partir de febrero.

[Fuente: Compromisos Financieros]

> /exit
👋 ¡Hasta pronto!
```

**Estimación:** 5 horas

---

### E4-US04: Respuestas con cálculos y proyecciones
**Como** usuario  
**Quiero** que el chat pueda hacer cálculos simples  
**Para** responder preguntas de planeación financiera

**Criterios de Aceptación:**
- [x] Calcula totales por categoría/período
- [x] Calcula promedios históricos
- [x] Proyecta ahorro futuro (si reduzco X, en Y meses tengo Z)
- [x] Calcula fecha de liberación de compromisos
- [x] Calcula costo total de deuda (intereses acumulados)

**Ejemplos:**
```
> Si reduzco gastos hormiga a la mitad, ¿cuánto ahorro en 6 meses?

Actualmente gastas ~$1,200/mes en gastos hormiga.
Si reduces a $600/mes, en 6 meses ahorrarías $3,600 adicionales.

> ¿Cuánto me ha costado el Efectivo Inmediato de BBVA?

El Efectivo Inmediato de $35,600 a 36 meses al 31% te ha costado:
- Intereses pagados hasta ahora: $1,378.30
- Intereses proyectados restantes: ~$4,200
- Costo total estimado: ~$5,578
```

**Estimación:** 4 horas

---

### E4-US05: Guardrails y manejo de errores
**Como** sistema  
**Quiero** manejar casos edge y prevenir respuestas incorrectas  
**Para** mantener la confianza del usuario

**Criterios de Aceptación:**
- [x] Detecta preguntas fuera de scope (inversiones, crypto, etc.)
- [x] Responde "no tengo esa información" cuando corresponde
- [x] No inventa datos si no hay documentos relevantes
- [x] Maneja errores de Ollama gracefully
- [x] Logging de preguntas sin respuesta (para mejorar)
- [x] Disclaimer: "Esta información es orientativa..."

**Estimación:** 3 horas

---

## Sprint 6 (Semanas 11-12): Reportes + Estabilización

### Objetivo
Generar reportes automáticos y pulir el sistema para uso real.

---

### E5-US01: Generador de reporte mensual en Markdown
**Como** usuario  
**Quiero** un reporte mensual automático  
**Para** revisar mis finanzas sin hacer preguntas

**Criterios de Aceptación:**
- [ ] Se genera automáticamente al procesar nuevo mes
- [ ] Formato Markdown con secciones claras
- [ ] Incluye: resumen ejecutivo, gastos por categoría, tendencias
- [ ] Incluye: alertas (gastos hormiga altos, comisiones, etc.)
- [ ] Incluye: compromisos próximos a vencer
- [ ] Incluye: recomendaciones accionables (3 max)
- [ ] Guardado en carpeta `reports/`
- [ ] Comando: `fin report --month 2025-12`

**Estimación:** 5 horas

---

### E5-US02: Alertas y detección de anomalías
**Como** usuario  
**Quiero** alertas sobre patrones preocupantes  
**Para** tomar acción antes de que sea problema

**Criterios de Aceptación:**
- [ ] Alerta: gastos hormiga > $500/semana
- [ ] Alerta: categoría > 30% del total
- [ ] Alerta: gasto inusual (> 2x desviación estándar)
- [ ] Alerta: comisiones o penalizaciones cobradas
- [ ] Alerta: pago mínimo insuficiente
- [ ] Las alertas se incluyen en reporte mensual
- [ ] Comando: `fin alerts` para ver alertas activas

**Estimación:** 4 horas

---

### E5-US03: Export de datos
**Como** usuario  
**Quiero** exportar mis datos  
**Para** análisis externo o backup

**Criterios de Aceptación:**
- [ ] `fin export transactions --format csv`
- [ ] `fin export transactions --format json`
- [ ] `fin export msi --format csv`
- [ ] Filtros por fecha, categoría, banco
- [ ] Incluye todos los campos relevantes

**Estimación:** 2 horas

---

### E6-US01: Documentación de usuario
**Como** usuario  
**Quiero** documentación clara  
**Para** saber cómo usar el sistema

**Criterios de Aceptación:**
- [ ] README completo con instalación paso a paso
- [ ] Guía de uso con ejemplos de comandos
- [ ] FAQ con problemas comunes
- [ ] Lista de categorías y subcategorías
- [ ] Ejemplos de preguntas para el chat

**Estimación:** 3 horas

---

### E6-US02: Testing end-to-end
**Como** desarrollador  
**Quiero** tests de integración  
**Para** asegurar que todo funciona junto

**Criterios de Aceptación:**
- [ ] Test: procesar PDF → clasificar → generar docs → indexar
- [ ] Test: query al chat con respuesta correcta
- [ ] Test: generación de reporte mensual
- [ ] Fixtures con estados de cuenta de ejemplo
- [ ] CI básico (pytest en cada commit)

**Estimación:** 4 horas

---

### E6-US03: Performance y optimización
**Como** usuario  
**Quiero** que el sistema sea razonablemente rápido  
**Para** usarlo sin frustración

**Criterios de Aceptación:**
- [ ] Procesar 1 PDF: < 10 segundos
- [ ] Query simple al chat: < 30 segundos
- [ ] Query compleja al chat: < 60 segundos
- [ ] Generación de reporte: < 20 segundos
- [ ] Identificar y documentar cuellos de botella

**Estimación:** 3 horas

---

### E6-US04: Bugfixes y polish
**Como** desarrollador  
**Quiero** tiempo para arreglar bugs encontrados  
**Para** entregar un MVP estable

**Criterios de Aceptación:**
- [ ] Buffer de tiempo para issues emergentes
- [ ] Mejoras de UX basadas en uso real
- [ ] Limpieza de código y refactoring menor

**Estimación:** 6 horas (buffer)

---

## Resumen de Estimaciones

| Sprint | Épica | Horas Estimadas |
|--------|-------|-----------------|
| 1 | E1: Ingesta (BBVA) | 34 hrs |
| 2 | E1: Ingesta (HSBC + consultas) | 18 hrs |
| 3 | E2: Clasificación | 22 hrs |
| 4 | E3: Docs + Vectorización | 21 hrs |
| 5 | E4: RAG + Chat | 20 hrs |
| 6 | E5-E6: Reportes + Estabilización | 27 hrs |

**Total: ~142 horas** (~12 semanas × 10-12 hrs/semana)

---

## Definition of Done (Global)

Una historia está "Done" cuando:
- [ ] Código implementado y funcionando
- [ ] Tests unitarios pasando (si aplica)
- [ ] Sin errores en consola
- [ ] Documentación actualizada (si cambia interfaz)
- [ ] Code review (auto-review en este caso)
- [ ] Merge a main

---

## Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Parser falla con formato diferente de PDF | Alta | Alto | Tener PDFs de múltiples meses para testing |
| LLM local muy lento | Media | Medio | Optimizar prompts, usar modelo más pequeño |
| ChromaDB consume mucha RAM | Baja | Medio | Monitorear, considerar SQLite-VSS como alternativa |
| Clasificación muy imprecisa | Media | Alto | Priorizar corrección manual fácil, iterar en reglas |
| Scope creep | Alta | Alto | Mantener backlog priorizado, decir "post-MVP" |