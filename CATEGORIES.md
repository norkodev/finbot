# Finbot - Catálogo de Categorías

## Introducción

Este documento lista todas las categorías y subcategorías usadas por Finbot para clasificar transacciones.

El sistema de clasificación tiene 3 niveles:
1. **Reglas** (`fin/config/rules.yaml`) - Patrones exactos
2. **Historial** - Aprende de correcciones anteriores
3. **LLM** - Qwen2.5 con contexto mexicano

---

## Categorías Principales

### 1. Alimentación

**`alimentacion`**

Gastos en comida y bebida.

**Subcategorías:**
- `supermercado` - Compras de despensa
- `restaurante` - Comidas en establecimientos
- `delivery` - Pedidos a domicilio (Uber Eats, Rappi, etc.)
- `cafeteria` - Cafés, panaderías
- `bar` - Bares y antros

**Ejemplos:**
- SUPERCENTER SANTIN → alimentacion / supermercado
- RESTAURANTE EL FOGON → alimentacion / restaurante
- UBER EATS → alimentacion / delivery
- STARBUCKS → alimentacion / cafeteria

---

### 2. Transporte

**`transporte`**

Gastos relacionados con movilidad.

**Subcategorías:**
- `gasolina` - Combustible
- `uber` - Viajes en app
- `estacionamiento` - Parking
- `autopista` - Casetas y peajes
- `taxi` - Taxis tradicionales
- `transporte_publico` - Metro, camión

**Ejemplos:**
- GASOLINERA PEMEX → transporte / gasolina
- UBER TRIP → transporte / uber
- ESTACIONAMIENTO → transporte / estacionamiento

---

### 3. Servicios

**`servicios`**

Servicios recurrentes y utilidades.

**Subcategorías:**
- `internet` - Servicio de internet
- `telefono` - Celular, teléfono fijo
- `luz` - CFE, electricidad
- `agua` - Servicio de agua
- `gas` - Gas LP/natural
- `streaming` - Netflix, Spotify, etc.
- `otros` - Otros servicios

**Ejemplos:**
- TELMEX → servicios / internet
- TOTALPLAY → servicios / internet
- CFE → servicios / luz
- NETFLIX.COM → servicios / streaming

---

### 4. Vivienda

**`vivienda`**

Gastos del hogar.

**Subcategorías:**
- `renta` - Renta mensual
- `mantenimiento` - Reparaciones
- `muebles` - Muebles y decoración
- `hogar` - Artículos para el hogar

**Ejemplos:**
- TRANSFERENCIA RENTA → vivienda / renta
- HOME DEPOT → vivienda / muebles
- WALMART MUEBLES → vivienda / muebles

---

### 5. Salud

**`salud`**

Gastos médicos y bienestar.

**Subcategorías:**
- `farmacia` - Medicamentos
- `doctor` - Consultas médicas
- `dental` - Servicios dentales
- `gimnasio` - Membresías de gym
- `seguro` - Seguros de gastos médicos

**Ejemplos:**
- FARMACIAS GUADALAJARA → salud / farmacia
- CONSULTORIO DR → salud / doctor
- SPORT CITY → salud / gimnasio

---

### 6. Entretenimiento

**`entretenimiento`**

Diversión y ocio.

**Subcategorías:**
- `cine` - Películas
- `streaming` - Plataformas digitales
- `eventos` - Conciertos, shows
- `juegos` - Videojuegos, juguetes
- `hobbies` - Otros pasatiempos

**Ejemplos:**
- CINEPOLIS → entretenimiento / cine
- TICKETMASTER → entretenimiento / eventos
- STEAM GAMES → entretenimiento / juegos

---

### 7. Educación

**`educacion`**

Inversión en aprendizaje.

**Subcategorías:**
- `colegiatura` - Gastos escolares
- `cursos` - Cursos y talleres
- `libros` - Libros y material
- `subscripciones` - Plataformas educativas

**Ejemplos:**
- UNIVERSIDAD → educacion / colegiatura
- UDEMY → educacion / cursos
- KINDLE BOOKS → educacion / libros

---

### 8. Ropa

**`ropa`**

Vestimenta y accesorios.

**Subcategorías:**
- `ropa` - Prendas
- `calzado` - Zapatos
- `accesorios` - Bolsas, joyería

**Ejemplos:**
- ZARA → ropa / ropa
- NIKE → ropa / calzado
- LIVERPOOL → ropa / ropa

---

### 9. Tecnología

**`tecnologia`**

Dispositivos y servicios tech.

**Subcategorías:**
- `hardware` - Computadoras, celulares
- `software` - Aplicaciones, licencias
- `reparaciones` - Service de equipo

**Ejemplos:**
- APPLE STORE → tecnologia / hardware
- MICROSOFT → tecnologia / software
- BEST BUY → tecnologia / hardware

---

### 10. Viajes

**`viajes`**

Gastos de turismo.

**Subcategorías:**
- `hospedaje` - Hoteles, Airbnb
- `vuelos` - Boletos de avión
- `tours` - Actividades turísticas
- `internacional` - Compras en el extranjero

**Ejemplos:**
- BOOKING.COM → viajes / hospedaje
- AEROMEXICO → viajes / vuelos
- AIRBNB → viajes / hospedaje

---

### 11. Gastos Hormiga

**`gastos_hormiga`**

Gastos pequeños frecuentes.

**Subcategorías:**
- `conveniencia` - OXXO, 7-Eleven
- `snacks` - Botanas, dulces
- `impulso` - Compras no planificadas

**Ejemplos:**
- OXXO → gastos_hormiga / conveniencia
- 7 ELEVEN → gastos_hormiga / conveniencia

---

### 12. Transferencias

**`transferencias`**

Movimientos entre cuentas.

**Subcategorías:**
- `ahorro` - A cuenta de ahorro
- `inversion` - A inversiones
- `prestamo` - Préstamos a terceros
- `entre_cuentas` - Entre tus cuentas

**Ejemplos:**
- TRANSFERENCIA SPEI → transferencias / entre_cuentas
- ABONO CUENTA AHORRO → transferencias / ahorro

---

### 13. Impuestos

**`impuestos`**

Pagos fiscales.

**Subcategorías:**
- `isr` - Impuesto sobre la renta
- `predial` - Impuesto predial
- `tenencia` - Tenencia vehicular
- `otros` - Otros impuestos

**Ejemplos:**
- SAT PAGO → impuestos / isr
- PAGO PREDIAL → impuestos / predial

---

### 14. Mascotas

**`mascotas`**

Gastos de animales de compañía.

**Subcategorías:**
- `veterinario` - Consultas médicas
- `alimento` - Comida para mascotas
- `accesorios` - Juguetes, camas

**Ejemplos:**
- VETERINARIA → mascotas / veterinario
- PETCO → mascotas / alimento

---

### 15. Regalos

**`regalos`**

Obsequios y donaciones.

**Subcategorías:**
- `cumpleanos` - Regalos de cumpleaños
- `navidad` - Regalos navideños
- `donaciones` - Donativos

**Ejemplos:**
- AMAZON GIFT → regalos / cumpleanos

---

### 16. Belleza

**`belleza`**

Cuidado personal.

**Subcategorías:**
- `estetica` - Salón de belleza
- `cosmeticos` - Maquillaje, perfumes
- `spa` - Tratamientos

**Ejemplos:**
- SEPHORA → belleza / cosmeticos
- SPA  → belleza / spa

---

### 17. Seguros

**`seguros`**

Pólizas de seguro.

**Subcategorías:**
- `auto` - Seguro de auto
- `vida` - Seguro de vida
- `hogar` - Seguro de hogar
- `gastos_medicos` - Seguro médico

**Ejemplos:**
- QUALITAS → seguros / auto
- METLIFE → seguros / vida

---

### 18. Inversiones

**`inversiones`**

Instrumentos financieros.

**Subcategorías:**
- `cetes` - CETES
- `fondos` - Fondos de inversión
- `acciones` - Bolsa
- `crypto` - Criptomonedas

---

### 19. Otros

**`otros`**

Gastos no clasificados en otra categoría.

**Subcategorías:**
- `varios` - Miscellaneous

---

## Tipos de Transacción

Además de la categoría, cada transacción tiene un **tipo**:

- `expense` - Gasto normal
- `payment` - Pago a tarjeta o cuenta
- `income` - Ingreso
- `fee` - Comisión bancaria
- `interest` - Interés cobrado
- `reversal` - Reversión/cancelación

---

## Personalizar Categorías

### Agregar Reglas Personalizadas

Edita `fin/config/rules.yaml`:

```yaml
# Tus reglas personalizadas
- pattern: "MI_COMERCIO_FAVORITO"
  category: "mi_categoria"
  subcategory: "mi_subcategoria"
  priority: 100  # Mayor = más prioridad
```

### Entrenar el Sistema

```bash
fin correct --limit 50
```

El sistema aprende de tus correcciones y las aplica automáticamente.

---

## Estadísticas de Clasificación

Después de entrenar el sistema:
- **Reglas**: ~40% de transacciones
- **Historial**: ~30% de transacciones
- **LLM**: ~25% de transacciones
- **Sin clasificar**: <5%

---

## Mejores Prácticas

1. **Consistencia**: Usa las mismas categorías siempre
2. **Granularidad**: Usa subcategorías para mejor análisis
3. **Revisión**: Verifica clasificaciones mensualmente
4. **Entrenamiento**: Corrige al menos 50 transacciones inicialmente

---

## Ejemplos de Clasificación

| Descripción | Categoría | Subcategoría |
|-------------|-----------|--------------|
| OXXO HDA DEL VALLE | gastos_hormiga | conveniencia |
| UBER TRIP | transporte | uber |
| NETFLIX.COM | servicios | streaming |
| SPORT CITY UNIVERSITY | salud | gimnasio |
| AMAZON MEXICO | otros | varios |
| SUPERCENTER SANTIN | alimentacion | supermercado |
| STARBUCKS | alimentacion | cafeteria |
| GASOLINERA PEMEX | transporte | gasolina |

---

## Recursos

- [USAGE_GUIDE.md](USAGE_GUIDE.md) - Cómo usar el sistema
- [FAQ.md](FAQ.md) - Preguntas frecuentes
- `fin/config/rules.yaml` - Archivo de reglas

---

## Contribuir

¿Falta una categoría importante? Crea un issue en GitHub con tu sugerencia.
