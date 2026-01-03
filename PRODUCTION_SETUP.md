# Estructura de Carpetas para Producción - Finbot

## Organización Recomendada

Para procesamiento periódico de estados de cuenta (2-3 veces/mes por banco), se recomienda la siguiente estructura:

```
finbot/
├── data/
│   ├── statements/              # Carpeta principal de estados de cuenta
│   │   ├── 2026/
│   │   │   ├── 01-enero/
│   │   │   │   ├── BBVA_TDC_20260115.pdf
│   │   │   │   ├── HSBC_TDC_20260120.pdf
│   │   │   │   ├── BANAMEX_CLASICA_20260119.pdf
│   │   │   │   └── ...
│   │   │   ├── 02-febrero/
│   │   │   │   └── ...
│   │   │   └── 12-diciembre/
│   │   ├── 2027/
│   │   │   └── ...
│   │   └── processed/           # Backup de procesados (opcional)
│   │       ├── 2026/
│   │       └── 2027/
│   ├── examples/                # Solo para desarrollo/testing
│   └── temp/                    # Archivos temporales OCR
└── fin.db                       # Base de datos SQLite

```

## Convención de Nombres de Archivos

**Formato recomendado**: `BANCO_TIPO_YYYYMMDD.pdf`

Ejemplos:
- `BBVA_TDC_20260115.pdf` → BBVA Tarjeta de Crédito, 15 enero 2026
- `HSBC_TDC_20260120.pdf` → HSBC Tarjeta de Crédito, 20 enero 2026
- `BANAMEX_JOY_20260117.pdf` → Banamex Joy, 17 enero 2026
- `BANORTE_TDC_20260117.pdf` → Banorte, 17 enero 2026
- `LIVERPOOL_TDC_20260118.pdf` → Liverpool Crédito
- `LIVERPOOL_TDD_20260118.pdf` → Liverpool Débito

## Uso en Producción

### Procesamiento Manual (Actual)

```bash
# Procesar todos los PDFs del mes actual
fin process data/statements/2026/01-enero/

# Procesar mes específico
fin process data/statements/2026/02-febrero/

# Procesar todo el año
fin process data/statements/2026/
```

### Procesamiento Automático (Futuro)

Crear script o cron job:

```bash
#!/bin/bash
# process_monthly.sh

YEAR=$(date +%Y)
MONTH=$(date +%m)
MONTH_NAME=$(date +%m-%B | tr '[:upper:]' '[:lower:]')

STATEMENTS_DIR="data/statements/$YEAR/$MONTH_NAME"

if [ -d "$STATEMENTS_DIR" ]; then
    echo "Processing statements for $MONTH_NAME $YEAR..."
    fin process "$STATEMENTS_DIR"
else
    echo "No statements found for $MONTH_NAME $YEAR"
fi
```

**Cron** (ejemplo: cada día 20 del mes):
```
0 9 20 * * /home/nor/Workspace/finbot/process_monthly.sh
```

## Workflow Recomendado

### 1. Descarga de Estados de Cuenta
- Descargar PDFs de bancos (según fecha de corte de cada uno)
- Organizar en carpeta del mes correspondiente

### 2. Procesamiento
```bash
cd /home/nor/Workspace/finbot
fin process data/statements/2026/01-enero/
```

### 3. Revisión
```bash
# Ver transacciones del mes
fin transactions --month 2026-01

# Ver resumen
fin summary --month 2026-01

# Ver MSI activos
fin msi --ending-soon 3
```

### 4. Correcciones (opcional)
```bash
# Corregir clasificaciones incorrectas
fin correct
```

## Fechas de Corte Estimadas por Banco

Basándose en los PDFs de ejemplo:

| Banco | Fecha Corte Aprox | Procesamiento Sugerido |
|-------|-------------------|------------------------|
| BBVA | 19-20 del mes | Día 22 |
| HSBC | 17-20 del mes | Día 22 |
| Banamex Clásica | 19-20 del mes | Día 22 |
| Banamex Joy | 15-17 del mes | Día 20 |
| Banorte | 15-17 del mes | Día 20 |
| Liverpool | Variable | Revisar mensual |

**Recomendación**: Procesar **2 veces por mes**:
- **Día 20**: Bancos con corte ~15-17
- **Día 25**: Bancos con corte ~19-22

## Migración de `examples/` a Producción

```bash
# Crear estructura
mkdir -p data/statements/2025/12-diciembre

# Mover ejemplos actuales (si corresponden a dic 2025)
mv data/examples/*.pdf data/statements/2025/12-diciembre/

# Vaciar examples (dejar solo .gitkeep)
rm data/examples/*.pdf
touch data/examples/.gitkeep
```

## Backup y Mantenimiento

### Backup Automático
```bash
# Antes de procesar, hacer backup de DB
cp fin.db fin.db.backup.$(date +%Y%m%d)

# Mantener solo últimos 10 backups
ls -t fin.db.backup.* | tail -n +11 | xargs rm -f
```

### Limpieza de Temporales OCR
```bash
# Limpiar archivos temp de OCR (si se generan)
rm -rf data/temp/*
```

## GitIgnore Actualizado

Agregar a `.gitignore`:
```
# Datos de producción
data/statements/
!data/statements/.gitkeep

# Backups
*.backup.*
fin.db.backup*

# Temporales OCR
data/temp/
```

## Próximos Pasos (Automatización)

1. **Alertas**: Notificar cuando hay PDFs nuevos sin procesar
2. **Validación**: Verificar que todos los bancos tengan PDF del mes
3. **Dashboard**: CLI o web para ver status de procesamiento
4. **Auto-clasificación**: Mejorar % con LLM
5. **Reportes**: Generar reportes mensuales automáticos
