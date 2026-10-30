# Memoria del Proyecto — E.V.A (Taller Integrador II · UNSTA 2026)

---

## 1. Antecedentes (De dónde venimos: TP1 y TP2)

### Trabajo Práctico 1 — Definición del Problema y MVP
En el **TP1** identificamos una problemática cotidiana del tránsito urbano: los conductores pierden tiempo valioso circulando a baja velocidad o estacionando en doble fila por desconocer dónde hay estacionamientos cercanos con lugares disponibles y cuáles son sus tarifas reales. Aplicando **Design Thinking**, definimos como MVP a **E.V.A (Estacionamiento Virtual Automatizado)**: una aplicación web con mapa digitalizado, registro de cuentas, lista dinámica de precios, estacionamientos afiliados y procesamiento de pagos.

### Trabajo Práctico 2 — Épicas, Historias de Usuario y Planning Poker
En el **TP2** estructuramos el Product Backlog en **5 Épicas**:
- **EP1 (*El comienzo de la aventura*):** Acceso al mapa y búsqueda básica para visitantes; filtros para usuarios registrados.
- **EP2 (*El troll del puente*):** Registro con validación de duplicados, inicio de sesión seguro y perfil con vehículos.
- **EP3 (*El ave mensajera*):** Selección y ocupación/reserva de plazas con visibilidad para el encargado del estacionamiento.
- **EP4 (*El poder del oro*):** Cobro de tarifa y emisión de comprobante/factura.
- **EP5 (*La carpeta roja*):** Confirmación de servicio y feedback mediante reseñas.

Durante la estimación con **Planning Poker**, detectamos que la mayor incertidumbre técnica residía en **EP4 (40 Story Points)** debido a la complejidad burocrática y técnica de integrar APIs bancarias externas, y en la validación rigurosa de errores de base de datos en **EP2**.

---

## 2. Solución Construida (Alcance del MVP vs. Backlog)

Para lograr un MVP sólido, funcional de punta a punta y persistente en ** tres capas reales (HTML/CSS/JS + Python Flask + MySQL en XAMPP)**, tomamos dos decisiones estratégicas de ingeniería:
1. **Billetera Virtual Interna en lugar de pasarela bancaria externa:** Resolvió el bloqueo de 40 SP de la Épica 4 permitiendo depósitos de saldo, validación de fondos insuficientes en tiempo real, débito automático al finalizar la estadía y acreditación inmediata al propietario.
2. **Grilla Operativa en Tiempo Real ("Estilo Restaurante"):** En lugar de reservas diferidas complejas que podían generar plazas bloqueadas sin presencia física, implementamos un control en vivo (**Verde = Desocupado / Rojo = Ocupado**) con cronómetro sincronizado con el reloj del servidor MySQL y cálculo dinámico (mínimo 1 hora + fracción proporcional por minuto, o Estadía Fija).

### Tabla Resumen: Hecho vs. Pendiente

| Ítem del Backlog (TP2) | Estado Final | Detalle de Implementación |
| :--- | :---: | :--- |
| **EP1-HU1 / HU2:** Mapa y buscador para Visitante sin filtros | **Hecho** | Mapa Leaflet + OpenStreetMap (con respaldo offline) y bloqueo de filtros para visitantes. |
| **EP2-HU1 / HU2:** Registro e inicio de sesión con validación | **Hecho** | Contraseñas encriptadas (`pbkdf2:sha256`), control de sesión y rechazo de emails duplicados. |
| **EP2-HU3:** Vehículos del usuario y filtros avanzados | **Hecho** | Alta de múltiples vehículos con patente única normalizada y filtros activos para usuarios logueados. |
| **EP3 (Adaptada):** Gestión de plazas en vivo y panel del dueño | **Hecho** | Grilla Verde/Rojo estilo restaurante, redimensionamiento de plazas $N$, tarifas por vehículo e ingreso manual en mostrador. |
| **EP4-HU1:** Pago con validación de fondos insuficientes | **Hecho** | Billetera Virtual con exigencia de saldo mínimo al ingresar y débito atómico con liberación de plaza al salir. |
| **EP4-HU2:** Factura / Ticket digital imprimible | **Hecho** | Emisión automática de comprobante numerado `EVA-2026-XXXXX` con vista de impresión `/ticket/<id>`. |
| **EP5-HU1:** Calificación y reseña al finalizar estadía | **Hecho** | Calificación verificada de 1 a 5 estrellas y comentario visible en la ficha del estacionamiento. |
| **EP3 / EP5-HU2:** Reservas a fecha futura y multas por inasistencia | **Pendiente** | Pospuesto para una versión posterior para priorizar la operación inmediata en tiempo real sin conflictos de turnos. |

---

## 3. Decisión Técnica Destacada (Para la Defensa Oral)

- **Decisión tomada:** Calcular siempre el tiempo transcurrido y el monto a cobrar en el **servidor (Python + MySQL `TIMESTAMPDIFF(SECOND, fecha_ingreso, NOW())`)** dentro de una **transacción ACID**, utilizando el reloj de JavaScript únicamente para refrescar la interfaz segundo a segundo.
- **Alternativa descartada:** Calcular el tiempo y el costo en el navegador del cliente y enviar el monto final por POST al finalizar la estadía.
- **Por qué:** Si el cálculo dependiera del navegador, el cronómetro se perdería al cerrar la pestaña o recargar la página, y cualquier usuario podría alterar el reloj de su dispositivo para pagar menos. Con el cálculo en la Capa de Negocio sobre la marca `fecha_ingreso` persistida en MySQL, los datos sobreviven a reinicios del navegador o del servidor Flask y la facturación es inalterable.

---

## 4. Conclusiones del Equipo

- **Qué aprendimos:** Comprendimos en la práctica cómo desacoplar una aplicación real en **tres capas** (Presentación, Lógica de Negocio y Persistencia), la importancia de las **transacciones en bases de datos relacionales** cuando hay dinero/saldo y cambios de estado simultáneos (debitar billetera y liberar plaza a verde), y cómo transformar una historia de usuario inabarcable (40 SP de pagos bancarios) en una solución de MVP viable y completa (Billetera Virtual).
- **Qué nos costó más:** Coordinar la consistencia entre el estado visual en tiempo real (cronómetros corriendo en pantalla tanto para el conductor como para el propietario) y las reglas de validación ante casos borde (patentes duplicadas, reducción de cantidad de plazas cuando hay autos estacionados o saldo insuficiente al momento de retirarse).
- **Qué haríamos distinto si empezáramos de nuevo:** Definiríamos el esquema entidad-relación y los contratos JSON de la API desde la primera semana antes de diseñar las pantallas finales, lo que acelera enormemente el trabajo en paralelo entre quienes desarrollan frontend y quienes programan backend.

---

## 5. Guion Sugerido para la Presentación de 10 Minutos (TP5)

1. **Minuto 0:00 – 1:00 | El Problema (Integrante 1):** Quién sufre el caos de estacionar en horario pico y cómo E.V.A evita dar vueltas o estacionar en doble fila.
2. **Minuto 1:00 – 2:00 | El Alcance (Integrante 2):** Mostrar la tabla *Hecho vs. Pendiente* explicando cómo destrabaron la Épica 4 (40 SP) con la Billetera Virtual y la grilla en tiempo real.
3. **Minuto 2:00 – 6:30 | Demo en Vivo (Integrante 3):**
   - Entrar como **Visitante**: mostrar el mapa y que los filtros están bloqueados.
   - Entrar como **Conductora con saldo bajo** (`sofia.conductora@eva.com`): intentar estacionar para **mostrar la validación de fondos insuficientes** y probar cargar una patente inválida (`A@1`) para mostrar la **validación en frontend**.
   - Cambiar a **Conductor activo** (`juan.conductor@eva.com`): ver su auto en `P-02` pasando la hora con monto dinámico subiendo en vivo $\rightarrow$ pulsar **Finalizar y Pagar** $\rightarrow$ abrir el **Ticket Imprimible** y dejar **5 estrellas**.
   - Entrar como **Propietario** (`carlos.dueno@eva.com`): mostrar cómo `P-02` ya figura en **Verde**, registrar un ingreso manual en mostrador y mostrar al **Administrador** (`admin@eva.com`).
4. **Minuto 6:30 – 8:30 | Cómo está hecho (Integrante 4):** Mostrar el diagrama de las 3 capas, el DER de 10 tablas en MySQL y explicar la decisión técnica del cálculo de tiempo en servidor + transacciones ACID.
5. **Minuto 8:30 – 10:00 | Cierre Grupal:** Aprendizajes del año y qué harían distinto.
