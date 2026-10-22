# ComedorOS

Sistema de gestión para el **área de eventos del comedor de la UNCuyo** (Mendoza). Reemplaza un conjunto de planillas de Excel y documentos de Word por una sola aplicación web: agenda de eventos, presupuestos, finanzas, compras, pagos al personal, inventario e informes de gestión.

> 🚧 En desarrollo activo. Hoy se usa de forma local, con datos reales del área.

## El problema

La gestión de eventos del comedor (catering institucional, ágapes, coffee breaks, cenas, puntos de venta) se llevaba en planillas separadas: una para la agenda, otra para la facturación con contaduría, otra para inventario, más presupuestos y el informe semestral armados a mano en Word. Eso implicaba datos duplicados, errores de carga y horas de trabajo para cada informe.

ComedorOS centraliza todo alrededor del **evento** como entidad principal: cada evento tiene su presupuesto, sus costos, sus compras y pagos asociados, y a partir de eso se calculan los indicadores y se generan los documentos automáticamente.

## Funcionalidades

**Eventos**
- Agenda agrupada por mes, con filtros por semestre y estado (solicitud → presupuestado → confirmado → realizado).
- Registro de solicitudes y conversión en presupuesto.
- Presupuestos con varias opciones de menú y precios diferenciados (regular, vegetariano, celíaco), extras incluidos y costo de personal. Exportación a Word con el formato oficial del área.

**Finanzas**
- Indicadores por semestre: eventos internos/externos, facturado, costo y margen.
- Rentabilidad por evento con desglose de costos (mantelería, materia prima, personal, planillas, varios).
- Facturación y cobros mensuales según la planilla compartida con contaduría.
- **Informe de gestión semestral** generado en Word: resumen, indicadores, desglose de servicios, balance mensual, puntos de venta, integrantes y funciones.
- Sincronización con el Excel histórico del área, sin pisar los eventos editados a mano.

**Compras y pagos**
- Compras con ítems por producto e historial de precios con variación porcentual.
- Pagos a personal eventual y planillas.

**Punto de venta** (gazebo, foodtruck, peñas)
- Catálogo de comidas y bebidas con tamaños/opciones (ej. papas chico/mediano/grande) y promos.
- Jornadas de venta con carta y precios del día; se puede copiar la carta de una jornada anterior.
- Caja pensada para el celular: ticket rápido, cambio de precios en plena venta, promos creadas en el momento, pago en efectivo, QR o dividido.
- Cierre con totales por medio de pago, por caja y por categoría, stock vendido y sobrante. El total se puede registrar en la Agenda.
- Funciona sin internet: la notebook hace de servidor y los celulares se conectan por WiFi o hotspot.

**Inventario**
- Vajilla, mantelería, uniformes y demás elementos por categoría.
- Envíos a lavandería y préstamos, con cálculo de disponibilidad (total − en lavandería − prestado).

**Equipo**
- Integrantes del área y funciones/actividades con sus responsables.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13+ · Django 6.1 |
| Base de datos | SQLite |
| Frontend | Templates de Django · Bootstrap 5.3 · Bootstrap Icons |
| Datos y documentos | pandas · openpyxl (importación de Excel) · python-docx (exportación a Word) |

Se eligió un stack simple a propósito: lo usan 2–3 personas, corre en una PC del área y no necesita una API ni un frontend separado.

## Estructura

```
comedoros/
├── comedor_uncuyo/          # Configuración del proyecto Django
├── eventos/                 # App principal
│   ├── models.py            # Evento, Presupuesto, Compra, Pago, Inventario, etc.
│   ├── views.py             # Vistas agrupadas por módulo
│   ├── forms.py             # Formularios y formsets
│   ├── templates/eventos/   # Interfaz (Bootstrap)
│   ├── static/eventos/      # Logos e imágenes
│   └── management/commands/ # Scripts de importación y limpieza de datos
├── ventas/                  # Punto de venta: catálogo, jornadas, caja y cierre
└── manage.py
```

## Instalación local

```bash
git clone https://github.com/gaboo5/comedoros.git
cd comedoros
python -m venv venv
venv\Scripts\activate          # Windows  (en Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Después abrí `http://127.0.0.1:8000/`. El panel de administración está en `/admin/`.

### Datos iniciales (opcional)

```bash
python manage.py cargar_extras_iniciales
python manage.py cargar_conceptos_costo
python manage.py cargar_funciones_iniciales
```

Los comandos `importar_informe2026`, `importar_facturacion` e `importar_inventario` cargan datos desde las planillas Excel del área. Los archivos no se incluyen en el repositorio porque contienen datos internos.

### Usar el punto de venta sin internet

1. Activá el **hotspot del celular** (no hace falta tener datos) y conectá la notebook a esa red.
2. En la notebook, iniciá el sistema aceptando conexiones de la red:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   La primera vez Windows pregunta por el firewall: permitilo en **redes privadas**.
3. Abrí la caja en la notebook y tocá el botón con el nombre de la caja: muestra un código QR y la dirección (ej. `http://192.168.43.20:8000/...`) para abrirla desde otro celular conectado a la misma red.

## Próximos pasos

- Recetas vinculadas al historial de precios de productos.
- Cálculo automático del costo por persona y del precio final con % de ganancia.
- Comparación presupuestado vs. real por evento.
- Inicio de sesión para uso compartido entre varios editores.

## Autor

**Gabriel Donoso**: jefe de mozos en el comedor de la UNCuyo y estudiante de Ciencia de Datos e IA.
