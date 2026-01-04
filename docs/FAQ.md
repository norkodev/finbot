# Finbot - Preguntas Frecuentes (FAQ)

## Instalación y Setup

### ¿Qué versión de Python necesito?
Python 3.9 o superior. Verifica con:
```bash
python --version
```

### ¿Cómo instalo las dependencias de OCR?
**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

### El comando `fin` no se encuentra
**Soluciones:**
1. Activa el entorno conda:
   ```bash
   conda activate finbot
   ```

2. Reinstala el package:
   ```bash
   pip install --force-reinstall -e .
   ```

3. Verifica que `~/.local/bin` esté en tu PATH:
   ```bash
   echo $PATH | grep .local/bin
   ```

---

## Procesamiento de PDFs

### ¿Qué bancos están soportados?
- BBVA (Crédito)
- HSBC (Crédito)
- Banamex Joy y Clásica (Crédito)
- Banorte (Crédito)
- Liverpool Crédito y Débito

### El PDF no se extrae correctamente
**Diagnóstico:**
```bash
pdfinfo /path/to/statement.pdf
```

**Problemas comunes:**
1. **PDF protegido con contraseña**: Desbloquear primero
2. **PDF escaneado (imágenes)**: Liverpool usa OCR automáticamente
3. **Formato desconocido**: El banco puede haber cambiado formato

**Soluciones:**
- Intenta con otro mes del mismo banco
- Revisa que sea el PDF correcto (no comprobante de pago)
- Reporta el issue con una muestra anonimizada

### El banco no detecta automáticamente
El sistema intenta detectar el banco por patrones en el PDF. Si falla:
```bash
# Verifica manualmente el contenido
pdftotext statement.pdf - | head -20
```

Busca palabras clave del banco en las primeras líneas.

### OCR muy lento (Liverpool)
El OCR con tesseract puede tardar 30-60 segundos por PDF. Es normal.

**Optimización:**
- Procesa por lotes nocturnos
- Usa un servidor más potente si tienes muchos PDFs

---

## Clasificación de Transacciones

### Muchas transacciones quedan "Sin categoría"
**Primera vez:** Normal. El sistema aprende con el tiempo.

**Solución:**
```bash
fin correct --limit 50
```

Después de corregir 50-100 transacciones, la precisión mejora significativamente.

### La clasificación automática es incorrecta
**Causas comunes:**
1. **Descripción ambigua**: "PAGO SERVICIO" no dice mucho
2. **Nuevo comercio**: No está en la base de datos
3. **Categoría múltiple**: OXXO puede ser comida o gastos hormiga

**Soluciones:**
- Usa `fin correct` para enseñarle al sistema
- El LLM aprende de tus correcciones
- Las reglas se aplican primero, luego el LLM

### ¿Cómo personalizo las categorías?
Edita `fin/config/rules.yaml`:
```yaml
- pattern: "NOMBRE_COMERCIO"
  category: "mi_categoria_custom"
  subcategory: "subcategoria"
```

Ver [CATEGORIES.md](CATEGORIES.md) para el catálogo completo.

---

## Ollama y Chat

### Ollama no inicia
**Verificar:**
```bash
sudo systemctl status ollama
```

**Iniciar:**
```bash
sudo systemctl start ollama
```

**Si falla:**
```bash
# Verificar logs
journalctl -u ollama -n 50

# Reinstalar
curl -fsSL https://ollama.com/install.sh | sh
```

### El modelo qwen2.5 no está disponible
```bash
# Descargar (4.7 GB)
ollama pull qwen2.5:7b

# Verificar
ollama list | grep qwen
```

### Chat responde muy lento o timeout
**Causas:**
1. **Primera vez**: Modelo se está cargando en memoria (30-60s)
2. **Hardware limitado**: Requiere ~8GB RAM
3. **Query compleja**: Muchos documentos a procesar

**Soluciones:**
- Aumentar timeout en el código (default 60s)
- Usar modelo más pequeño: `ollama pull qwen2.5:3b`
- Simplificar la pregunta

### Chat inventa números (alucinaciones)
**Prevención:**
- Los prompts tienen instrucciones anti-alucinación
- Sistema valida que números estén en fuentes
- Siempre verifica cifras importantes

**Si sucede:**
```bash
# Ver fuentes
> /sources

# Verificar manualmente
fin transactions --month 2025-12 | grep COMERCIO
```

### Vector index está vacío
```bash
# Rebuild desde cero
fin index --rebuild

# Verificar
fin index
# Total documents: XX
```

Si sigue vacío, verifica que haya reportes generados:
```bash
ls data/reports/summaries/
ls data/reports/merchants/
```

---

## Reportes y Alerts

### El reporte no se genera
**Verificar que haya transacciones:**
```bash
fin transactions --month 2025-12
```

Si hay transacciones pero no reporte:
```bash
# Generar manualmente
fin report --month 2025-12

# Ver errores
fin report --month 2025-12 2>&1 | grep Error
```

### Alertas no aparecen
Las alertas se basan en umbrales configurables. Puede que no haya nada que alertar.

**Personalizar umbrales:**
Crea `alert_config.json`:
```json
{
  "gastos_hormiga_weekly": 300,
  "category_dominance_pct": 25,
  "unusual_spending_sigma": 1.5
}
```

Usa:
```bash
fin alerts --config alert_config.json
```

---

## Export y Datos

### Export CSV no abre en Excel
**Problema:** Encoding o separadores

**Solución:**
```bash
# Agregar BOM para Excel
fin export transactions --format csv > temp.csv
echo -ne '\xEF\xBB\xBF' | cat - temp.csv > excel_ready.csv
```

O abre en Google Sheets que maneja mejor UTF-8.

### Quiero exportar todo
```bash
# Todas las transacciones
fin export transactions --format csv > all_transactions.csv

# Todos los MSI
fin export msi --status all --format csv > all_msi.csv

# Backup de BD completa
cp data/finbot.db backups/finbot_$(date +%Y%m%d).db
```

---

## Performance

### Procesar PDFs es muy lento
**Normal:** 5-15 segundos por PDF (con OCR hasta 60s)

**Optimización:**
- Procesa por lotes en horarios nocturnos
- Usa cron jobs automatizados

### La base de datos es muy grande
**Típico:** 1-5 MB por año de transacciones

**Si excede 100 MB:**
- Revisar duplicados
- Limpiar transacciones de prueba
- Archivar años antiguos en BD separada

### Chat demora mucho en buscar
**Causa:** Muchos documentos indexados

**Solución:**
- Usa filtros en queries: "en diciembre", "en OXXO"
- Ajusta top_k: `fin chat --top-k 3`

---

## Errores Comunes

### SQLAlchemy: DetachedInstanceError
Este error ocurre cuando se accede a relaciones fuera de sesión.

**Ya está corregido** en las versiones recientes. Si persiste:
```bash
git pull origin main
pip install --force-reinstall -e .
```

### ChromaDB: InvalidDimensionException
El vector store tiene dimensiones inconsistentes.

**Solución:**
```bash
# Borrar y rebuild
rm -rf data/chromadb/
fin index --rebuild
```

### PDF: ExtractionError
El extractor no pudo procesar el PDF.

**Diagnóstico:**
```bash
# Verificar PDF válido
pdfinfo statement.pdf

# Ver contenido
pdftotext statement.pdf - | less
```

Si el PDF es válido pero falla, es probable un formato nuevo del banco. Reportar issue.

---

## Mejores Prácticas

### ¿Con qué frecuencia debo procesar?
**Mensual** es lo recomendado, cuando recibes todos tus estados de cuenta.

**Fechas típicas:**
- Día 15-17: HSBC, Banamex Joy, Banorte
- Día 19-20: BBVA, Banamex Clásica
- Día 25: Procesar todo

### ¿Debo hacer backup?
**Sí.** La base de datos contiene toda tu información financiera.

**Backup recomendado:**
```bash
# Semanal
cp data/finbot.db backups/finbot_$(date +%Y%m%d).db

# Comprimir viejos
gzip backups/finbot_*.db
```

### ¿Puedo usar con múltiples personas?
Actualmente Finbot es **single-user**.

Para múltiples usuarios:
- Usa bases de datos separadas
- O crea un fork para multi-tenant

---

## Troubleshooting Avanzado

### Debug mode
```bash
# Ver queries SQL
export FINBOT_DEBUG=1
fin transactions --month 2025-12

# Ver logs de Ollama
journalctl -u ollama -f
```

### Rebuild completo
Si algo está muy roto:
```bash
# 1. Backup
cp data/finbot.db backup_before_rebuild.db

# 2. Limpiar
rm -rf data/chromadb/
rm -rf data/reports/

# 3. Rebuild
fin reports
fin index --rebuild
```

### Reportar un bug
Incluye:
1. Versión de Python: `python --version`
2. Comando exacto que falla
3. Output completo del error
4. PDF de ejemplo (anonimizado) si es problema de extracción

---

## Recursos

- [README.md](README.md) - Features e instalación
- [USAGE_GUIDE.md](USAGE_GUIDE.md) - Guía completa de uso
- [CATEGORIES.md](CATEGORIES.md) - Catálogo de categorías
- [GitHub Issues](https://github.com/norkodev/finbot/issues) - Reportar problemas

---

## Pregunta no Listada?

Si tu pregunta no está aquí:
1. Busca en GitHub Issues
2. Lee USAGE_GUIDE.md
3. Crea un nuevo issue con detalles

¡Contribuciones al FAQ son bienvenidas!
