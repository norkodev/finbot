# Inbox - PDFs para Procesar

Coloca aquí los PDFs de tus estados de cuenta.

## Estructura Actual

```
inbox/
└── 2025/
    └── 12/          # Diciembre 2025 - LISTO PARA PRUEBAS
        └── (coloca tus PDFs aquí)
```

## Formato de Nombres Recomendado

```
{banco}_{YYYY-MM}.pdf
```

**Ejemplos**:
- `bbva_2025-12.pdf`
- `hsbc_2025-12.pdf`
- `banamex_2025-12.pdf`
- `liverpool_credito_2025-12.pdf`

## Cómo Procesar

### Opción 1: Script Automático (Recomendado)
```bash
# Desde la raíz del proyecto
./validate_e2e.sh
```

### Opción 2: Manual
```bash
# Procesar carpeta del mes
fin process data/inbox/2025/12/

# O archivo específico
fin process data/inbox/2025/12/bbva_2025-12.pdf
```

## Después de Procesar

Los PDFs se pueden:
1. Mover a `data/processed/2025/12/`
2. Eliminar (si tienes respaldos)
3. Comprimir y archivar

## Base de Datos

- **Nueva**: La BD se creará automáticamente al procesar el primer PDF
- **Ubicación**: `data/finbot.db`
- **Backup anterior**: Si existía, está en `data/finbot_backup_*.db`

## Siguiente Paso

1. ✅ Estructura creada
2. 📥 Coloca tus PDFs en `data/inbox/2025/12/`
3. ▶️  Ejecuta `./validate_e2e.sh` o `fin process data/inbox/2025/12/`
