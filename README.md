# E.V.A — Estacionamiento Virtual Automatizado

**E.V.A** resuelve la pérdida de tiempo y congestión vehicular de los conductores urbanos al buscar dónde estacionar, permitiéndoles localizar estacionamientos afiliados en un mapa interactivo, visualizar sus plazas libres u ocupadas en tiempo real y abonar automáticamente mediante una Billetera Virtual integrada. Asimismo, brinda a los propietarios de estacionamientos un panel operativo estilo restaurante para gestionar su capacidad, tarifas dinámicas e ingresos en vivo.

> *Espacio reservado para captura principal de la aplicación:*
> `![Pantalla Principal de E.V.A](docs/img/captura-principal.png)`

---

## Integrantes
- **Matias Santiago Hyon**
- **Ignacio Nicolas Garcia Juarez**
- **Maria Celeste Lara**
- **Belisario Abel Iturbe**

*Facultad de Ingeniería · Ingeniería en Informática · Taller Integrador II · UNSTA (2026)*

---

## Stack (Frontend, Backend, Base de Datos)
- **Capa de Presentación (Frontend):** HTML5 semántico, CSS3 moderno (Grid/Flexbox responsivo y semáforo visual Verde/Rojo), JavaScript Vanilla (`fetch` API, validaciones en cliente y cronómetro en tiempo real) y **Leaflet.js + OpenStreetMap** para el mapa interactivo (con modo esquemático local de respaldo sin conexión).
- **Capa de Lógica de Negocio (Backend):** **Python 3.9+** con **Flask 3** estructurado en servicios de dominio (`services/`), controladores REST (`routes/`) y encriptación segura de credenciales con `Werkzeug` (`pbkdf2:sha256`).
- **Capa de Persistencia (Base de Datos):** **MySQL / MariaDB** gestionado mediante **XAMPP**, accedido desde Python con `PyMySQL` usando consultas SQL parametrizadas (`repositories/`) y transacciones ACID (`COMMIT` / `ROLLBACK`).

---

## Cómo ejecutarlo

### 1. Requisitos previos
- **Python 3.9 o superior**
- **XAMPP** (con el servicio **MySQL Database** iniciado en puerto `3306`)
- **Git**

### 2. Clonar el repositorio e ingresar al proyecto
```bash
git clone <URL_DEL_REPOSITORIO_GITHUB>
cd eva-parking
```

### 3. Configurar el entorno virtual y copiar variables `.env`
**En macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**En Windows (PowerShell / CMD):**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Edita el archivo `.env` si tu usuario o contraseña de MySQL en XAMPP difieren del estándar (`DB_USER=root` y `DB_PASSWORD=` vacío).

### 4. Crear la base de datos y cargar datos de ejemplo
Asegúrate de que **MySQL Database** esté corriendo (en verde) en el panel de XAMPP y ejecuta:
```bash
python run.py --init-db
```
*(Alternativamente, puedes importar `database/schema.sql` y luego `database/seed.sql` desde `http://localhost/phpmyadmin`).*

### 5. Levantar el servidor (Backend + Frontend integrados)
```bash
python run.py
```

### 6. Abrir en el navegador y probar los 4 roles
Abre **`http://127.0.0.1:5050`** en tu computadora (o la URL `http://<IP_WI-FI>:5050` que imprime la consola para abrirlo desde tu celular).

| Rol | Correo de Prueba | Contraseña | Caso de Prueba Recomendado |
| :--- | :--- | :--- | :--- |
| **Visitante** | *(Sin iniciar sesión)* | — | Ver mapa y buscar locales sin filtros avanzados (`EP1-HU1` / `EP1-HU2`). |
| **Conductor (con saldo y estadía en vivo)** | `juan.conductor@eva.com` | `eva1234` | Ver estadía activa superando 1h, finalizar pago con Billetera, imprimir Ticket y calificar con estrellas. |
| **Conductora (saldo bajo para validación)** | `sofia.conductora@eva.com` | `eva1234` | Intentar estacionar con `$500` para disparar la validación de fondos insuficientes y recarga rápida. |
| **Propietario de Estacionamiento** | `carlos.dueno@eva.com` | `eva1234` | Gestionar grilla Verde/Rojo en vivo de *Parking Central Plaza*, tarifas, cantidad de plazas e ingreso en mostrador. |
| **Administrador Global** | `admin@eva.com` | `eva1234` | Supervisar métricas de toda la red, tipos de vehículo, usuarios y estacionamientos. |

---

## Qué funciona / Qué quedó pendiente

### Qué funciona en este MVP
- **Explorador con Mapa Interactivo y Permisos por Rol (`EP1`):** Búsqueda de estacionamientos afiliados para visitantes (sin filtros) y filtros avanzados por tipo de vehículo, precio máximo, techado y disponibilidad para usuarios con sesión.
- **Autenticación Encriptada y 4 Roles (`EP2`):** Registro e inicio de sesión con hash `pbkdf2:sha256`, validación de correos y patentes duplicadas, gestión de múltiples vehículos por usuario y registro 1 a 1 de propietarios con su estacionamiento.
- **Grilla de Plazas Estilo Restaurante en Tiempo Real (`EP3`):** Visualización instantánea de plazas libres (**Verde**) y ocupadas (**Rojo**), cronómetro en vivo, cálculo dinámico en servidor (1 hora mínima + fracción proporcional por minuto, o Estadía Fija) e ingreso/cobro manual en mostrador por parte del propietario.
- **Billetera Virtual y Ticket Digital Imprimible (`EP4`):** Recarga de saldo, validación de saldo mínimo al ingresar, débito automático al finalizar con liberación atómica de la plaza y emisión de comprobante imprimible (`/ticket/<id>`).
- **Reseñas y Calificaciones Verificadas (`EP5`):** Calificación de 1 a 5 estrellas y comentario al finalizar cada estadía.

### Qué quedó pendiente (Backlog futuro)
- **Reservas anticipadas por calendario futuro (`EP3` original):** Se priorizó la ocupación inmediata en tiempo real para garantizar precisión operativa en el MVP.
- **Integración con pasarelas bancarias externas reales (`EP4` de 40 SP):** Resuelta en el MVP mediante la Billetera Virtual interna para evitar dependencias bancarias externas.
- **Penalizaciones automáticas por inasistencia (`EP5-HU2`):** Ligadas al módulo futuro de reservas programadas.

---

## Uso de IA (herramientas usadas y para qué)
- **ChatGPT y Stitch (durante TP1 y TP2):** Generación de ideas iniciales, mejora de redacción de historias de usuario y bocetado visual de referencia ajustado luego en Figma por el equipo.
- **Antigravity (durante el cierre e integración de código):** Asistencia en la estructuración de la arquitectura en 3 capas con Flask y MySQL (XAMPP), revisión de transacciones ACID para la Billetera Virtual, diseño responsivo de la grilla de plazas en tiempo real y organización de la documentación técnica del repositorio. Todas las reglas de negocio (relación 1 a 1 de propietarios, cálculo de tarifa con mínimo de 1 hora más fracción por minuto y validación de saldo) fueron definidas y validadas por el equipo.
