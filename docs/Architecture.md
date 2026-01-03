# Arquitectura Técnica - Sistema de Inteligencia Financiera Personal

## 1. Visión General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE PRESENTACIÓN                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  CLI Chat   │  │ CLI Process │  │ CLI Query   │  │ CLI Report  │        │
│  │  (fin chat) │  │(fin process)│  │ (fin msi)   │  │(fin report) │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE APLICACIÓN                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   RAG Engine    │  │  Classification │  │    Reporting    │              │
│  │   - Retrieval   │  │  - Rules        │  │    - Monthly    │              │
│  │   - Generation  │  │  - LLM Fallback │  │    - Alerts     │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│  ┌────────┴────────────────────┴────────────────────┴────────┐              │
│  │                    Document Generator                      │              │
│  │  - Monthly Summary  - Commitments  - Merchant Profiles    │              │
│  └────────────────────────────┬───────────────────────────────┘              │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE DATOS                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │     SQLite      │  │    ChromaDB     │  │   File System   │              │
│  │  - Transactions │  │  - Embeddings   │  │  - PDFs raw     │              │
│  │  - Statements   │  │  - Doc chunks   │  │  - Reports      │              │
│  │  - MSI Plans    │  │  - Metadata     │  │  - Config       │              │
│  │  - Merchants    │  │                 │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE EXTRACCIÓN                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ BBVA Parser │  │ HSBC Parser │  │ XML Parser  │  │  (Future)   │        │
│  │             │  │             │  │   (CFDI)    │  │  Banorte    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICIOS EXTERNOS (Local)                         │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐          │
│  │         Ollama              │  │    Sentence Transformers    │          │
│  │  - DeepSeek / Llama 3       │  │    - all-MiniLM-L6-v2       │          │
│  │  - Clasificación            │  │    - Embeddings             │          │
│  │  - Generación RAG           │  │                             │          │
│  └─────────────────────────────┘  └─────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Estructura de Carpetas

```
finanzas-personales-ia/
│
├── fin/                          # Paquete principal
│   ├── __init__.py
│   ├── cli.py                    # Entry point CLI (Click)
│   │
│   ├── extractors/               # Parsers de PDFs y XMLs
│   │   ├── __init__.py
│   │   ├── base.py               # Clase base para parsers
│   │   ├── bbva.py               # Parser BBVA
│   │   ├── hsbc.py               # Parser HSBC
│   │   ├── cfdi.py               # Parser XML CFDI
│   │   └── detector.py           # Auto-detección de banco
│   │
│   ├── models/                   # Modelos de datos
│   │   ├── __init__.py
│   │   ├── database.py           # Setup SQLite + SQLAlchemy
│   │   ├── transaction.py        # Modelo Transaction
│   │   ├── statement.py          # Modelo Statement
│   │   ├── installment.py        # Modelo InstallmentPlan (MSI)
│   │   └── merchant.py           # Modelo Merchant
│   │
│   ├── classification/           # Motor de clasificación
│   │   ├── __init__.py
│   │   ├── rules.py              # Motor de reglas
│   │   ├── llm.py                # Clasificación con Ollama
│   │   ├── merchants.py          # Catálogo de comercios
│   │   └── subscriptions.py      # Detección de suscripciones
│   │
│   ├── documents/                # Generación de documentos derivados
│   │   ├── __init__.py
│   │   ├── monthly_summary.py    # Resumen mensual
│   │   ├── commitments.py        # Compromisos futuros
│   │   ├── merchant_profile.py   # Perfiles de comercio
│   │   └── templates/            # Templates Jinja2
│   │       ├── monthly.md.j2
│   │       ├── commitments.md.j2
│   │       └── report.md.j2
│   │
│   ├── vectorstore/              # RAG y embeddings
│   │   ├── __init__.py
│   │   ├── embeddings.py         # Generación de embeddings
│   │   ├── store.py              # ChromaDB wrapper
│   │   ├── chunking.py           # Estrategias de chunking
│   │   └── retrieval.py          # Motor de retrieval híbrido
│   │
│   ├── rag/                      # Chat y generación
│   │   ├── __init__.py
│   │   ├── engine.py             # RAG engine principal
│   │   ├── prompts.py            # Templates de prompts
│   │   ├── chat.py               # Lógica de chat interactivo
│   │   └── calculations.py       # Cálculos financieros
│   │
│   ├── reports/                  # Generación de reportes
│   │   ├── __init__.py
│   │   ├── generator.py          # Generador de reportes
│   │   └── alerts.py             # Sistema de alertas
│   │
│   └── utils/                    # Utilidades
│       ├── __init__.py
│       ├── dates.py              # Parsing de fechas
│       ├── money.py              # Parsing de montos
│       └── text.py               # Normalización de texto
│
├── config/                       # Configuración
│   ├── categories.yaml           # Definición de categorías
│   ├── rules.yaml                # Reglas de clasificación
│   ├── merchants.yaml            # Comercios conocidos
│   └── settings.yaml             # Configuración general
│
├── data/                         # Datos (gitignored excepto examples)
│   ├── statements/               # PDFs de estados de cuenta
│   │   ├── 2025/
│   │   └── 2026/
│   ├── database/                 # SQLite files
│   │   └── finanzas.db
│   ├── vectorstore/              # ChromaDB persistence
│   └── examples/                 # Ejemplos para testing
│
├── reports/                      # Reportes generados
│   └── 2025-12-report.md
│
├── tests/                        # Tests
│   ├── __init__.py
│   ├── test_extractors/
│   ├── test_classification/
│   ├── test_rag/
│   └── fixtures/
│
├── docs/                         # Documentación
│   ├── BACKLOG.md
│   ├── ARCHITECTURE.md
│   └── USER_GUIDE.md
│
├── scripts/                      # Scripts de utilidad
│   └── setup_ollama.sh
│
├── requirements.txt
├── setup.py
├── pyproject.toml
└── README.md
```

---

## 3. Flujos de Datos

### 3.1 Flujo de Ingesta y Procesamiento

```
                                    ┌─────────────────┐
                                    │   fin process   │
                                    │   ./statements  │
                                    └────────┬────────┘
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │   Detectar archivos      │
                              │   nuevos (no procesados) │
                              └─────────────┬────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │   Por cada PDF:          │
                              │   1. Detectar banco      │
                              └─────────────┬────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ▼                       ▼                       ▼
            ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
            │  BBVA Parser  │       │  HSBC Parser  │       │ (Otro banco)  │
            └───────┬───────┘       └───────┬───────┘       └───────────────┘
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Extraer:            │
                    │   - Resumen           │
                    │   - Transacciones     │
                    │   - MSI sin intereses │
                    │   - MSI con intereses │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Normalizar          │
                    │   descripciones       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Clasificar          │
                    │   (Rules → LLM)       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Guardar en SQLite   │
                    │   - statements        │
                    │   - transactions      │
                    │   - installment_plans │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Generar documentos  │
                    │   derivados           │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Vectorizar y        │
                    │   almacenar en        │
                    │   ChromaDB            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Generar reporte     │
                    │   mensual (si nuevo   │
                    │   mes completo)       │
                    └───────────────────────┘
```

### 3.2 Flujo de Clasificación

```
                    ┌───────────────────────┐
                    │   Transacción nueva   │
                    │   (sin clasificar)    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Buscar en catálogo  │
                    │   de merchants        │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
               [Encontrado]            [No encontrado]
                    │                       │
                    ▼                       ▼
            ┌───────────────┐       ┌───────────────────────┐
            │ Usar categoría│       │   Aplicar reglas      │
            │ del merchant  │       │   (regex matching)    │
            └───────┬───────┘       └───────────┬───────────┘
                    │                           │
                    │               ┌───────────┴───────────┐
                    │               │                       │
                    │          [Match]                 [No match]
                    │               │                       │
                    │               ▼                       ▼
                    │       ┌───────────────┐       ┌───────────────────────┐
                    │       │ Usar categoría│       │   Clasificar con LLM  │
                    │       │ de la regla   │       │   (batch de 20)       │
                    │       └───────┬───────┘       └───────────┬───────────┘
                    │               │                           │
                    └───────────────┴───────────────────────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │   Guardar clasificación│
                                │   - category           │
                                │   - subcategory        │
                                │   - source (rules/llm) │
                                │   - confidence         │
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │   Si es nuevo merchant│
                                │   → agregar a catálogo│
                                └───────────────────────┘
```

### 3.3 Flujo de RAG (Chat)

```
                    ┌───────────────────────┐
                    │   Usuario hace        │
                    │   pregunta            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Extraer entidades   │
                    │   - Fechas/meses      │
                    │   - Categorías        │
                    │   - Comercios         │
                    │   - Montos            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Construir filtros   │
                    │   de metadata         │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Generar embedding   │
                    │   de la pregunta      │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Buscar en ChromaDB  │
                    │   - Similaridad       │
                    │   - Filtros metadata  │
                    │   - Top K = 5         │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Reranking de        │
                    │   resultados          │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Construir prompt    │
                    │   - System prompt     │
                    │   - Documentos        │
                    │   - Pregunta          │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Enviar a Ollama     │
                    │   (LLM local)         │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Procesar respuesta  │
                    │   - Parsear cálculos  │
                    │   - Agregar fuentes   │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Mostrar al usuario  │
                    │   con referencias     │
                    └───────────────────────┘
```

---

## 4. Modelo de Datos (SQLite)

### 4.1 Diagrama Entidad-Relación

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌─────────────────┐         ┌─────────────────┐                        │
│  │   statements    │         │  transactions   │                        │
│  ├─────────────────┤         ├─────────────────┤                        │
│  │ id (PK)         │────┐    │ id (PK)         │                        │
│  │ bank            │    │    │ statement_id(FK)│◄───────────────────┐   │
│  │ source_type     │    │    │ date            │                    │   │
│  │ account_number  │    │    │ post_date       │                    │   │
│  │ period_start    │    │    │ description     │    ┌────────────────┐  │
│  │ period_end      │    │    │ amount          │    │   merchants    │  │
│  │ statement_date  │    │    │ category        │    ├────────────────┤  │
│  │ due_date        │    │    │ subcategory     │    │ id (PK)        │  │
│  │ previous_balance│    │    │ merchant_id(FK) │───►│ name           │  │
│  │ current_balance │    │    │ is_recurring    │    │ normalized_name│  │
│  │ minimum_payment │    └───►│ ...             │    │ category       │  │
│  │ credit_limit    │         └─────────────────┘    │ subcategory    │  │
│  │ source_file     │                                │ is_subscription│  │
│  │ ...             │         ┌─────────────────┐    └────────────────┘  │
│  └─────────────────┘         │installment_plans│                        │
│                              ├─────────────────┤                        │
│                              │ id (PK)         │                        │
│                              │ statement_id(FK)│◄────────────────────┐  │
│                              │ description     │                     │  │
│                              │ original_amount │                     │  │
│                              │ pending_balance │                     │  │
│                              │ monthly_payment │                     │  │
│                              │ current_install │                     │  │
│                              │ total_installs  │                     │  │
│                              │ start_date      │                     │  │
│                              │ end_date        │                     │  │
│                              │ has_interest    │                     │  │
│                              │ interest_rate   │                     │  │
│                              │ source_bank     │                     │  │
│                              │ ...             │                     │  │
│                              └─────────────────┘                     │  │
│                                                                      │  │
│  ┌─────────────────┐         ┌─────────────────┐                     │  │
│  │ processing_log  │         │  derived_docs   │                     │  │
│  ├─────────────────┤         ├─────────────────┤                     │  │
│  │ id (PK)         │         │ id (PK)         │                     │  │
│  │ file_path       │         │ doc_type        │                     │  │
│  │ file_hash       │         │ year            │                     │  │
│  │ bank_detected   │         │ month           │                     │  │
│  │ processed_at    │         │ content         │                     │  │
│  │ status          │         │ metadata (JSON) │                     │  │
│  │ error_message   │         │ created_at      │                     │  │
│  │ records_created │         │ updated_at      │                     │  │
│  └─────────────────┘         └─────────────────┘                     │  │
│                                                                      │  │
└──────────────────────────────────────────────────────────────────────┘  │
```

### 4.2 Esquema SQL Detallado

```sql
-- Statements (Estados de cuenta)
CREATE TABLE statements (
    id TEXT PRIMARY KEY,
    bank TEXT NOT NULL,                    -- 'bbva', 'hsbc', etc.
    source_type TEXT NOT NULL,             -- 'credit_card', 'debit', etc.
    account_number TEXT,                   -- últimos 4 dígitos
    
    period_start DATE,
    period_end DATE,
    statement_date DATE,
    due_date DATE,
    
    previous_balance DECIMAL(12,2),
    current_balance DECIMAL(12,2),
    minimum_payment DECIMAL(12,2),
    payment_no_interest DECIMAL(12,2),
    credit_limit DECIMAL(12,2),
    available_credit DECIMAL(12,2),
    
    total_regular_charges DECIMAL(12,2),
    total_msi_charges DECIMAL(12,2),
    total_interest DECIMAL(12,2),
    total_fees DECIMAL(12,2),
    total_payments DECIMAL(12,2),
    
    source_file TEXT NOT NULL,
    raw_data JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions (Transacciones)
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    statement_id TEXT REFERENCES statements(id),
    
    date DATE NOT NULL,
    post_date DATE,
    description TEXT NOT NULL,
    description_normalized TEXT,
    
    amount DECIMAL(12,2) NOT NULL,
    currency TEXT DEFAULT 'MXN',
    
    transaction_type TEXT NOT NULL,        -- 'expense', 'income', 'payment', 'interest', 'fee'
    has_interest BOOLEAN DEFAULT FALSE,
    
    category TEXT,
    subcategory TEXT,
    merchant_id TEXT REFERENCES merchants(id),
    
    classification_source TEXT,            -- 'rules', 'llm', 'manual'
    classification_confidence DECIMAL(3,2),
    
    is_recurring BOOLEAN DEFAULT FALSE,
    is_subscription BOOLEAN DEFAULT FALSE,
    is_reversal BOOLEAN DEFAULT FALSE,
    is_installment_payment BOOLEAN DEFAULT FALSE,
    installment_plan_id TEXT REFERENCES installment_plans(id),
    
    tags JSON,                             -- array de tags
    raw_data JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Installment Plans (MSI - Meses Sin Intereses)
CREATE TABLE installment_plans (
    id TEXT PRIMARY KEY,
    statement_id TEXT REFERENCES statements(id),
    
    description TEXT NOT NULL,
    original_amount DECIMAL(12,2) NOT NULL,
    pending_balance DECIMAL(12,2),
    monthly_payment DECIMAL(12,2),
    
    current_installment INTEGER,           -- ej: 5 (de 12)
    total_installments INTEGER,            -- ej: 12
    
    start_date DATE,
    end_date_calculated DATE,              -- calculado: start + total_installments meses
    
    has_interest BOOLEAN DEFAULT FALSE,
    interest_rate DECIMAL(5,2),            -- ej: 31.00 (%)
    interest_this_period DECIMAL(12,2),
    
    source_bank TEXT NOT NULL,
    plan_type TEXT,                        -- 'msi', 'efectivo_inmediato', 'balance_transfer'
    status TEXT DEFAULT 'active',          -- 'active', 'completed', 'cancelled'
    
    raw_data JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Merchants (Catálogo de comercios)
CREATE TABLE merchants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    aliases JSON,                          -- array de variaciones del nombre
    
    category TEXT,
    subcategory TEXT,
    
    is_subscription BOOLEAN DEFAULT FALSE,
    subscription_amount DECIMAL(12,2),
    subscription_frequency TEXT,           -- 'monthly', 'yearly', etc.
    
    total_transactions INTEGER DEFAULT 0,
    total_amount DECIMAL(12,2) DEFAULT 0,
    average_amount DECIMAL(12,2),
    last_transaction_date DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing Log (Registro de archivos procesados)
CREATE TABLE processing_log (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,               -- SHA256 del archivo
    file_size INTEGER,
    
    bank_detected TEXT,
    processing_status TEXT,                -- 'success', 'error', 'partial'
    error_message TEXT,
    
    statements_created INTEGER DEFAULT 0,
    transactions_created INTEGER DEFAULT 0,
    installments_created INTEGER DEFAULT 0,
    
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Derived Documents (Documentos derivados para RAG)
CREATE TABLE derived_docs (
    id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL,                -- 'monthly_summary', 'commitments', 'merchant_profile'
    
    year INTEGER,
    month INTEGER,
    merchant_id TEXT REFERENCES merchants(id),
    
    title TEXT,
    content TEXT NOT NULL,                 -- Contenido completo del documento
    
    metadata JSON,                         -- Metadata adicional para filtros
    
    is_indexed BOOLEAN DEFAULT FALSE,      -- Si ya está en ChromaDB
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classification Rules (Reglas de clasificación - cache)
CREATE TABLE classification_cache (
    id TEXT PRIMARY KEY,
    description_normalized TEXT NOT NULL UNIQUE,
    
    category TEXT,
    subcategory TEXT,
    source TEXT,                           -- 'rules', 'llm', 'manual'
    confidence DECIMAL(3,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_statement ON transactions(statement_id);
CREATE INDEX idx_transactions_merchant ON transactions(merchant_id);
CREATE INDEX idx_installments_end_date ON installment_plans(end_date_calculated);
CREATE INDEX idx_installments_status ON installment_plans(status);
CREATE INDEX idx_merchants_normalized ON merchants(normalized_name);
CREATE INDEX idx_processing_file_hash ON processing_log(file_hash);
CREATE INDEX idx_derived_docs_type_period ON derived_docs(doc_type, year, month);
```

---

## 5. Configuración de Componentes

### 5.1 Ollama (LLM Local)

```yaml
# config/settings.yaml

ollama:
  base_url: "http://localhost:11434"
  model: "deepseek-r1:7b"              # o "llama3:8b"
  timeout: 60                          # segundos
  
  # Parámetros de generación
  generation:
    temperature: 0.3                   # Bajo para consistencia
    max_tokens: 1000
    top_p: 0.9
  
  # Parámetros de clasificación
  classification:
    temperature: 0.1                   # Muy bajo para determinismo
    max_tokens: 500
    batch_size: 20                     # Transacciones por llamada
```

### 5.2 Embeddings

```yaml
# config/settings.yaml

embeddings:
  model: "all-MiniLM-L6-v2"           # Modelo pequeño y rápido
  # alternativa: "paraphrase-multilingual-MiniLM-L12-v2" para español
  
  dimension: 384                       # Dimensión del vector
  batch_size: 32                       # Documentos por batch
```

### 5.3 ChromaDB

```yaml
# config/settings.yaml

vectorstore:
  type: "chromadb"
  persist_directory: "./data/vectorstore"
  collection_name: "finanzas_docs"
  
  # Configuración de búsqueda
  search:
    n_results: 5                       # Top K
    include_metadata: true
    include_documents: true
```

### 5.4 Categorías

```yaml
# config/categories.yaml

categories:
  alimentacion:
    subcategories:
      - supermercado
      - restaurantes
      - delivery
      - cafeterias
    is_essential: true
    
  transporte:
    subcategories:
      - gasolina
      - rideshare
      - transporte_publico
      - estacionamiento
    is_essential: true
    
  vivienda:
    subcategories:
      - hipoteca
      - renta
      - servicios
      - mantenimiento
    is_essential: true
    is_fixed: true
    
  entretenimiento:
    subcategories:
      - streaming
      - gaming
      - eventos
      - viajes
    is_essential: false
    
  tecnologia:
    subcategories:
      - hardware
      - software
      - suscripciones
    is_essential: false
    
  gastos_hormiga:
    subcategories:
      - tienda_conveniencia
      - cafe_snacks
      - antojos
    is_essential: false
    alert_threshold: 500              # Alertar si > $500/semana
    
  costo_deuda:
    subcategories:
      - intereses
      - comisiones
      - anualidades
      - penalizaciones
    is_essential: false
    is_cost: true                     # Costo financiero
    
  # ... más categorías
```

---

## 6. Interfaces de API Interna

### 6.1 Extractor Interface

```python
from abc import ABC, abstractmethod
from typing import Optional
from models import Statement

class BaseExtractor(ABC):
    """Interface para extractores de estados de cuenta."""
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Determina si este extractor puede parsear el archivo."""
        pass
    
    @abstractmethod
    def parse(self, file_path: str) -> Optional[Statement]:
        """Parsea el archivo y retorna un Statement."""
        pass
    
    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Nombre del banco que maneja este extractor."""
        pass
```

### 6.2 Classifier Interface

```python
from abc import ABC, abstractmethod
from typing import List, Tuple
from models import Transaction

class BaseClassifier(ABC):
    """Interface para clasificadores."""
    
    @abstractmethod
    def classify(self, transaction: Transaction) -> Tuple[str, str, float]:
        """
        Clasifica una transacción.
        
        Returns:
            Tuple de (category, subcategory, confidence)
        """
        pass
    
    @abstractmethod
    def classify_batch(self, transactions: List[Transaction]) -> List[Tuple[str, str, float]]:
        """Clasifica múltiples transacciones en batch."""
        pass
```

### 6.3 Document Generator Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseDocumentGenerator(ABC):
    """Interface para generadores de documentos derivados."""
    
    @abstractmethod
    def generate(self, year: int, month: int) -> str:
        """
        Genera el documento para un período.
        
        Returns:
            Contenido del documento en formato string.
        """
        pass
    
    @property
    @abstractmethod
    def doc_type(self) -> str:
        """Tipo de documento (monthly_summary, commitments, etc.)."""
        pass
```

---

## 7. Consideraciones de Seguridad y Privacidad

### 7.1 Datos Sensibles

```
Datos que se almacenan localmente:
├── Transacciones completas (montos, descripciones)
├── Números de cuenta (últimos 4 dígitos solamente)
├── Patrones de gasto
└── Documentos derivados con análisis

Datos que NUNCA salen del sistema local:
├── PDFs originales
├── Datos completos de cuenta
├── Información personal (RFC, dirección)
└── Todo el contenido de la base de datos

Datos enviados a Ollama (local):
├── Descripciones normalizadas (sin datos personales)
├── Montos (solo para contexto de clasificación)
└── Preguntas del usuario
```

### 7.2 Mitigaciones

```python
# Siempre anonimizar antes de enviar a LLM
def sanitize_for_llm(description: str) -> str:
    """Remueve información sensible antes de enviar a LLM."""
    # Remover números de tarjeta
    sanitized = re.sub(r'\*{3,}\d{4}', '', description)
    # Remover posibles números de cuenta
    sanitized = re.sub(r'\b\d{10,}\b', '[CUENTA]', sanitized)
    return sanitized.strip()
```

---

## 8. Plan de Extensibilidad

### 8.1 Agregar Nuevo Banco

```python
# 1. Crear nuevo extractor en fin/extractors/banorte.py
class BanorteExtractor(BaseExtractor):
    bank_name = "banorte"
    
    def can_parse(self, file_path: str) -> bool:
        # Lógica de detección
        pass
    
    def parse(self, file_path: str) -> Statement:
        # Lógica de parsing
        pass

# 2. Registrar en fin/extractors/__init__.py
EXTRACTORS = [
    BBVAExtractor(),
    HSBCExtractor(),
    BanorteExtractor(),  # Nuevo
]

# 3. Agregar tests en tests/test_extractors/test_banorte.py
```

### 8.2 Agregar Nueva Categoría

```yaml
# config/categories.yaml
categories:
  nueva_categoria:
    subcategories:
      - sub1
      - sub2
    is_essential: false
```

```yaml
# config/rules.yaml
rules:
  - pattern: "PATRON_NUEVO"
    category: "nueva_categoria"
    subcategory: "sub1"
```

### 8.3 Migrar a Cloud (Futuro)

```
Componentes diseñados para migración:
│
├── SQLite → PostgreSQL (RDS)
│   └── Solo cambiar connection string en SQLAlchemy
│
├── ChromaDB → Pinecone/Qdrant
│   └── Implementar nueva clase que herede de BaseVectorStore
│
├── Ollama → Claude API / OpenAI
│   └── Implementar nueva clase que herede de BaseLLM
│   └── Agregar manejo de API keys
│
├── Local files → S3
│   └── Implementar StorageBackend abstracto
│
└── CLI → FastAPI + React
    └── Exponer servicios existentes como REST API
```

---

## 9. Requisitos de Hardware

### Mínimos (tu setup actual)

| Componente | Requisito |
|------------|-----------|
| RAM | 16 GB |
| CPU | 4+ cores |
| Disco | 10 GB libres |
| OS | Linux Mint |

### Uso Estimado de Recursos

| Operación | RAM | CPU | Tiempo |
|-----------|-----|-----|--------|
| Procesar 1 PDF | ~500 MB | Bajo | 5-10 seg |
| Clasificar con LLM (batch 20) | ~8 GB | Alto | 20-40 seg |
| Query RAG | ~8 GB | Alto | 15-30 seg |
| Indexar documentos | ~2 GB | Medio | 5-10 seg |

---

## 10. Dependencias Principales

```
# requirements.txt - Dependencias core

# PDF Processing
pdfplumber>=0.10.0

# Data
pandas>=2.1.0
sqlalchemy>=2.0.0

# CLI
click>=8.1.0
rich>=13.0.0              # Output bonito en terminal

# LLM Local
ollama>=0.1.0             # Cliente Python para Ollama

# Embeddings & Vector Store
sentence-transformers>=2.2.0
chromadb>=0.4.0

# Templates
jinja2>=3.1.0

# Utilities
pyyaml>=6.0
python-dateutil>=2.8.0
unidecode>=1.3.0

# Development
pytest>=7.4.0
```