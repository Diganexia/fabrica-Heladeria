# Plan técnico — Calculadora de costos para fábrica de helado

## Descripción general

Aplicación de escritorio para Windows (32 y 64 bits) que permite calcular el costo de producción de helados, gestionar materia prima y gastos variables, y exportar el detalle de cada receta en PDF.

---

## Stack tecnológico

| Rol | Tecnología | Motivo |
|---|---|---|
| Lenguaje | Python 3.8+ | Versiones 32 y 64 bits disponibles. Amplio ecosistema. |
| Interfaz gráfica | CustomTkinter | Widgets modernos, sin dependencias del sistema. Funciona en Windows 7+. |
| Base de datos | SQLite3 | Incluido en Python. Un solo archivo `.db` local, sin servidor. |
| Exportar PDF | ReportLab | Genera PDFs con tablas y formato profesional. Puro Python. Gratuito. |
| Empaquetado | PyInstaller | Convierte el proyecto en `.exe` sin que el usuario instale Python. |
| Íconos / logo | Pillow (PIL) | Para mostrar logo de la fábrica en la interfaz y en el PDF. Opcional. |

Todo el stack es **gratuito** y corre en **Windows 32 y 64 bits**.

---

## UX — Dashboard con menú lateral

La interfaz tiene un **menú lateral fijo** que permite navegar libremente entre secciones. En la parte superior hay una **barra de métricas siempre visible** que muestra costo de materia prima, gastos variables y precio de venta sugerido, actualizándose cada vez que se guardan cambios.

### Pantallas

| Pantalla | Descripción |
|---|---|
| Dashboard | Resumen de costos y últimas recetas guardadas |
| Materia prima | ABM de ingredientes con nombre, precio y unidad |
| Gastos variables | Luz, gas, empleados y producción mensual en kg |
| Recetas | Armar receta, calcular costo, definir margen y precio sugerido |

---

## Base de datos (SQLite)

### `ingredientes`
| Campo | Tipo | Descripción |
|---|---|---|
| id | INTEGER PK | Clave primaria |
| nombre | TEXT | Nombre del ingrediente |
| precio | REAL | Precio por unidad |
| unidad | TEXT | kg / L / gr / unidad |
| fecha_actualizacion | TEXT | Última modificación |

### `gastos`
| Campo | Tipo | Descripción |
|---|---|---|
| id | INTEGER PK | Clave primaria |
| nombre | TEXT | Nombre del gasto (ej: Luz) |
| monto | REAL | Monto del período |
| periodo | TEXT | mensual / diario |
| produccion_kg | REAL | Kg producidos en el período |

### `recetas`
| Campo | Tipo | Descripción |
|---|---|---|
| id | INTEGER PK | Clave primaria |
| nombre | TEXT | Nombre del helado |
| rinde_kg | REAL | Kg que produce la receta |
| margen_pct | REAL | Margen de ganancia definido por el usuario |
| fecha_creacion | TEXT | Fecha de creación |

### `receta_ingredientes`
| Campo | Tipo | Descripción |
|---|---|---|
| id | INTEGER PK | Clave primaria |
| receta_id | INTEGER FK | Referencia a `recetas` |
| ingrediente_id | INTEGER FK | Referencia a `ingredientes` |
| cantidad | REAL | Cantidad usada en la receta |

---

## Lógica de cálculo

### 1. Costo de materia prima por kg
```
Σ (cantidad_usada × precio_por_unidad) para cada ingrediente ÷ rinde_kg
```

### 2. Gasto variable por kg
```
Σ (todos los gastos del período) ÷ produccion_mensual_kg
```

### 3. Costo total por kg
```
Costo materia prima + Gasto variable por kg
```

### 4. Precio de venta sugerido
El margen se aplica **sobre el precio de venta** (no sobre el costo), que es la forma correcta en gastronomía:
```
Precio de venta = Costo total ÷ (1 − margen%)
```
> Ejemplo: costo $7.000, margen 40% → precio = $7.000 ÷ 0,60 = $11.667

El margen es una **variable que define el usuario** por receta y se guarda en la base de datos.

---

## Estructura de carpetas

```
heladeria/
  main.py                     ← arranque de la app
  requirements.txt
  build.bat                   ← script para generar el .exe
  db/
    database.py               ← conexión y queries SQLite
    heladeria.db              ← archivo de datos (se crea automáticamente)
  ui/
    main_window.py            ← ventana principal y menú lateral
    screen_dashboard.py
    screen_ingredientes.py
    screen_gastos.py
    screen_recetas.py
  reports/
    pdf_export.py             ← genera PDF con ReportLab
  assets/
    logo.png                  ← logo de la fábrica (opcional)
```

---

## PDF exportado — contenido

Cada receta genera un PDF con:
- Nombre del helado y fecha
- Tabla de ingredientes: nombre, cantidad, precio unitario, subtotal
- Desglose de gastos variables por kg
- Costo total por kg
- Margen de ganancia aplicado
- **Precio de venta sugerido**

---

## Fases de desarrollo

| Fase | Descripción |
|---|---|
| 1 ✅ | Crear proyecto, instalar dependencias, inicializar base de datos SQLite con las 4 tablas |
| 2 ✅ | Interfaz principal: ventana CustomTkinter con menú lateral y barra de métricas superior |
| 3 ✅ | Pantalla Materia prima: tabla, formulario ABM, validaciones |
| 4 ✅ | Pantalla Gastos variables: lista de gastos, campo de producción mensual, cálculo por kg |
| 5 ✅ | Pantalla Recetas: selector de ingredientes, cantidades, cálculo en tiempo real, margen editable por el usuario, precio sugerido |
| 6 ✅ | Exportación PDF con ReportLab: detalle completo de la receta |
| 7 ✅ | Modificar UX: nueva paleta azul/blanco, toasts, filtro en tablas, atajos de teclado, gráfico de torta en dashboard. Pulido: fix blank screen (bind_all → bind _entry), dashboard compacto, tipografía consistente con theme.py |
| 8 ✅ | Empaquetado con PyInstaller: generar `.exe` para Windows 64 bits — `dist\Heladeria.exe` (31.8 MB) |
| 8b ✅ | Fix v1.0.1: `hiddenimports` para `ui.screen_*` — import dinámico via `__import__()` no detectado por PyInstaller |
| 9 ✅ | Fase de feedback v1 (2026-06-15): rediseño completo de Gastos variables + fixes Materia prima |
| 9b ✅ | Build v1.0.2 (2026-06-15): exe generado (33.3 MB), publicado en GitHub releases — testing final queda para tester humano |
| 10 ✅ | Fase de feedback v2 (2026-06-22): fix PDF crash ("No item with that key"), fix chips topbar (altura + color), nueva pantalla Períodos con export PDF por período |
| 10b ✅ | Build v1.1.0 (2026-06-22): exe compilado con pantalla Períodos, publicado en GitHub releases |
| 11 ✅ | Análisis estático + fixes v1.1.1 (2026-06-22): 5 bugs corregidos — ver detalle abajo |
| 11b ✅ | Build v1.1.1 (2026-06-22): exe 31.8 MB, publicado en GitHub releases |
| 12 ✅ | Fix layout PDFs v1.1.2 (2026-06-23): PDF receta — spaceAfter título 2pt→6pt evita pisado con fecha/rinde/margen; PDF período — eliminada línea "Generado el..." duplicada bajo título del mes, queda solo el footer |
| 12b ✅ | Build v1.1.2 (2026-06-23): exe 31.8 MB, publicado en GitHub releases |
| 13 ✅ | Fix espaciado receta v1.1.3 (2026-06-23): spaceAfter título receta 6pt→12pt — texto fecha/rinde/margen demasiado pegado al nombre |
| 13b ✅ | Build v1.1.3 (2026-06-23): exe 31.8 MB, publicado en GitHub releases |

---

## Dependencias (`requirements.txt`)

```
customtkinter
reportlab
pillow
pyinstaller
```

> `sqlite3` viene incluido en Python, no necesita instalación.

---

## Empaquetado (`build.bat` + `heladeria.spec`)

- `heladeria.spec` incluye datos de CustomTkinter y ReportLab con `collect_data_files`.
- `DB_PATH` en `database.py` detecta `sys.frozen` y guarda la DB en `%APPDATA%\Heladeria\` cuando corre como `.exe`.
- Ejecutable generado: `dist\Heladeria.exe` — 31.8 MB, sin consola, sin icono.
- **Truco importante:** los módulos `ui.screen_*` se importan dinámicamente via `__import__()` en `main_window.py` — PyInstaller no los detecta. Deben estar en `hiddenimports` del spec.
- Releases publicados en GitHub: [v1.0.0](https://github.com/Diganexia/fabrica-Heladeria/releases/tag/v1.0.0), [v1.0.1](https://github.com/Diganexia/fabrica-Heladeria/releases/tag/v1.0.1)
