# Manual de Usuario — E.V.A (Estacionamiento Virtual Automatizado)

Esta guía describe paso a paso cómo utilizar **E.V.A** desde la perspectiva de cada uno de los **4 roles del sistema**.

---

## 1. Rol Visitante (Sin Sesión)
Al abrir `http://127.0.0.1:5000` sin iniciar sesión, ingresas en **Modo Visitante**:
1. **Explorar el Mapa Interactivo:** Visualiza los marcadores de todos los estacionamientos afiliados con su tarifa base por hora y la cantidad de plazas libres en tiempo real.
2. **Buscador Básico:** Escribe una calle, barrio o nombre (por ejemplo, `UNSTA` o `25 de Mayo`) y presiona **Buscar en Mapa**.
3. **Ver Grilla de Plazas:** Haz clic en **Ver Grilla de Plazas (Verde / Rojo)** de cualquier estacionamiento para consultar sus lugares libres (**Verde**) y ocupados (**Rojo**), sus tarifas y reseñas verificadas.
4. **Restricción de Visitante:** Los filtros avanzados (por tipo de vehículo, precio máximo y techado) y la ocupación de plazas requieren iniciar sesión o crear una cuenta.

> *Captura sugerida:* `![Vista Visitante y Mapa](img/01-visitante-mapa.png)`

---

## 2. Rol Usuario con Sesión (Conductor)

### 2.1. Registro, Vehículos y Billetera Virtual
1. Haz clic en **Registrarse** (o inicia sesión con `juan.conductor@eva.com` / `eva1234`).
2. Dirígete a la pestaña **Mis Vehículos**:
   - Selecciona el **Tipo de Vehículo** (`Auto`, `Moto`, `Camioneta`, `Utilitario`).
   - Ingresa la **Placa / Patente** (ej. `AF420TK`) y una descripción opcional, y pulsa **Guardar Vehículo**.
3. Dirígete a la pestaña **Billetera Virtual**:
   - Usa los botones rápidos (`+$2,000`, `+$5,000`, `+$10,000`) o ingresa un monto personalizado (mínimo `$100.00`) y pulsa **Confirmar Depósito**. El saldo se acredita en el acto y se actualiza en la barra superior.

> *Captura sugerida:* `![Billetera Virtual y Mis Vehículos](img/02-conductor-billetera-vehiculos.png)`

### 2.2. Ocupar una Plaza Libre (Verde) y Seguir el Tiempo Real
1. En **Mapa y Locales**, aplica los filtros deseados y abre **Ver Grilla de Plazas (Verde / Rojo)** del estacionamiento elegido.
2. Haz clic sobre cualquier plaza en **Verde (`LIBRE`)**.
3. En el panel inferior de ingreso:
   - Elige uno de tus vehículos disponibles.
   - Selecciona la modalidad: **Por Hora** (cobra mínimo 1 hora completa y, desde el minuto 61, suma proporcionalmente por minuto) o **Estadía Fija**.
   - Verifica la previsualización de tarifa frente a tu saldo disponible (si tu saldo no cubre el mínimo, el sistema te permite recargar la diferencia en un clic).
4. Pulsa **Confirmar Ingreso e Iniciar Cronómetro**:
   - La plaza cambia inmediatamente a **Rojo (`OCUPADO`)**.
   - En la parte superior de la pantalla aparece tu **Banner de Estadía Activa en Tiempo Real** con el cronómetro `HH:MM:SS` y el monto acumulado actualizándose segundo a segundo.

> *Captura sugerida:* `![Grilla Verde/Rojo y Estadía en Vivo](img/03-grilla-tiempo-real.png)`

### 2.3. Finalizar Estadía, Obtener Ticket Imprimible y Dejar Reseña
1. Pulsa **Finalizar Estadía y Pagar** desde el banner superior o desde tu plaza en la grilla.
2. El sistema recalcula el tiempo exacto en el servidor, debita el importe de tu **Billetera Virtual** y libera automáticamente la plaza devolviéndola a **Verde**.
3. Se abre la ventana de confirmación donde puedes:
   - Hacer clic en **Abrir / Imprimir Ticket Oficial** para visualizar o guardar en PDF el comprobante numerado (`EVA-2026-XXXXX`).
   - Seleccionar de **1 a 5 estrellas** y escribir una reseña breve sobre el estacionamiento.

> *Captura sugerida:* `![Ticket Oficial y Calificación](img/04-ticket-y-resena.png)`

---

## 3. Rol Propietario del Estacionamiento
Inicia sesión con `carlos.dueno@eva.com` / `eva1234` (o regístrate eligiendo **Propietario de Estacionamiento** para crear tu local propio en relación 1 a 1):
1. **Indicadores en Tiempo Real:** Visualiza la ocupación actual, el monto acumulado en vivo de los vehículos estacionados en este instante, lo facturado hoy y el histórico total.
2. **Mapa de Plazas Estilo Restaurante:**
   - **Plazas Verdes (`DESOCUPADO`):** Haz clic sobre cualquiera para registrar un **Ingreso Manual en Mostrador** de un cliente presencial sin cuenta (ingresando patente, tipo de vehículo y modalidad).
   - **Plazas Rojas (`OCUPADO`):** Observa patente, tipo de vehículo, origen (`App EVA` o `Mostrador`), tiempo transcurrido y monto acumulado en vivo. Puedes finalizar y liberar la plaza desde el botón de cobro correspondiente.
3. **Capacidad y Tarifas:**
   - Modifica la **Cantidad Total de Plazas** (el sistema crea o desactiva plazas dinámicamente impidiendo eliminar plazas ocupadas).
   - Ajusta los precios **Por Hora** y **Estadía Fija** para cada tipo de vehículo en la **Matriz de Tarifas**.

> *Captura sugerida:* `![Panel del Propietario Estilo Restaurante](img/05-panel-propietario.png)`

---

## 4. Rol Administrador Global
Inicia sesión con `admin@eva.com` / `eva1234`:
1. Consulta las métricas consolidadas de toda la red E.V.A (usuarios, estacionamientos activos, ocupación global de plazas y volumen total facturado).
2. Habilita o pausa estacionamientos afiliados.
3. Activa o suspende cuentas de usuarios ante incidencias.
4. Agrega o desactiva categorías en el **Catálogo Maestro de Tipos de Vehículo**.
