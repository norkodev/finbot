# Finbot - Guía de Uso Completa

## Introducción

Finbot es un sistema completo de inteligencia financiera personal que te permite:
- Procesar estados de cuenta de 7 bancos mexicanos
- Clasificar transacciones automáticamente con AI
- Generar reportes financieros detallados
- Hacer preguntas en lenguaje natural sobre tus finanzas
- Exportar datos para análisis externo

---

## Workflow Completo

### 1. Procesamiento Inicial

**1.1. Organizar PDFs**
```bash
# Estructura recomendada
data/inbox/
├── 2025/
│   ├── 12/
│   │   ├── bbva_2025-12.pdf
│   │   ├── hsbc_2025-12.pdf
│   │   └── banamex_2025-12.pdf
```

**1.2. Procesar Estados de Cuenta**
```bash
# Procesar un solo PDF
fin process data/inbox/2025/12/bbva_2025-12.pdf

# Procesar todos los PDFs de un mes
fin process data/inbox/2025/12/

# Ver progreso
# [████████████████████] 100% Extracting...
# ✓ Extracted 45 transactions
# ✓ Classified 45 transactions
# ✓ Statement saved
```

**1.3. Verificar Extracción**
```bash
# Ver transacciones del mes
fin transactions --month 2025-12

# Ver resumen
fin summary --month 2025-12
```

---

### 2. Clasificación y Corrección

**2.1. Revisar Clasificaciones**
```bash
# Ver transacciones sin categoría
fin transactions --month 2025-12 | grep "Sin categoría"
```

**2.2. Corregir Clasificación Interactiva**
```bash
fin correct --limit 10

# UI interactiva:
# Transaction: OXXO HDA DEL VALLE - $145.00
# Current: Sin categoría
# 
# Select category:
#   1. gastos_hormiga
#   2. alimentacion
#   3. transporte
# > 1
# ✓ Updated
```

**2.3. Verificar Suscripciones Detectadas**
```bash
fin subscriptions --months-back 3

# Output:
# Active Subscriptions
# ⭐ NETFLIX.COM: $199.00/mes
# ⭐ SPOTIFY: $129.00/mes
```

---

### 3. Análisis Financiero

**3.1. Ver MSI Activos**
```bash
# Todos los MSI
fin msi

# MSI que terminan pronto
fin msi --ending-soon 3

# Output:
# Active Installment Plans
# 
# MERCADO PAGO
# - Monthly: $339.00
# - Remaining: 1 installments
# - Ends: 2026-01
```

**3.2. Generar Reportes**
```bash
# Reporte mensual mejorado
fin report --month 2025-12

# Genera: data/reports/summaries/2025-12-enhanced.md
# Incluye:
# - Resumen ejecutivo
# - Alertas inline
# - Recomendaciones accionables
```

**3.3. Ver Alertas**
```bash
fin alerts --month 2025-12

# Output:
# Alertas Financieras - 2025-12
# 
# ADVERTENCIAS:
#   ⚠️  Gastos Hormiga Altos: $625/semana
#   ⚠️  Categoría Dominante: Vivienda (39%)
```

---

### 4. Generación de Documentos y Vector Index

**4.1. Generar Todos los Reportes**
```bash
# Generar resúmenes, compromisos y perfiles
fin reports

# O solo para un mes
fin reports --month 2025-12
```

**4.2. Indexar Documentos para RAG**
```bash
# Indexar todo desde cero
fin index --rebuild

# Indexar solo un mes
fin index --month 2025-12

# Ver estadísticas
fin index
# Total documents: 26
```

---

### 5. Chat Interactivo con AI

**5.1. Iniciar Chat**
```bash
fin chat

# Asegúrate que Ollama esté corriendo:
# sudo systemctl start ollama
```

**5.2. Preguntas Efectivas**
```
> ¿Cuánto gasté en comida en diciembre?

📊 En diciembre 2025 gastaste $8,543 en alimentación,
representando el 22% de tus gastos totales...

📄 Fuentes: Resumen 2025-12

> ¿Qué MSI terminan pronto?

📅 Tienes 2 MSI que terminan en enero 2026...

> /sources
📄 Fuentes:
  1. commitment (N/A) - relevancia: 0.95

> /exit
👋 ¡Hasta pronto!
```

**5.3. Comandos del Chat**
- `/exit` - Salir
- `/clear` - Limpiar historial
- `/sources` - Ver fuentes de última respuesta
- `/examples` - Ver ejemplos de preguntas
- `/help` - Ayuda completa

---

### 6. Exportación de Datos

**6.1. Export Transactions**
```bash
# Todo diciembre a CSV
fin export transactions --start-date 2025-12-01 --end-date 2025-12-31 --format csv > dec.csv

# Por categoría a JSON
fin export transactions --category alimentacion --format json -o food.json

# Por banco
fin export transactions --bank bbva --format csv > bbva.csv
```

**6.2. Export MSI**
```bash
# MSI activos
fin export msi --status active --format csv > msi_active.csv

# Todos los MSI
fin export msi --status all --format json -o msi_all.json
```

---

## Workflows Comunes

### Workflow Mensual (Recomendado)

**Día 20-25 de cada mes:**
```bash
# 1. Procesar nuevos estados de cuenta
fin process data/inbox/2025/12/

# 2. Revisar y corregir clasificación
fin correct --limit 20

# 3. Generar reporte mejorado
fin report --month 2025-12

# 4. Ver alertas
fin alerts --month 2025-12

# 5. Actualizar índice para RAG
fin index --month 2025-12

# 6. Revisar con chat
fin chat
> ¿Cómo estuvo mi mes?
```

### Workflow Anual

**Fin de año:**
```bash
# 1. Exportar todo el año
fin export transactions --start-date 2025-01-01 --end-date 2025-12-31 --format csv > 2025_full.csv

# 2. Analizar tendencias
fin chat
> Compara mis gastos de cada trimestre de 2025

# 3. Backup de base de datos
cp data/finbot.db backups/finbot_2025.db
```

---

## Tips y Mejores Prácticas

### Organización de Archivos

**Producción:**
```
/Finanzas/
├── PDFs/
│   └── Procesar/          # Inbox
│       └── 2025/
│           └── 12/
├── Procesados/            # Archivados
│   └── 2025/
│       └── 12/
└── Reportes/              # Generados
    └── 2025/
```

### Automatización

**Cron job mensual:**
```bash
# Editar crontab
crontab -e

# Agregar (día 25 a las 9am):
0 9 25 * * cd /path/to/finbot && /path/to/venv/bin/fin process /Finanzas/PDFs/Procesar/$(date +\%Y)/$(date +\%m)/
```

### Clasificación Eficiente

1. **Primera vez:** Usa `fin correct --limit 50` para entrenar al sistema
2. **Después:** El sistema aprende y clasifica automáticamente >90%
3. **Revisa:** Solo transacciones grandes o inusuales

### Mantenimiento

**Semanal:**
- Revisar nuevas transacciones
- Verificar suscripciones activas

**Mensual:**
- Procesar estados de cuenta
- Generar reportes
- Revisar alertas

**Trimestral:**
- Revisar categorías y ajustar
- Exportar para análisis externo
- Backup de base de datos

---

## Casos de Uso Avanzados

### 1. Análisis de Tendencias

```bash
# Generar reportes de 6 meses
for month in {07..12}; do
    fin report --month 2025-$month
done

# Luego preguntar al chat:
fin chat
> Analiza la tendencia de mis gastos en los últimos 6 meses
```

### 2. Presupuestación

```bash
# Ver promedio de categoría
fin chat
> ¿Cuánto gasto en promedio al mes en transporte?

# Exportar para presupuesto
fin export transactions --category transporte --format csv > transport_budget.csv
```

### 3. Consolidación de Deuda

```bash
# Ver todos los MSI
fin msi

# Calcular costo total
fin chat
> ¿Cuánto me ha costado mi deuda en intereses este año?

# Planificar
> Si pago anticipadamente el MSI de MERCADO PAGO, ¿cuánto ahorro?
```

---

## Solución de Problemas Comunes

Ver [FAQ.md](FAQ.md) para troubleshooting detallado.

**Problemas Comunes:**
1. **PDF no se extrae**: Verificar con `pdfinfo`, puede estar protegido
2. **Clasificación incorrecta**: Usar `fin correct` para entrenar
3. **Chat no responde**: Verificar que Ollama esté corriendo
4. **Vector index vacío**: Ejecutar `fin index --rebuild`

---

## Referencia Rápida

### Comandos Principales

| Comando | Descripción |
|---------|-------------|
| `fin process <path>` | Procesar PDFs |
| `fin transactions --month YYYY-MM` | Ver transacciones |
| `fin summary --month YYYY-MM` | Resumen mensual |
| `fin msi` | Ver MSI activos |
| `fin correct` | Corregir clasificación |
| `fin subscriptions` | Ver suscripciones |
| `fin report --month YYYY-MM` | Reporte mejorado |
| `fin alerts` | Ver alertas |
| `fin reports` | Generar todos los reportes |
| `fin index --rebuild` | Reconstruir índice |
| `fin chat` | Chat interactivo |
| `fin export transactions` | Exportar transacciones |
| `fin export msi` | Exportar MSI |

### Opciones Comunes

| Opción | Descripción |
|--------|-------------|
| `--month YYYY-MM` | Filtrar por mes |
| `--format csv\|json` | Formato de export |
| `--start-date YYYY-MM-DD` | Fecha inicio |
| `--end-date YYYY-MM-DD` | Fecha fin |
| `--category <nombre>` | Filtrar por categoría |
| `--bank <nombre>` | Filtrar por banco |

---

## Recursos Adicionales

- [README.md](README.md) - Instalación y features
- [FAQ.md](FAQ.md) - Preguntas frecuentes
- [CATEGORIES.md](CATEGORIES.md) - Catálogo de categorías
- [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) - Setup para uso real

---

## Soporte

Para reportar bugs o solicitar features:
- GitHub Issues: https://github.com/norkodev/finbot/issues
- Email: [tu email]

## Licencia

MIT License - Ver LICENSE file para detalles.
