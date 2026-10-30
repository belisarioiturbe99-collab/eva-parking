# Guía de Despliegue 24/7 en la Nube — E.V.A (Executive Mobility)

Esta guía explica paso a paso cómo publicar **E.V.A** en Internet con un enlace `https://...` permanente, accesible las **24 horas desde cualquier celular o computadora** (incluso con tu Mac y XAMPP apagados), de forma **100% gratuita y sin tarjeta de crédito**, cumpliendo además con la **Opción B (Aplicación Desplegada)** del Trabajo Práctico 5 (UNSTA).

---

## Arquitectura en la Nube (Gratuita)

Para que la arquitectura en 3 capas funcione 24/7 sin depender de tu computadora local, reemplazamos XAMPP y el servidor local por dos servicios gratuitos en la nube:

1. **Capa de Datos (MySQL 8 en la nube):** **Aiven for MySQL (Free Plan)** — Base de datos MySQL administrada gratuita (`$0/mes`, sin tarjeta).
2. **Capa de Negocio + Presentación (Python/Flask + Gunicorn):** **Render (Free Web Service)** — Conectado directamente a tu repositorio de **GitHub** (cada `git push` actualiza tu web automáticamente).

El proyecto ya incluye toda la configuración necesaria:
- `wsgi.py`, `Procfile` y `render.yaml` para ejecución en producción con **Gunicorn**.
- Soporte automático de cifrado **SSL/TLS** en `backend/database.py` para MySQL remoto.
- Inicialización automática (`AUTO_INIT_DB=true`): en el primer arranque en la nube, E.V.A detecta que la base está vacía y ejecuta automáticamente `database/schema.sql` (10 tablas) y `database/seed.sql` (estacionamientos, tarifas y cuentas demo) sin necesidad de consola SSH ni phpMyAdmin.

---

## Paso 1: Subir el proyecto a GitHub

1. Crea una cuenta o inicia sesión en [https://github.com](https://github.com).
2. Haz clic en **New repository** (arriba a la derecha):
   - **Repository name:** `eva-parking`
   - **Visibility:** Public (o Private)
   - **NO** marques *"Add a README file"* ni *".gitignore"* (el proyecto ya los tiene).
   - Haz clic en **Create repository**.
3. Abre la aplicación **Terminal** en tu Mac y ejecuta estos comandos (reemplazando `TU_USUARIO` por tu usuario real de GitHub):

```bash
cd /Users/belisario/.gemini/antigravity/scratch/eva-parking
git init
git branch -M main
git add .
git commit -m "feat: sistema EVA Executive Mobility 3 capas listo para produccion"
git remote add origin https://github.com/TU_USUARIO/eva-parking.git
git push -u origin main
```

> **Seguridad:** El archivo `.gitignore` ya excluye automáticamente tu `.env` local y la carpeta `venv/`.

---

## Paso 2: Crear la Base de Datos MySQL 24/7 en Aiven (Gratis)

1. Ingresa a [https://console.aiven.io](https://console.aiven.io) y regístrate gratis (puedes entrar con tu cuenta de GitHub o Google, **no pide tarjeta de crédito**).
2. Haz clic en **Create service**:
   - Selecciona **MySQL**.
   - En **Service plan**, elige **Free** (`$0/month`).
   - Elige la región más cercana (por ejemplo, *North America / US East* o *South America* si está habilitada en Free) y ponle de nombre `eva-mysql`.
   - Haz clic en **Create free service**.
3. Espera ~1 a 2 minutos hasta que el estado pase de *Rebuilding* a **Running** (en verde).
4. En la pestaña **Overview** (sección *Connection information*), deja abierta esa pantalla para copiar estos **5 datos**:
   - **Host:** (ejemplo: `eva-mysql-tuproyecto.b.aivencloud.com`)
   - **Port:** (ejemplo: `19423`)
   - **User:** `avnadmin`
   - **Password:** *(haz clic en el ícono de copiar contraseña)*
   - **Database Name:** `defaultdb`

---

## Paso 3: Publicar la App Web en Render y obtener tu Link

Tienes dos formas en Render: **Automática (Blueprint en 1 clic)** gracias al archivo `render.yaml`, o **Manual (Web Service)**.

### Opción Rápida (Recomendada — Blueprint con `render.yaml`)
1. Ingresa a [https://dashboard.render.com](https://dashboard.render.com) e inicia sesión con **GitHub**.
2. Arriba a la derecha haz clic en **New +** -> **Blueprint**.
3. Conecta tu repositorio `eva-parking`.
4. Render leerá automáticamente `render.yaml` y te pedirá completar únicamente los **5 datos de Aiven**:
   - `DB_HOST` = el *Host* de Aiven
   - `DB_PORT` = el *Port* de Aiven
   - `DB_USER` = `avnadmin`
   - `DB_PASSWORD` = el *Password* de Aiven
   - `DB_NAME` = `defaultdb`
5. Haz clic en **Apply** / **Deploy**.

### Opción Alternativa (Manual — Web Service)
Si prefieres cargarlo como **New +** -> **Web Service**:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn wsgi:app --preload --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
- **Instance Type:** `Free`
- **Environment Variables:**
  - `FLASK_ENV` = `production`
  - `SECRET_KEY` = *(cualquier frase larga aleatoria)*
  - `AUTO_INIT_DB` = `true`
  - `DB_SSL` = `auto`
  - `DB_HOST` = *(Host de Aiven)*
  - `DB_PORT` = *(Port de Aiven)*
  - `DB_USER` = `avnadmin`
  - `DB_PASSWORD` = *(Password de Aiven)*
  - `DB_NAME` = `defaultdb`

---

## Paso 4: Acceder a tu enlace público permanente

1. En ~2 minutos, Render mostrará el cartel verde **Live** y arriba verás tu enlace público permanente con HTTPS:
   `https://eva-executive-mobility.onrender.com` *(o el subdominio asignado)*.
2. **Ábrelo en tu navegador o celular:** en esa primera visita, E.V.A creará automáticamente las 10 tablas en Aiven MySQL y cargará los estacionamientos y usuarios de prueba (`admin@eva.com`, `carlos.dueno@eva.com`, `juan.conductor@eva.com` con contraseña `eva1234`).
3. **Tip para el plan gratuito (Modo Reposo):**
   - En el plan gratuito, Render pone el servidor en reposo si pasan **15 minutos sin ninguna visita**. La primera persona que entre después de ese reposo esperará unos **30 segundos** mientras despierta; luego vuela al instante.
   - Si quieres que **nunca se duerma** (respuesta instantánea 24/7), crea un monitor gratuito en [https://uptimerobot.com](https://uptimerobot.com) o [https://cron-job.org](https://cron-job.org) apuntando a tu enlace `https://...onrender.com` cada **10 minutos**.
