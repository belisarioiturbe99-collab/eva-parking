/* ==========================================================================
   E.V.A — EXECUTIVE MOBILITY
   Lógica de Capa de Presentación: Validaciones, Mapa, QR Móvil y Tiempo Real
   ========================================================================== */

const EVA = (() => {
    const state = {
        user: null,
        currentView: 'explorer',
        vehicleTypes: [],
        myVehicles: [],
        myActiveStays: [],
        parkings: [],
        openParkingDetail: null,
        selectedSpotForCheckin: null,
        ownerData: null,
        networkInfo: null,
        map: null,
        mapMarkers: [],
        selectedReviewStars: 5,
    };

    const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    const PLATE_RE = /^[A-Z0-9]{5,10}$/;

    /* -------------------- Utilidades Generales -------------------- */
    function esc(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function fmtMoney(num) {
        const val = Number(num || 0);
        return '$' + val.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function fmtDuration(totalSeconds) {
        const sec = Math.max(0, Math.floor(Number(totalSeconds || 0)));
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
    }

    function renderPlateBadge(plate) {
        return `
            <span class="mercosur-plate">
                <span class="mercosur-plate-top">REPÚBLICA ARGENTINA</span>
                <span class="mercosur-plate-num">${esc(plate)}</span>
            </span>
        `;
    }

    function computeDynamicAmount(modalidad, tarifaBase, totalSeconds) {
        const sec = Math.max(0, Math.floor(Number(totalSeconds || 0)));
        const mins = sec > 0 ? Math.max(1, Math.ceil(sec / 60)) : 1;
        const rate = Number(tarifaBase || 0);
        if (modalidad === 'ESTADIA_FIJA') {
            return rate;
        }
        if (mins <= 60) {
            return rate;
        }
        const extra = ((mins - 60) / 60) * rate;
        return Math.round((rate + extra) * 100) / 100;
    }

    function toast(msg, type = 'info') {
        const box = document.getElementById('toast-container');
        if (!box) return;
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = msg;
        box.appendChild(el);
        setTimeout(() => el.remove(), 4200);
    }

    function clearErrors(formEl) {
        if (!formEl) return;
        formEl.querySelectorAll('.form-control.invalid').forEach(i => i.classList.remove('invalid'));
        formEl.querySelectorAll('.field-error').forEach(e => { e.textContent = ''; });
    }

    function setFieldError(inputId, errId, message) {
        const input = inputId ? document.getElementById(inputId) : null;
        const err = errId ? document.getElementById(errId) : null;
        if (input) input.classList.add('invalid');
        if (err) err.textContent = message;
    }

    async function api(path, options = {}) {
        const opts = {
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            ...options,
        };
        if (opts.body && typeof opts.body === 'object') {
            opts.body = JSON.stringify(opts.body);
        }
        const resp = await fetch(path, opts);
        const data = await resp.json().catch(() => ({ ok: false, error: 'Respuesta inválida del servidor.' }));

        const dbBanner = document.getElementById('db-alert-banner');
        if (data.code === 'DATABASE_UNAVAILABLE') {
            if (dbBanner) {
                dbBanner.style.display = 'block';
                dbBanner.innerHTML = `<strong>Conexión MySQL (XAMPP) pendiente:</strong> ${esc(data.error)}`;
            }
        } else if (dbBanner && resp.ok) {
            dbBanner.style.display = 'none';
        }

        if (!resp.ok || !data.ok) {
            const err = new Error(data.error || 'Ocurrió un error al procesar la solicitud.');
            err.code = data.code || 'ERROR';
            err.details = data.details || {};
            err.status = resp.status;
            throw err;
        }
        return data;
    }

    /* -------------------- Modales, QR Móvil y Navegación -------------------- */
    function openModal(id) {
        const el = document.getElementById(id);
        if (el) el.classList.add('open');
    }

    function closeModal(id) {
        const el = document.getElementById(id);
        if (el) el.classList.remove('open');
        if (id === 'modal-parking-detail') {
            state.openParkingDetail = null;
            state.selectedSpotForCheckin = null;
        }
    }

    async function openDeviceAccessModal() {
        try {
            if (!state.networkInfo) {
                state.networkInfo = await api('/api/network-info');
            }
        } catch (_) {
            state.networkInfo = {
                lan_url: window.location.origin,
                local_url: window.location.origin,
            };
        }

        const currentOrigin = window.location.origin;
        const isPublicTunnel = !currentOrigin.includes('127.0.0.1') && !currentOrigin.includes('localhost') && !currentOrigin.startsWith('http://192.168.') && !currentOrigin.startsWith('http://10.');
        const shareUrl = isPublicTunnel ? currentOrigin : (state.networkInfo?.lan_url || currentOrigin);
        const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=190x190&margin=8&data=${encodeURIComponent(shareUrl)}`;

        const body = document.getElementById('device-access-body');
        body.innerHTML = `
            <div style="text-align:center; margin-bottom:1.1rem;">
                <div class="qr-frame">
                    <img src="${qrApiUrl}" alt="QR Acceso Móvil EVA" width="180" height="180"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div style="display:none; padding:1.5rem; font-size:0.82rem; color:var(--text-muted);">
                        Copia el enlace inferior en el navegador de tu celular.
                    </div>
                    <span style="font-size:0.74rem; font-weight:800; color:var(--gold-700); margin-top:0.45rem;">
                        ESCANEA CON LA CÁMARA DE TU CELULAR
                    </span>
                </div>
            </div>

            <div style="margin-bottom:0.9rem;">
                <div style="font-size:0.78rem; font-weight:800; color:var(--text-muted); margin-bottom:0.35rem;">
                    ${isPublicTunnel ? 'LINK PÚBLICO ACTIVO (CUALQUIER RED 4G / WI-FI):' : 'LINK EN TU RED WI-FI LOCAL (CELULAR Y OTRAS PC):'}
                </div>
                <div class="url-copy-box">
                    <span style="flex:1;">${esc(shareUrl)}</span>
                    <button type="button" class="btn btn-primary btn-sm" onclick="EVA.copyText('${esc(shareUrl)}')">Copiar</button>
                </div>
            </div>

            <div style="background:var(--bg-champagne); border:1px solid rgba(221, 160, 10, 0.38); border-radius:10px; padding:0.85rem; font-size:0.82rem; color:#5c4004;">
                <strong>¿Quieres un link público HTTPS para entrar con 4G/5G fuera de tu Wi-Fi?</strong><br>
                Sin instalar nada en tu Mac, abre otra terminal y ejecuta:<br>
                <code>ssh -R 80:127.0.0.1:${state.networkInfo?.port || 5050} nokey@localhost.run</code><br>
                Te dará al instante un link <code>https://...lhr.life</code> accesible desde cualquier dispositivo.
            </div>
        `;
        openModal('modal-device-access');
    }

    function copyText(txt) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(txt).then(() => toast('Enlace copiado al portapapeles.', 'success'));
        } else {
            toast(`Enlace: ${txt}`);
        }
    }

    function renderNavbar() {
        const tabsEl = document.getElementById('nav-tabs');
        const userEl = document.getElementById('nav-user-area');
        const u = state.user;

        const tabs = [{ id: 'explorer', label: 'Mapa y Locales' }];
        if (u && u.rol === 'USUARIO') {
            const activeBadge = state.myActiveStays.length > 0 ? ` (${state.myActiveStays.length})` : '';
            tabs.push({ id: 'stays', label: `Mis Estadías${activeBadge}` });
            tabs.push({ id: 'vehicles', label: 'Mis Vehículos' });
            tabs.push({ id: 'wallet', label: 'Billetera' });
        } else if (u && u.rol === 'PROPIETARIO') {
            tabs.push({ id: 'owner', label: 'Mi Parking en Vivo' });
            tabs.push({ id: 'wallet', label: 'Ingresos' });
        } else if (u && u.rol === 'ADMIN') {
            tabs.push({ id: 'admin', label: 'Dirección Global' });
        }

        tabsEl.innerHTML = tabs.map(t => `
            <button class="nav-tab ${state.currentView === t.id ? 'active' : ''}"
                    onclick="EVA.switchView('${t.id}')">
                ${esc(t.label)}
            </button>
        `).join('');

        const qrBtn = `
            <button class="device-qr-btn" title="Abrir en Celular u otro dispositivo" onclick="EVA.openDeviceAccessModal()">
                📱 Celular / QR
            </button>
        `;

        if (!u) {
            userEl.innerHTML = `
                ${qrBtn}
                <span class="role-badge VISITANTE">Visitante</span>
                <button class="btn btn-ghost-light btn-sm" onclick="EVA.openAuthModal('login')">Ingresar</button>
                <button class="btn btn-primary btn-sm" onclick="EVA.openAuthModal('register')">Registrarse</button>
            `;
        } else {
            const walletBtn = u.rol !== 'ADMIN'
                ? `<span class="wallet-pill" title="Abrir Billetera Virtual" onclick="EVA.switchView('wallet')">
                       ${fmtMoney(u.saldo_billetera)}
                   </span>`
                : '';
            userEl.innerHTML = `
                ${qrBtn}
                ${walletBtn}
                <span class="role-badge ${esc(u.rol)}">${esc(u.rol)}</span>
                <span class="nav-username">${esc(u.nombre)}</span>
                <button class="btn btn-ghost-light btn-sm" onclick="EVA.handleLogout()">Salir</button>
            `;
        }
    }

    async function switchView(viewId) {
        state.currentView = viewId;
        document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
        const target = document.getElementById(`view-${viewId}`);
        if (target) target.classList.add('active');
        renderNavbar();

        if (viewId === 'explorer') {
            await loadCatalog();
            if (state.map) setTimeout(() => state.map.invalidateSize(), 120);
        } else if (viewId === 'stays') {
            await loadMyStays();
        } else if (viewId === 'vehicles') {
            await loadMyVehicles();
        } else if (viewId === 'wallet') {
            await loadWallet();
        } else if (viewId === 'owner') {
            await loadOwnerDashboard();
        } else if (viewId === 'admin') {
            await loadAdminDashboard();
        }
    }

    /* -------------------- Autenticación (EP2) -------------------- */
    function openAuthModal(tab = 'login') {
        switchAuthTab(tab);
        openModal('modal-auth');
    }

    function switchAuthTab(tab) {
        const loginForm = document.getElementById('login-form');
        const regForm = document.getElementById('register-form');
        const btnLogin = document.getElementById('tab-btn-login');
        const btnReg = document.getElementById('tab-btn-register');
        clearErrors(loginForm);
        clearErrors(regForm);

        if (tab === 'login') {
            loginForm.style.display = 'block';
            regForm.style.display = 'none';
            btnLogin.className = 'btn btn-primary';
            btnReg.className = 'btn btn-outline';
        } else {
            loginForm.style.display = 'none';
            regForm.style.display = 'block';
            btnLogin.className = 'btn btn-outline';
            btnReg.className = 'btn btn-primary';
            toggleOwnerRegisterFields();
        }
    }

    function toggleOwnerRegisterFields() {
        const rol = document.getElementById('reg-rol').value;
        const box = document.getElementById('owner-register-fields');
        box.style.display = rol === 'PROPIETARIO' ? 'block' : 'none';
    }

    function fillDemoLogin(email) {
        document.getElementById('login-email').value = email;
        document.getElementById('login-password').value = 'eva1234';
    }

    async function handleLogin(ev) {
        ev.preventDefault();
        const form = document.getElementById('login-form');
        clearErrors(form);

        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        let valid = true;

        if (!EMAIL_RE.test(email)) {
            setFieldError('login-email', 'err-login-email', 'Ingresa un correo electrónico con formato válido.');
            valid = false;
        }
        if (!password || password.length < 4) {
            setFieldError('login-password', 'err-login-password', 'Ingresa tu contraseña.');
            valid = false;
        }
        if (!valid) return;

        try {
            const res = await api('/api/auth/login', {
                method: 'POST',
                body: { email, password },
            });
            state.user = res.user;
            closeModal('modal-auth');
            toast(res.message, 'success');
            await afterAuthChange();
        } catch (err) {
            setFieldError(null, 'err-login-general', err.message);
        }
    }

    async function handleRegister(ev) {
        ev.preventDefault();
        const form = document.getElementById('register-form');
        clearErrors(form);

        const rol = document.getElementById('reg-rol').value;
        const nombre = document.getElementById('reg-nombre').value.trim();
        const email = document.getElementById('reg-email').value.trim();
        const password = document.getElementById('reg-password').value;

        let valid = true;
        if (nombre.length < 3) {
            setFieldError('reg-nombre', 'err-reg-nombre', 'El nombre debe tener al menos 3 caracteres.');
            valid = false;
        }
        if (!EMAIL_RE.test(email)) {
            setFieldError('reg-email', 'err-reg-email', 'Ingresa un correo electrónico válido (ej: usuario@dominio.com).');
            valid = false;
        }
        if (password.length < 6) {
            setFieldError('reg-password', 'err-reg-password', 'La contraseña debe tener al menos 6 caracteres.');
            valid = false;
        }

        const payload = { rol, nombre, email, password };
        if (rol === 'PROPIETARIO') {
            const estNombre = document.getElementById('reg-est-nombre').value.trim();
            const estDir = document.getElementById('reg-est-dir').value.trim();
            const estCiudad = document.getElementById('reg-est-ciudad').value.trim();
            const estPlazas = parseInt(document.getElementById('reg-est-plazas').value, 10);

            if (estNombre.length < 3) {
                setFieldError('reg-est-nombre', 'err-reg-est-nombre', 'Ingresa el nombre comercial del local (mín. 3 letras).');
                valid = false;
            }
            if (estDir.length < 4) {
                setFieldError('reg-est-dir', 'err-reg-est-dir', 'Ingresa la dirección física del estacionamiento.');
                valid = false;
            }
            if (isNaN(estPlazas) || estPlazas < 1 || estPlazas > 200) {
                setFieldError('reg-est-plazas', 'err-reg-est-plazas', 'Ingresa una cantidad entre 1 y 200 plazas.');
                valid = false;
            }
            payload.nombre_estacionamiento = estNombre;
            payload.direccion_estacionamiento = estDir;
            payload.ciudad_estacionamiento = estCiudad || 'San Miguel de Tucumán';
            payload.cantidad_plazas = estPlazas;
        }

        if (!valid) return;

        try {
            const res = await api('/api/auth/register', { method: 'POST', body: payload });
            state.user = res.user;
            closeModal('modal-auth');
            toast(res.message, 'success');
            await afterAuthChange();
        } catch (err) {
            if (err.code === 'DUPLICATE_EMAIL') {
                setFieldError('reg-email', 'err-reg-email', err.message);
            } else {
                setFieldError(null, 'err-reg-general', err.message);
            }
        }
    }

    async function handleLogout() {
        await api('/api/auth/logout', { method: 'POST' });
        state.user = null;
        state.myVehicles = [];
        state.myActiveStays = [];
        renderGlobalActiveStayBanner();
        toast('Sesión cerrada.');
        await switchView('explorer');
        renderFiltersBar();
    }

    async function refreshSessionUser() {
        try {
            const me = await api('/api/auth/me');
            state.user = me.user;
            if (state.user && state.user.rol === 'USUARIO') {
                const [vehRes, stayRes] = await Promise.all([
                    api('/api/vehicles'),
                    api('/api/stays/my'),
                ]);
                state.myVehicles = vehRes.vehiculos || [];
                state.myActiveStays = (stayRes.activas || []).map(s => ({
                    ...s,
                    _syncedAtMs: Date.now(),
                }));
            } else {
                state.myVehicles = [];
                state.myActiveStays = [];
            }
            renderNavbar();
            renderGlobalActiveStayBanner();
        } catch (_) {
            // Manejado por api()
        }
    }

    async function afterAuthChange() {
        await refreshSessionUser();
        renderFiltersBar();
        if (state.user && state.user.rol === 'PROPIETARIO') {
            await switchView('owner');
        } else if (state.user && state.user.rol === 'ADMIN') {
            await switchView('admin');
        } else {
            await switchView('explorer');
        }
    }

    /* -------------------- Explorador, Hero y Mapa (EP1) -------------------- */
    function renderFiltersBar() {
        const container = document.getElementById('advanced-filters-container');
        if (!container) return;

        if (!state.user) {
            container.innerHTML = `
                <div class="visitor-lock-banner">
                    <span><strong>Modo Visitante:</strong> Explora el mapa, consulta locales y verifica bahías libres en tiempo real. Inicia sesión para desbloquear filtros avanzados por vehículo y tarifa.</span>
                    <button type="button" class="btn btn-dark btn-sm" onclick="EVA.openAuthModal('login')">Desbloquear Filtros</button>
                </div>
            `;
            return;
        }

        const typeOptions = state.vehicleTypes.map(t =>
            `<option value="${t.id}">${esc(t.nombre)}</option>`
        ).join('');

        container.innerHTML = `
            <select id="filter-tipo" class="form-control" onchange="EVA.loadCatalog()">
                <option value="">Todas las categorías</option>
                ${typeOptions}
            </select>
            <input type="number" id="filter-max-precio" class="form-control" style="max-width:195px;"
                   placeholder="Tarifa máx. $/hora" min="1" onchange="EVA.loadCatalog()">
            <label style="display:flex; align-items:center; gap:0.4rem; font-size:0.84rem; font-weight:700; cursor:pointer;">
                <input type="checkbox" id="filter-techado" onchange="EVA.loadCatalog()"> Solo techados
            </label>
            <label style="display:flex; align-items:center; gap:0.4rem; font-size:0.84rem; font-weight:700; cursor:pointer;">
                <input type="checkbox" id="filter-libres" onchange="EVA.loadCatalog()"> Con bahías libres
            </label>
        `;
    }

    function updateHeroMetrics() {
        const elParkings = document.getElementById('hero-stat-parkings');
        const elFree = document.getElementById('hero-stat-free');
        const elMin = document.getElementById('hero-stat-minprice');
        if (!elParkings) return;

        const totalLocales = state.parkings.length;
        const totalLibres = state.parkings.reduce((acc, p) => acc + Number(p.plazas_libres || 0), 0);
        const prices = state.parkings
            .map(p => Number(p.precio_desde_hora || 0))
            .filter(v => v > 0);
        const minPrice = prices.length > 0 ? Math.min(...prices) : 0;

        elParkings.textContent = totalLocales;
        elFree.textContent = totalLibres;
        elMin.textContent = minPrice > 0 ? `$${minPrice.toLocaleString('es-AR')}` : '—';
    }

    function handleSearchSubmit(ev) {
        ev.preventDefault();
        loadCatalog();
    }

    function resetSearchFilters() {
        const s = document.getElementById('filter-search');
        if (s) s.value = '';
        ['filter-tipo', 'filter-max-precio'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        ['filter-techado', 'filter-libres'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.checked = false;
        });
        loadCatalog();
    }

    async function loadCatalog() {
        const params = new URLSearchParams();
        const searchVal = (document.getElementById('filter-search')?.value || '').trim();
        if (searchVal) params.set('search', searchVal);

        if (state.user) {
            const tipo = document.getElementById('filter-tipo')?.value;
            const maxP = document.getElementById('filter-max-precio')?.value;
            const tech = document.getElementById('filter-techado')?.checked;
            const lib = document.getElementById('filter-libres')?.checked;
            if (tipo) params.set('tipo_vehiculo_id', tipo);
            if (maxP) params.set('max_precio_hora', maxP);
            if (tech) params.set('solo_techado', '1');
            if (lib) params.set('solo_disponibles', '1');
        }

        try {
            const data = await api(`/api/parkings?${params.toString()}`);
            state.parkings = data.estacionamientos || [];
            updateHeroMetrics();
            renderParkingCards();
            renderMapMarkers();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function renderParkingCards() {
        const listEl = document.getElementById('parking-list');
        if (!listEl) return;

        if (state.parkings.length === 0) {
            listEl.innerHTML = `
                <div class="card" style="text-align:center; padding:2.2rem;">
                    <h3>Sin estacionamientos coincidentes</h3>
                    <p style="color:var(--text-muted); margin-top:0.35rem;">Prueba con otra zona o restablece los filtros seleccionados.</p>
                </div>
            `;
            return;
        }

        listEl.innerHTML = state.parkings.map(p => {
            const libres = Number(p.plazas_libres || 0);
            const totales = Number(p.plazas_totales || 0);
            const ocupadas = Number(p.plazas_ocupadas || 0);
            const pctFree = totales > 0 ? Math.round((libres / totales) * 100) : 0;
            const barColor = libres > 0 ? '#10b981' : '#ef4444';
            const pillClass = libres > 0 ? 'has-free' : 'full';
            const pillText = libres > 0 ? `${libres} de ${totales} Libres` : `Completo (${ocupadas}/${totales})`;

            const stars = p.promedio_estrellas
                ? `<span class="tag tag-rating">★ ${p.promedio_estrellas} (${p.total_resenas})</span>`
                : `<span class="tag">Nuevo en EVA</span>`;

            const tariffsHtml = (p.tarifas || []).map(t =>
                `<span class="tariff-chip"><strong>${esc(t.tipo_nombre)}:</strong> ${fmtMoney(t.precio_hora)}/h · Fija ${fmtMoney(t.precio_estadia_fija)}</span>`
            ).join('');

            return `
                <article class="parking-card">
                    <div class="parking-card-top">
                        <div>
                            <div class="parking-title">${esc(p.nombre)}</div>
                            <div class="parking-address">${esc(p.direccion)} · ${esc(p.ciudad)}</div>
                        </div>
                        <span class="availability-pill ${pillClass}">${esc(pillText)}</span>
                    </div>

                    <div class="occupancy-bar-track" title="${pctFree}% disponible">
                        <div class="occupancy-bar-fill" style="width:${Math.max(6, pctFree)}%; background:${barColor};"></div>
                    </div>

                    <div class="parking-meta-tags">
                        ${stars}
                        <span class="tag">${p.techado ? 'Cobertura Techada' : 'Aire Libre'}</span>
                        <span class="tag">${esc(p.horario_texto)}</span>
                    </div>

                    <div class="tariff-chips">${tariffsHtml || '<span class="tag">Consultar tarifas</span>'}</div>

                    <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                        <button class="btn btn-outline btn-sm" onclick="EVA.focusParkingOnMap(${p.id})">Centrar en Mapa</button>
                        <button class="btn btn-primary btn-sm" onclick="EVA.openParkingLiveModal(${p.id})">
                            Explorar Plazas en Vivo →
                        </button>
                    </div>
                </article>
            `;
        }).join('');
    }

    function renderMapMarkers() {
        const mapContainer = document.getElementById('parking-map');
        const statusLabel = document.getElementById('map-status-label');
        if (!mapContainer) return;

        // Respaldo esquemático interactivo si no hay internet durante la presentación local
        if (typeof L === 'undefined') {
            if (statusLabel) statusLabel.textContent = 'Mapa Esquemático Local E.V.A (Modo Offline)';
            mapContainer.innerHTML = `
                <div style="padding:1.35rem; height:100%; display:flex; flex-direction:column; justify-content:center; gap:0.8rem; background:#181b22; color:#fff;">
                    <div style="font-weight:800; color:#f5c227; letter-spacing:0.06em;">RED E.V.A EXECUTIVE MOBILITY</div>
                    ${state.parkings.map(p => `
                        <div onclick="EVA.openParkingLiveModal(${p.id})"
                             style="background:#111317; padding:0.85rem 1rem; border-radius:12px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; border:1.5px solid ${p.plazas_libres > 0 ? '#10b981' : '#ef4444'};">
                            <div>
                                <strong style="color:#fff;">${esc(p.nombre)}</strong>
                                <div style="font-size:0.8rem; color:#94a3b8;">${esc(p.direccion)} (${esc(p.ciudad)})</div>
                            </div>
                            <strong style="color:${p.plazas_libres > 0 ? '#34d399' : '#f87171'};">
                                ${p.plazas_libres}/${p.plazas_totales} libres
                            </strong>
                        </div>
                    `).join('')}
                </div>
            `;
            return;
        }

        if (!state.map) {
            state.map = L.map('parking-map').setView([-26.8285, -65.2150], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap',
            }).addTo(state.map);
        }

        state.mapMarkers.forEach(m => state.map.removeLayer(m));
        state.mapMarkers = [];

        const bounds = [];
        state.parkings.forEach(p => {
            const lat = Number(p.latitud);
            const lng = Number(p.longitud);
            if (isNaN(lat) || isNaN(lng)) return;

            const dotColor = p.plazas_libres > 0 ? '#10b981' : '#ef4444';
            const borderColor = p.plazas_libres > 0 ? '#dda00a' : '#ef4444';
            const desde = p.precio_desde_hora ? fmtMoney(p.precio_desde_hora) + '/h' : 'Ver';

            const icon = L.divIcon({
                className: 'eva-map-pin',
                html: `
                    <div style="background:#12151b; color:#fff; font-weight:800; font-size:12px; padding:5px 10px; border-radius:999px; border:2px solid ${borderColor}; box-shadow:0 6px 14px rgba(12,14,18,0.38); white-space:nowrap; display:inline-flex; align-items:center; gap:6px;">
                        <span style="width:8px; height:8px; border-radius:50%; background:${dotColor}; display:inline-block;"></span>
                        <span style="color:#f5c227;">${esc(desde)}</span>
                        <span>· ${p.plazas_libres} libres</span>
                    </div>
                `,
                iconSize: [140, 30],
                iconAnchor: [70, 15],
            });

            const marker = L.marker([lat, lng], { icon }).addTo(state.map);
            marker.bindPopup(`
                <div style="min-width:205px; font-family:'Plus Jakarta Sans', sans-serif;">
                    <strong style="font-size:14px; color:#111317;">${esc(p.nombre)}</strong><br>
                    <span style="font-size:12px; color:#4b5563;">${esc(p.direccion)}</span><br>
                    <span style="font-size:12px; font-weight:800; color:${p.plazas_libres > 0 ? '#059669' : '#dc2626'};">
                        ${p.plazas_libres} de ${p.plazas_totales} plazas libres
                    </span><br>
                    <button onclick="EVA.openParkingLiveModal(${p.id})"
                            style="margin-top:8px; width:100%; background:linear-gradient(135deg,#f6c428,#d99b08); color:#111317; border:none; border-radius:8px; padding:6px 10px; cursor:pointer; font-weight:800;">
                        Ver Plazas en Tiempo Real
                    </button>
                </div>
            `);
            marker.pId = p.id;
            state.mapMarkers.push(marker);
            bounds.push([lat, lng]);
        });

        if (bounds.length > 0) {
            state.map.fitBounds(bounds, { padding: [45, 45], maxZoom: 15 });
        }
    }

    function focusParkingOnMap(parkingId) {
        const p = state.parkings.find(x => x.id === parkingId);
        if (!p || !state.map) return;
        state.map.setView([Number(p.latitud), Number(p.longitud)], 16);
        const mk = state.mapMarkers.find(m => m.pId === parkingId);
        if (mk) mk.openPopup();
    }

    /* -------------------- Modal Grilla de Plazas + Check-in (EP3 + EP4) -------------------- */
    async function openParkingLiveModal(parkingId, preserveSpotId = null) {
        try {
            const res = await api(`/api/parkings/${parkingId}`);
            const park = res.estacionamiento;
            park._syncedAtMs = Date.now();
            state.openParkingDetail = park;

            if (preserveSpotId) {
                const found = park.plazas.find(s => s.id === preserveSpotId && !s.ocupada);
                state.selectedSpotForCheckin = found || null;
            } else {
                state.selectedSpotForCheckin = null;
            }

            renderParkingDetailModal();
            openModal('modal-parking-detail');
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function selectSpotForCheckin(spotId) {
        const park = state.openParkingDetail;
        if (!park) return;

        if (!state.user) {
            closeModal('modal-parking-detail');
            toast('Inicia sesión o crea tu cuenta para ocupar una plaza.');
            openAuthModal('login');
            return;
        }

        if (state.user.rol === 'PROPIETARIO' && park.propietario_id === state.user.id) {
            openManualDeskModal(spotId);
            return;
        }

        if (state.user.rol !== 'USUARIO') {
            toast('Inicia sesión con un perfil de Conductor para estacionar un vehículo.');
            return;
        }

        const spot = park.plazas.find(s => s.id === spotId && !s.ocupada);
        if (!spot) return;
        state.selectedSpotForCheckin = spot;
        renderParkingDetailModal();
        const panel = document.getElementById('checkin-action-panel');
        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function renderParkingDetailModal() {
        const park = state.openParkingDetail;
        if (!park) return;

        document.getElementById('detail-modal-title').textContent = park.nombre;
        document.getElementById('detail-modal-subtitle').textContent =
            `${park.direccion}, ${park.ciudad} · ${park.horario_texto} · ${park.techado ? 'Techado' : 'Aire Libre'} · Ocupación actual: ${park.plazas_ocupadas}/${park.plazas_totales} (${park.porcentaje_ocupacion}%)`;

        const body = document.getElementById('detail-modal-body');

        const tariffsBadges = (park.tarifas || []).map(t =>
            `<span class="tariff-chip"><strong>${esc(t.tipo_nombre)}:</strong> Hora ${fmtMoney(t.precio_hora)} | Estadía Fija ${fmtMoney(t.precio_estadia_fija)}</span>`
        ).join('');

        const gridHtml = (park.plazas || []).map(sp => {
            if (!sp.ocupada) {
                const isSelected = state.selectedSpotForCheckin && state.selectedSpotForCheckin.id === sp.id;
                return `
                    <div class="spot-tile free ${isSelected ? 'selected-spot' : ''}" onclick="EVA.selectSpotForCheckin(${sp.id})">
                        <div>
                            <div class="spot-header">
                                <span class="spot-code">${esc(sp.codigo)}</span>
                                <span class="spot-badge">DISPONIBLE</span>
                            </div>
                            <div class="spot-body">Bahía habilitada para ingreso inmediato</div>
                        </div>
                        <div class="spot-action-hint">
                            ${isSelected ? '◆ Bahía seleccionada' : 'Estacionar aquí'}
                        </div>
                    </div>
                `;
            }

            const ownBtn = sp.es_mi_estadia
                ? `<button class="btn btn-danger btn-sm" style="margin-top:0.55rem; width:100%;"
                           onclick="EVA.handleCheckoutStay(${sp.estadia_id})">
                       Finalizar y Pagar
                   </button>`
                : '';

            return `
                <div class="spot-tile busy ${sp.es_mi_estadia ? 'own-stay' : ''}">
                    <div>
                        <div class="spot-header">
                            <span class="spot-code">${esc(sp.codigo)}</span>
                            <span class="spot-badge">OCUPADO</span>
                        </div>
                        <div class="spot-body">
                            ${renderPlateBadge(sp.patente_snapshot)}
                            <div><strong>${esc(sp.tipo_vehiculo_nombre || 'Vehículo')}</strong> · ${sp.modalidad === 'HORA' ? 'Por Hora' : 'Estadía Fija'}</div>
                        </div>
                    </div>
                    <div>
                        <div class="spot-live-metrics"
                             data-live-stay="1"
                             data-base-sec="${sp.segundos_transcurridos}"
                             data-sync-ms="${park._syncedAtMs}"
                             data-modalidad="${sp.modalidad}"
                             data-tarifa="${sp.tarifa_aplicada}">
                            <span class="spot-timer">${fmtDuration(sp.segundos_transcurridos)}</span>
                            <span class="spot-amount">${fmtMoney(sp.monto_acumulado)}</span>
                        </div>
                        ${ownBtn}
                    </div>
                </div>
            `;
        }).join('');

        let checkinPanelHtml = '';
        if (state.selectedSpotForCheckin && state.user && state.user.rol === 'USUARIO') {
            const spot = state.selectedSpotForCheckin;
            if (state.myVehicles.length === 0) {
                checkinPanelHtml = `
                    <div id="checkin-action-panel" class="alert-box alert-warning" style="margin-top:1.15rem;">
                        <strong>Registra primero tu vehículo:</strong> Necesitas al menos un vehículo cargado en tu cuenta para estacionar en la bahía <strong>${esc(spot.codigo)}</strong>.
                        <div style="margin-top:0.65rem;">
                            <button class="btn btn-primary btn-sm" onclick="EVA.closeModal('modal-parking-detail'); EVA.switchView('vehicles');">
                                Registrar mi Vehículo Ahora
                            </button>
                        </div>
                    </div>
                `;
            } else {
                const vehOpts = state.myVehicles.map(v => `
                    <option value="${v.id}" data-tipo-id="${v.tipo_vehiculo_id}" ${v.en_estadia_activa ? 'disabled' : ''}>
                        ${esc(v.patente)} — ${esc(v.tipo_nombre)} ${v.descripcion ? '(' + esc(v.descripcion) + ')' : ''} ${v.en_estadia_activa ? '[Ya estacionado]' : ''}
                    </option>
                `).join('');

                checkinPanelHtml = `
                    <div id="checkin-action-panel" class="card" style="margin-top:1.2rem; border:2px solid var(--gold-500); background:var(--bg-champagne);">
                        <h4 style="margin-bottom:0.7rem; color:#111317;">
                            ◆ Confirmar Ingreso en Bahía ${esc(spot.codigo)} (${esc(park.nombre)})
                        </h4>
                        <form id="checkin-form" onsubmit="EVA.handleStartUserStay(event)" novalidate>
                            <div class="form-grid">
                                <div class="form-group">
                                    <label for="chk-vehiculo">Vehículo a Estacionar *</label>
                                    <select id="chk-vehiculo" class="form-control" onchange="EVA.updateCheckinPreview()">
                                        ${vehOpts}
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="chk-modalidad">Modalidad Tarifaria *</label>
                                    <select id="chk-modalidad" class="form-control" onchange="EVA.updateCheckinPreview()">
                                        <option value="HORA">Por Hora (1h mín. + fracción por minuto)</option>
                                        <option value="ESTADIA_FIJA">Estadía Fija Ejecutiva</option>
                                    </select>
                                </div>
                            </div>
                            <div id="checkin-price-preview" style="font-size:0.88rem; margin-bottom:0.8rem;"></div>
                            <div id="checkin-error-area" class="field-error" style="margin-bottom:0.65rem;"></div>
                            <div style="display:flex; gap:0.6rem; flex-wrap:wrap;">
                                <button type="submit" class="btn btn-primary">Confirmar e Iniciar Cronómetro</button>
                                <button type="button" class="btn btn-outline" onclick="EVA.cancelSpotSelection()">Cancelar</button>
                            </div>
                        </form>
                    </div>
                `;
            }
        }

        const reviewsHtml = (park.resenas || []).length === 0
            ? '<p style="font-size:0.85rem; color:var(--text-muted);">Este local aún no registra reseñas de usuarios.</p>'
            : park.resenas.map(r => `
                <div style="padding:0.7rem 0; border-bottom:1px solid var(--border); font-size:0.86rem;">
                    <div style="display:flex; justify-content:space-between;">
                        <strong>${esc(r.usuario_nombre)}</strong>
                        <span style="color:var(--gold-600); font-weight:800;">${'★'.repeat(r.estrellas)}${'☆'.repeat(5 - r.estrellas)}</span>
                    </div>
                    <div style="color:var(--text-muted); margin-top:0.2rem;">${esc(r.comentario || 'Experiencia verificada sin comentario.')}</div>
                </div>
            `).join('');

        body.innerHTML = `
            <div class="tariff-chips" style="margin-bottom:0.9rem;">${tariffsBadges}</div>
            <div class="legend-bar">
                <div class="legend-items">
                    <span><i class="legend-dot free"></i>VERDE: Bahía disponible (toca para ocupar)</span>
                    <span><i class="legend-dot busy"></i>ROJO: Ocupada (tiempo y monto en vivo)</span>
                </div>
            </div>
            <div class="restaurant-grid">${gridHtml}</div>
            ${checkinPanelHtml}
            <div style="margin-top:1.45rem; padding-top:1.05rem; border-top:1px solid var(--border);">
                <h4 style="margin-bottom:0.55rem;">Reseñas Verificadas de Conductores</h4>
                ${reviewsHtml}
            </div>
        `;

        if (document.getElementById('chk-vehiculo')) {
            updateCheckinPreview();
        }
    }

    function cancelSpotSelection() {
        state.selectedSpotForCheckin = null;
        renderParkingDetailModal();
    }

    function updateCheckinPreview() {
        const park = state.openParkingDetail;
        const sel = document.getElementById('chk-vehiculo');
        const mod = document.getElementById('chk-modalidad')?.value || 'HORA';
        const prev = document.getElementById('checkin-price-preview');
        if (!park || !sel || !prev) return;

        const opt = sel.options[sel.selectedIndex];
        if (!opt) return;
        const tipoId = Number(opt.getAttribute('data-tipo-id'));
        const tf = (park.tarifas || []).find(t => t.tipo_vehiculo_id === tipoId);

        if (!tf) {
            prev.innerHTML = `<span style="color:#dc2626; font-weight:700;">Este estacionamiento no tiene tarifa habilitada para ese tipo de vehículo.</span>`;
            return;
        }

        const req = mod === 'HORA' ? tf.precio_hora : tf.precio_estadia_fija;
        const saldo = Number(state.user?.saldo_billetera || 0);
        const alcanza = saldo >= req;

        prev.innerHTML = `
            Tarifa base: <strong>${fmtMoney(req)}</strong> ${mod === 'HORA' ? '/ hora' : '(Estadía Fija)'} ·
            Saldo en tu Billetera: <strong style="color:${alcanza ? '#059669' : '#dc2626'};">${fmtMoney(saldo)}</strong>
            ${!alcanza ? ` — <a href="#" onclick="event.preventDefault(); EVA.quickTopupAndRetryCheckin(${Math.max(100, Math.ceil(req - saldo))});" style="color:#875c04; font-weight:800; text-decoration:underline;">Acreditar diferencia (${fmtMoney(Math.max(100, Math.ceil(req - saldo)))}) en 1 toque</a>` : ''}
        `;
    }

    async function quickTopupAndRetryCheckin(amount) {
        try {
            const res = await api('/api/wallet/deposit', {
                method: 'POST',
                body: { monto: amount, metodo: 'Recarga Rápida Check-in' },
            });
            state.user.saldo_billetera = res.saldo_billetera;
            renderNavbar();
            updateCheckinPreview();
            const errEl = document.getElementById('checkin-error-area');
            if (errEl) errEl.textContent = '';
            toast(`Se acreditaron ${fmtMoney(amount)} en tu Billetera Virtual.`, 'success');
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function handleStartUserStay(ev) {
        ev.preventDefault();
        const park = state.openParkingDetail;
        const spot = state.selectedSpotForCheckin;
        if (!park || !spot) return;

        const vehiculoId = Number(document.getElementById('chk-vehiculo')?.value);
        const modalidad = document.getElementById('chk-modalidad')?.value || 'HORA';
        const errArea = document.getElementById('checkin-error-area');
        if (errArea) errArea.innerHTML = '';

        if (!vehiculoId) {
            if (errArea) errArea.textContent = 'Selecciona un vehículo disponible.';
            return;
        }

        try {
            const res = await api('/api/stays/checkin', {
                method: 'POST',
                body: { plaza_id: spot.id, vehiculo_id: vehiculoId, modalidad },
            });
            toast(res.message, 'success');
            await refreshSessionUser();
            await openParkingLiveModal(park.id);
            await loadCatalog();
        } catch (err) {
            if (err.code === 'INSUFFICIENT_FUNDS' && err.details?.faltante) {
                const topup = Math.max(100, Math.ceil(err.details.faltante));
                if (errArea) {
                    errArea.innerHTML = `
                        ${esc(err.message)}
                        <button type="button" class="btn btn-dark btn-sm" style="margin-left:0.5rem;"
                                onclick="EVA.quickTopupAndRetryCheckin(${topup})">
                            Acreditar ${fmtMoney(topup)} ahora
                        </button>
                    `;
                }
            } else {
                if (errArea) errArea.textContent = err.message;
            }
        }
    }

    /* -------------------- Estadías, Cobro, Ticket y Reseña (EP3/EP4/EP5) -------------------- */
    function renderGlobalActiveStayBanner() {
        const box = document.getElementById('global-active-stay-container');
        if (!box) return;

        if (!state.user || state.user.rol !== 'USUARIO' || state.myActiveStays.length === 0) {
            box.innerHTML = '';
            return;
        }

        box.innerHTML = state.myActiveStays.map(st => `
            <div class="active-stay-banner">
                <div>
                    <div style="font-size:0.74rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:var(--gold-400);">
                        <span class="live-pulse"></span>Telemetría de Estadía en Vivo
                    </div>
                    <div style="font-size:1.22rem; font-weight:800; margin-top:0.2rem;">
                        ${esc(st.estacionamiento_nombre)} · Bahía ${esc(st.plaza_codigo)}
                    </div>
                    <div style="font-size:0.86rem; color:#cbd5e1; margin-top:0.15rem;">
                        ${esc(st.tipo_vehiculo_nombre)} (${esc(st.patente_snapshot)}) ·
                        ${st.modalidad === 'HORA' ? `Por Hora (${fmtMoney(st.tarifa_aplicada)}/h)` : `Estadía Fija (${fmtMoney(st.tarifa_aplicada)})`}
                    </div>
                </div>

                <div style="display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap;"
                     data-live-stay="1"
                     data-base-sec="${st.segundos_transcurridos}"
                     data-sync-ms="${st._syncedAtMs}"
                     data-modalidad="${st.modalidad}"
                     data-tarifa="${st.tarifa_aplicada}">
                    <div>
                        <div style="font-size:0.7rem; color:#94a3b8; font-weight:700;">TIEMPO EN BAHÍA</div>
                        <div class="active-stay-clock spot-timer">${fmtDuration(st.segundos_transcurridos)}</div>
                    </div>
                    <div>
                        <div style="font-size:0.7rem; color:#94a3b8; font-weight:700;">IMPORTE ACUMULADO</div>
                        <div class="active-stay-cost spot-amount">${fmtMoney(st.monto_acumulado)}</div>
                    </div>
                    <button class="btn btn-primary" onclick="EVA.handleCheckoutStay(${st.id})">
                        Finalizar Estadía y Pagar
                    </button>
                </div>
            </div>
        `).join('');
    }

    async function handleCheckoutStay(estadiaId, cobroMostrador = false) {
        try {
            const res = await api(`/api/stays/${estadiaId}/checkout`, {
                method: 'POST',
                body: { cobro_mostrador: cobroMostrador },
            });
            toast(res.message, 'success');
            await refreshSessionUser();

            if (state.openParkingDetail) {
                await openParkingLiveModal(state.openParkingDetail.id);
            }
            if (state.currentView === 'stays') await loadMyStays();
            if (state.currentView === 'owner') await loadOwnerDashboard();
            if (state.currentView === 'explorer') await loadCatalog();

            showPostCheckoutModal(res.comprobante);
        } catch (err) {
            if (err.code === 'INSUFFICIENT_FUNDS' && err.details?.faltante && state.user?.rol === 'USUARIO') {
                const topup = Math.max(100, Math.ceil(err.details.faltante));
                showInsufficientCheckoutModal(estadiaId, err.message, topup);
            } else {
                toast(err.message, 'error');
            }
        }
    }

    function showInsufficientCheckoutModal(estadiaId, message, topupAmount) {
        const body = document.getElementById('post-checkout-body');
        body.innerHTML = `
            <div class="alert-box alert-danger">
                <strong>Fondos insuficientes para liberar la bahía:</strong><br>
                ${esc(message)}
            </div>
            <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:1rem;">
                La plaza permanece en estado <strong>Ocupado (Rojo)</strong> hasta procesar el pago. Acredita la diferencia exacta y libera tu vehículo en un toque:
            </p>
            <div style="display:flex; gap:0.65rem; flex-wrap:wrap;">
                <button class="btn btn-primary" onclick="EVA.topupAndCheckoutNow(${estadiaId}, ${topupAmount})">
                    Acreditar ${fmtMoney(topupAmount)} y Pagar Ahora
                </button>
                <button class="btn btn-outline" onclick="EVA.closeModal('modal-post-checkout'); EVA.switchView('wallet');">
                    Abrir Billetera Virtual
                </button>
            </div>
        `;
        openModal('modal-post-checkout');
    }

    async function topupAndCheckoutNow(estadiaId, amount) {
        try {
            await api('/api/wallet/deposit', {
                method: 'POST',
                body: { monto: amount, metodo: 'Recarga Instantánea al Salir' },
            });
            await handleCheckoutStay(estadiaId, false);
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function showPostCheckoutModal(comp) {
        state.selectedReviewStars = 5;
        const canReview = state.user && state.user.rol === 'USUARIO' && comp.usuario_id === state.user.id && !comp.resena_id;

        const reviewFormHtml = canReview ? `
            <div style="margin-top:1.25rem; padding-top:1rem; border-top:1px solid var(--border);">
                <h4 style="margin-bottom:0.35rem;">Califica tu experiencia en ${esc(comp.estacionamiento_nombre)}</h4>
                <p style="font-size:0.82rem; color:var(--text-muted); margin-bottom:0.5rem;">Tu reseña queda asociada a esta estadía verificada.</p>
                <div class="star-picker" id="checkout-star-picker">
                    ${[1, 2, 3, 4, 5].map(n => `<span class="selected" onclick="EVA.pickReviewStar(${n})">★</span>`).join('')}
                </div>
                <div class="form-group" style="margin-top:0.6rem;">
                    <textarea id="review-comment" class="form-control" rows="2" maxlength="300"
                              placeholder="Escribe un comentario breve (opcional)..."></textarea>
                </div>
                <button class="btn btn-dark btn-sm" onclick="EVA.submitStayReview(${comp.estadia_id})">
                    Publicar Calificación
                </button>
            </div>
        ` : '';

        const body = document.getElementById('post-checkout-body');
        body.innerHTML = `
            <div style="background:#f0fdf7; border:1px solid #6ee7b7; color:#065f46; padding:0.95rem; border-radius:12px; margin-bottom:1rem;">
                <strong>✓ Pago aprobado:</strong> Bahía <strong>${esc(comp.plaza_codigo)}</strong> liberada a <strong>Verde</strong>.
                Comprobante <strong>${esc(comp.numero_ticket)}</strong> emitido.
            </div>
            <div style="font-size:0.9rem; display:grid; gap:0.38rem; margin-bottom:1.1rem;">
                <div><strong>Estacionamiento:</strong> ${esc(comp.estacionamiento_nombre)}</div>
                <div><strong>Vehículo:</strong> ${esc(comp.tipo_vehiculo_nombre)} (${esc(comp.patente_snapshot)})</div>
                <div><strong>Tiempo computado:</strong> ${comp.minutos_transcurridos} min</div>
                <div><strong>Medio de pago:</strong> ${comp.metodo_pago === 'BILLETERA_VIRTUAL' ? 'Débito Automático Billetera Virtual EVA' : 'Efectivo en Mostrador'}</div>
                <div style="font-size:1.18rem; margin-top:0.3rem;"><strong>Total Abonado: <span style="color:#059669;">${fmtMoney(comp.monto_pagado)}</span></strong></div>
            </div>
            <div style="display:flex; gap:0.6rem; flex-wrap:wrap;">
                <a href="/ticket/${comp.estadia_id}" target="_blank" class="btn btn-primary">
                    Abrir / Imprimir Ticket Oficial
                </a>
                <button class="btn btn-outline" onclick="EVA.closeModal('modal-post-checkout')">Cerrar</button>
            </div>
            ${reviewFormHtml}
        `;
        openModal('modal-post-checkout');
    }

    function pickReviewStar(n) {
        state.selectedReviewStars = n;
        const spans = document.querySelectorAll('#checkout-star-picker span');
        spans.forEach((sp, idx) => {
            sp.classList.toggle('selected', idx < n);
        });
    }

    async function submitStayReview(estadiaId) {
        const comentario = (document.getElementById('review-comment')?.value || '').trim();
        try {
            const res = await api(`/api/stays/${estadiaId}/review`, {
                method: 'POST',
                body: { estrellas: state.selectedReviewStars, comentario },
            });
            toast(res.message, 'success');
            closeModal('modal-post-checkout');
            if (state.currentView === 'stays') await loadMyStays();
            if (state.currentView === 'explorer') await loadCatalog();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function openQuickReviewFromHistory(estadiaId, parkingName) {
        state.selectedReviewStars = 5;
        const body = document.getElementById('post-checkout-body');
        body.innerHTML = `
            <h4 style="margin-bottom:0.4rem;">Calificar estadía en ${esc(parkingName)}</h4>
            <div class="star-picker" id="checkout-star-picker" style="margin-bottom:0.65rem;">
                ${[1, 2, 3, 4, 5].map(n => `<span class="selected" onclick="EVA.pickReviewStar(${n})">★</span>`).join('')}
            </div>
            <div class="form-group">
                <textarea id="review-comment" class="form-control" rows="3" maxlength="300"
                          placeholder="Comparte tu experiencia con el estacionamiento..."></textarea>
            </div>
            <div style="display:flex; gap:0.6rem;">
                <button class="btn btn-primary" onclick="EVA.submitStayReview(${estadiaId})">Guardar Reseña</button>
                <button class="btn btn-outline" onclick="EVA.closeModal('modal-post-checkout')">Cancelar</button>
            </div>
        `;
        openModal('modal-post-checkout');
    }

    async function loadMyStays() {
        try {
            const res = await api('/api/stays/my');
            state.myActiveStays = (res.activas || []).map(s => ({ ...s, _syncedAtMs: Date.now() }));
            renderGlobalActiveStayBanner();
            renderNavbar();

            const activeEl = document.getElementById('my-active-stays-list');
            if (state.myActiveStays.length === 0) {
                activeEl.innerHTML = `
                    <div class="card" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                        <div>
                            <strong>No posees estadías activas en curso.</strong>
                            <div style="font-size:0.86rem; color:var(--text-muted);">Selecciona un estacionamiento en el mapa y elige una bahía libre en verde para comenzar.</div>
                        </div>
                        <button class="btn btn-primary btn-sm" onclick="EVA.switchView('explorer')">Explorar Mapa</button>
                    </div>
                `;
            } else {
                activeEl.innerHTML = '';
            }

            const hist = res.historial || [];
            const wrap = document.getElementById('my-history-table-wrap');
            if (hist.length === 0) {
                wrap.innerHTML = '<p style="color:var(--text-muted); font-size:0.88rem;">Aún no registras estadías finalizadas.</p>';
                return;
            }

            wrap.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Ticket</th>
                            <th>Estacionamiento / Bahía</th>
                            <th>Vehículo</th>
                            <th>Ingreso / Salida</th>
                            <th>Duración</th>
                            <th>Total</th>
                            <th>Calificación</th>
                            <th>Comprobante</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${hist.map(h => `
                            <tr>
                                <td><code>${esc(h.numero_ticket || '-')}</code></td>
                                <td><strong>${esc(h.estacionamiento_nombre)}</strong><br><span style="color:var(--text-muted);">Bahía ${esc(h.plaza_codigo)}</span></td>
                                <td>${esc(h.tipo_vehiculo_nombre)} · <strong>${esc(h.patente_snapshot)}</strong></td>
                                <td style="font-size:0.8rem;">${esc(h.fecha_ingreso)}<br>${esc(h.fecha_salida)}</td>
                                <td>${h.minutos_transcurridos} min</td>
                                <td><strong>${fmtMoney(h.monto_total)}</strong></td>
                                <td>
                                    ${h.resena_id
                                        ? `<span style="color:var(--gold-600); font-weight:800;">${'★'.repeat(h.resena_estrellas)}</span>`
                                        : `<button class="btn btn-outline btn-sm" onclick="EVA.openQuickReviewFromHistory(${h.id}, '${esc(h.estacionamiento_nombre)}')">Calificar ★</button>`
                                    }
                                </td>
                                <td>
                                    <a href="/ticket/${h.id}" target="_blank" class="btn btn-outline btn-sm">Ticket PDF</a>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    /* -------------------- Mis Vehículos (EP2-HU3) -------------------- */
    async function loadMyVehicles() {
        const sel = document.getElementById('veh-tipo');
        if (sel) {
            sel.innerHTML = state.vehicleTypes.map(t =>
                `<option value="${t.id}">${esc(t.nombre)}</option>`
            ).join('');
        }

        try {
            const res = await api('/api/vehicles');
            state.myVehicles = res.vehiculos || [];
            const box = document.getElementById('my-vehicles-list');
            if (state.myVehicles.length === 0) {
                box.innerHTML = '<p style="color:var(--text-muted); font-size:0.9rem;">No tienes vehículos registrados. Añade tu primera patente en el panel izquierdo.</p>';
                return;
            }

            box.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Placa / Patente</th>
                            <th>Categoría</th>
                            <th>Descripción</th>
                            <th>Estado</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${state.myVehicles.map(v => `
                            <tr>
                                <td>${renderPlateBadge(v.patente)}</td>
                                <td><strong>${esc(v.tipo_nombre)}</strong></td>
                                <td>${esc(v.descripcion || '-')}</td>
                                <td>
                                    ${v.en_estadia_activa
                                        ? '<span class="role-badge PROPIETARIO">En Bahía Activa</span>'
                                        : '<span class="role-badge USUARIO">Habilitado</span>'}
                                </td>
                                <td>
                                    <button class="btn btn-outline btn-sm" ${v.en_estadia_activa ? 'disabled' : ''}
                                            onclick="EVA.handleDeleteVehicle(${v.id})">
                                        Quitar
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function handleCreateVehicle(ev) {
        ev.preventDefault();
        const form = document.getElementById('vehicle-form');
        clearErrors(form);

        const tipoId = document.getElementById('veh-tipo').value;
        const rawPlate = document.getElementById('veh-patente').value.replace(/[\s\-]+/g, '').toUpperCase();
        const desc = document.getElementById('veh-desc').value.trim();

        let valid = true;
        if (!tipoId) {
            setFieldError('veh-tipo', 'err-veh-tipo', 'Selecciona una categoría.');
            valid = false;
        }
        if (!PLATE_RE.test(rawPlate)) {
            setFieldError('veh-patente', 'err-veh-patente', 'Formato inválido: ingresa entre 5 y 10 letras/números sin símbolos (ej: AF420TK).');
            valid = false;
        }
        if (!valid) return;

        try {
            const res = await api('/api/vehicles', {
                method: 'POST',
                body: { tipo_vehiculo_id: Number(tipoId), patente: rawPlate, descripcion: desc },
            });
            document.getElementById('veh-patente').value = '';
            document.getElementById('veh-desc').value = '';
            toast(res.message, 'success');
            await loadMyVehicles();
        } catch (err) {
            setFieldError('veh-patente', 'err-veh-patente', err.message);
        }
    }

    async function handleDeleteVehicle(vehicleId) {
        try {
            const res = await api(`/api/vehicles/${vehicleId}`, { method: 'DELETE' });
            toast(res.message, 'success');
            await loadMyVehicles();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    /* -------------------- Billetera Virtual Ejecutiva (EP4) -------------------- */
    function setQuickDeposit(amount) {
        const input = document.getElementById('wallet-amount');
        if (input) input.value = amount;
    }

    async function loadWallet() {
        try {
            const res = await api('/api/wallet');
            if (state.user) state.user.saldo_billetera = res.saldo_billetera;
            renderNavbar();

            document.getElementById('wallet-balance-big').textContent = fmtMoney(res.saldo_billetera);
            const holderName = document.getElementById('wallet-holder-name');
            const holderRole = document.getElementById('wallet-holder-role');
            if (holderName && state.user) holderName.textContent = state.user.nombre.toUpperCase();
            if (holderRole && state.user) holderRole.textContent = state.user.rol === 'PROPIETARIO' ? 'CUENTA RECAUDADORA' : 'EXECUTIVE MEMBER';

            const depPanel = document.getElementById('wallet-deposit-panel');
            if (depPanel) {
                depPanel.style.display = state.user?.rol === 'PROPIETARIO' ? 'none' : 'block';
            }

            const movs = res.movimientos || [];
            const wrap = document.getElementById('wallet-movements-wrap');
            if (movs.length === 0) {
                wrap.innerHTML = '<p style="color:var(--text-muted); font-size:0.88rem;">Sin movimientos registrados en la cuenta.</p>';
                return;
            }

            wrap.innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Concepto</th>
                            <th>Importe</th>
                            <th>Saldo Posterior</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${movs.map(m => {
                            const pos = Number(m.monto) >= 0;
                            return `
                                <tr>
                                    <td style="font-size:0.8rem;">${esc(m.creado_en)}</td>
                                    <td>${esc(m.descripcion)}</td>
                                    <td style="font-weight:800; color:${pos ? '#059669' : '#dc2626'};">
                                        ${pos ? '+' : ''}${fmtMoney(m.monto)}
                                    </td>
                                    <td><strong>${fmtMoney(m.saldo_posterior)}</strong></td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            `;
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function handleWalletDeposit(ev) {
        ev.preventDefault();
        const form = document.getElementById('wallet-form');
        clearErrors(form);

        const raw = document.getElementById('wallet-amount').value;
        const monto = parseFloat(raw);
        const metodo = document.getElementById('wallet-method').value;

        if (isNaN(monto) || monto < 100 || monto > 500000) {
            setFieldError('wallet-amount', 'err-wallet-amount', 'Ingresa un importe válido entre $100.00 y $500,000.00.');
            return;
        }

        try {
            const res = await api('/api/wallet/deposit', {
                method: 'POST',
                body: { monto, metodo },
            });
            document.getElementById('wallet-amount').value = '';
            toast(res.message, 'success');
            await loadWallet();
        } catch (err) {
            setFieldError('wallet-amount', 'err-wallet-amount', err.message);
        }
    }

    /* -------------------- Panel del Propietario -------------------- */
    async function loadOwnerDashboard() {
        try {
            const data = await api('/api/owner/dashboard');
            data._syncedAtMs = Date.now();
            state.ownerData = data;
            renderOwnerDashboard();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function renderOwnerDashboard() {
        const d = state.ownerData;
        if (!d || !d.tiene_estacionamiento) return;

        const est = d.estacionamiento;
        const r = d.resumen;
        document.getElementById('owner-parking-title').textContent = `Consola Operativa — ${est.nombre}`;

        document.getElementById('owner-kpis').innerHTML = `
            <div class="kpi-card">
                <div class="kpi-label">Ocupación Actual</div>
                <div class="kpi-value">${r.plazas_ocupadas} / ${r.plazas_totales}</div>
                <div class="kpi-sub">${r.porcentaje_ocupacion}% ocupado · ${r.plazas_libres} bahías verdes</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Devengado en Curso (En Vivo)</div>
                <div class="kpi-value" id="owner-live-ongoing-kpi" style="color:var(--gold-700);">${fmtMoney(r.monto_en_curso_vivo)}</div>
                <div class="kpi-sub">${r.estadias_activas} vehículos en bahía ahora</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Facturado Hoy</div>
                <div class="kpi-value" style="color:#059669;">${fmtMoney(r.ingresos_hoy)}</div>
                <div class="kpi-sub">Estadías cerradas en la fecha</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Recaudación Histórica</div>
                <div class="kpi-value">${fmtMoney(r.ingresos_totales)}</div>
                <div class="kpi-sub">${r.estadias_finalizadas} operaciones completadas</div>
            </div>
        `;

        // Grilla Estilo Restaurante Ejecutiva
        document.getElementById('owner-spots-grid').innerHTML = (d.plazas || []).map(sp => {
            if (!sp.ocupada) {
                return `
                    <div class="spot-tile free" onclick="EVA.openManualDeskModal(${sp.id})">
                        <div>
                            <div class="spot-header">
                                <span class="spot-code">${esc(sp.codigo)}</span>
                                <span class="spot-badge">DESOCUPADO</span>
                            </div>
                            <div class="spot-body">Bahía libre y operativa</div>
                        </div>
                        <div class="spot-action-hint">+ Ingreso Mostrador</div>
                    </div>
                `;
            }

            const isDesk = sp.origen === 'MOSTRADOR_PROPIETARIO';
            return `
                <div class="spot-tile busy">
                    <div>
                        <div class="spot-header">
                            <span class="spot-code">${esc(sp.codigo)}</span>
                            <span class="spot-badge">OCUPADO</span>
                        </div>
                        <div class="spot-body">
                            ${renderPlateBadge(sp.patente_snapshot)}
                            <div><strong>${esc(sp.tipo_vehiculo_nombre)}</strong> · ${sp.modalidad === 'HORA' ? 'Hora' : 'Fija'}</div>
                            <div style="font-size:0.75rem; opacity:0.85;">
                                ${esc(sp.nombre_cliente_snapshot || 'Conductor')} · ${isDesk ? 'Mostrador' : 'App EVA'}
                            </div>
                        </div>
                    </div>
                    <div>
                        <div class="spot-live-metrics"
                             data-live-stay="1"
                             data-owner-live="1"
                             data-base-sec="${sp.segundos_transcurridos}"
                             data-sync-ms="${d._syncedAtMs}"
                             data-modalidad="${sp.modalidad}"
                             data-tarifa="${sp.tarifa_aplicada}">
                            <span class="spot-timer">${fmtDuration(sp.segundos_transcurridos)}</span>
                            <span class="spot-amount">${fmtMoney(sp.monto_acumulado)}</span>
                        </div>
                        <button class="btn btn-danger btn-sm" style="margin-top:0.55rem; width:100%;"
                                onclick="EVA.handleCheckoutStay(${sp.estadia_id}, ${isDesk ? 'true' : 'false'})">
                            ${isDesk ? 'Cobrar Efectivo y Liberar' : 'Debitar Billetera y Liberar'}
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Formulario configuración local
        document.getElementById('own-nombre').value = est.nombre || '';
        document.getElementById('own-plazas').value = est.cantidad_plazas || 10;
        document.getElementById('own-direccion').value = est.direccion || '';
        document.getElementById('own-ciudad').value = est.ciudad || '';
        document.getElementById('own-lat').value = est.latitud;
        document.getElementById('own-lng').value = est.longitud;
        document.getElementById('own-horario').value = est.horario_texto || '';
        document.getElementById('own-techado').checked = Boolean(est.techado);

        // Matriz de tarifas
        const tariffMap = {};
        (d.tarifas || []).forEach(t => { tariffMap[t.tipo_vehiculo_id] = t; });

        document.getElementById('owner-tariffs-table-wrap').innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Activa</th>
                        <th>Categoría</th>
                        <th>Precio / Hora ($)</th>
                        <th>Estadía Fija ($)</th>
                    </tr>
                </thead>
                <tbody>
                    ${(d.tipos_vehiculo || []).map(tv => {
                        const tf = tariffMap[tv.id];
                        return `
                            <tr data-tariff-row="${tv.id}">
                                <td><input type="checkbox" class="tf-enabled" ${tf ? 'checked' : ''}></td>
                                <td><strong>${esc(tv.nombre)}</strong></td>
                                <td>
                                    <input type="number" step="0.01" min="1" class="form-control tf-hora"
                                           value="${tf ? tf.precio_hora : 1500}" style="max-width:130px;">
                                </td>
                                <td>
                                    <input type="number" step="0.01" min="1" class="form-control tf-fija"
                                           value="${tf ? tf.precio_estadia_fija : 8000}" style="max-width:130px;">
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;

        // Actividad reciente
        const recent = d.actividad_reciente || [];
        document.getElementById('owner-recent-stays-wrap').innerHTML = recent.length === 0
            ? '<p style="color:var(--text-muted); font-size:0.88rem;">Sin movimientos registrados.</p>'
            : `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Bahía</th>
                            <th>Patente / Categoría</th>
                            <th>Cliente / Canal</th>
                            <th>Modalidad</th>
                            <th>Ingreso</th>
                            <th>Estado</th>
                            <th>Importe</th>
                            <th>Ticket</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${recent.map(st => `
                            <tr>
                                <td><strong>${esc(st.plaza_codigo)}</strong></td>
                                <td><strong>${esc(st.patente_snapshot)}</strong> · ${esc(st.tipo_vehiculo_nombre)}</td>
                                <td>${esc(st.nombre_cliente_snapshot || '-')} <span class="tag">${st.origen === 'APP_USUARIO' ? 'App EVA' : 'Mostrador'}</span></td>
                                <td>${st.modalidad === 'HORA' ? 'Por Hora' : 'Estadía Fija'}</td>
                                <td style="font-size:0.8rem;">${esc(st.fecha_ingreso)}</td>
                                <td>
                                    <span class="role-badge ${st.estado === 'ACTIVA' ? 'PROPIETARIO' : 'USUARIO'}">
                                        ${esc(st.estado)}
                                    </span>
                                </td>
                                <td><strong>${st.monto_total !== null ? fmtMoney(st.monto_total) : 'En curso'}</strong></td>
                                <td>
                                    ${st.numero_ticket
                                        ? `<a href="/ticket/${st.id}" target="_blank" class="btn btn-outline btn-sm">${esc(st.numero_ticket)}</a>`
                                        : '-'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
    }

    async function handleSaveOwnerParking(ev) {
        ev.preventDefault();
        const form = document.getElementById('owner-config-form');
        clearErrors(form);

        const nombre = document.getElementById('own-nombre').value.trim();
        const cantidadPlazas = parseInt(document.getElementById('own-plazas').value, 10);
        const direccion = document.getElementById('own-direccion').value.trim();
        const ciudad = document.getElementById('own-ciudad').value.trim();
        const latitud = parseFloat(document.getElementById('own-lat').value);
        const longitud = parseFloat(document.getElementById('own-lng').value);
        const horarioTexto = document.getElementById('own-horario').value.trim();
        const techado = document.getElementById('own-techado').checked;

        let valid = true;
        if (nombre.length < 3) {
            setFieldError('own-nombre', 'err-own-nombre', 'El nombre debe tener al menos 3 caracteres.');
            valid = false;
        }
        if (isNaN(cantidadPlazas) || cantidadPlazas < 1 || cantidadPlazas > 200) {
            setFieldError('own-plazas', 'err-own-plazas', 'Ingresa una capacidad válida entre 1 y 200 plazas.');
            valid = false;
        }
        if (direccion.length < 4) {
            setFieldError('own-direccion', 'err-own-direccion', 'Ingresa una dirección válida.');
            valid = false;
        }
        if (!valid) return;

        try {
            const res = await api('/api/owner/parking', {
                method: 'PUT',
                body: {
                    nombre,
                    cantidad_plazas: cantidadPlazas,
                    direccion,
                    ciudad,
                    latitud,
                    longitud,
                    horario_texto: horarioTexto,
                    techado,
                },
            });
            toast(res.message, 'success');
            await loadOwnerDashboard();
        } catch (err) {
            setFieldError('own-plazas', 'err-own-plazas', err.message);
            toast(err.message, 'error');
        }
    }

    async function handleSaveOwnerTariffs(ev) {
        ev.preventDefault();
        const errEl = document.getElementById('err-owner-tariffs');
        if (errEl) errEl.textContent = '';

        const rows = document.querySelectorAll('[data-tariff-row]');
        const tarifas = [];
        let enabledCount = 0;

        for (const r of rows) {
            const tipoId = Number(r.getAttribute('data-tariff-row'));
            const habilitado = r.querySelector('.tf-enabled').checked;
            const pHora = parseFloat(r.querySelector('.tf-hora').value);
            const pFija = parseFloat(r.querySelector('.tf-fija').value);

            if (habilitado) {
                enabledCount++;
                if (isNaN(pHora) || pHora <= 0 || isNaN(pFija) || pFija <= 0) {
                    if (errEl) errEl.textContent = 'Todas las tarifas habilitadas deben tener importes mayores a $0.';
                    return;
                }
            }
            tarifas.push({
                tipo_vehiculo_id: tipoId,
                habilitado,
                precio_hora: pHora || 0,
                precio_estadia_fija: pFija || 0,
            });
        }

        if (enabledCount === 0) {
            if (errEl) errEl.textContent = 'Debes habilitar al menos una categoría de vehículo.';
            return;
        }

        try {
            const res = await api('/api/owner/tariffs', {
                method: 'PUT',
                body: { tarifas },
            });
            toast(res.message, 'success');
            await loadOwnerDashboard();
        } catch (err) {
            if (errEl) errEl.textContent = err.message;
        }
    }

    function openManualDeskModal(spotId) {
        const d = state.ownerData;
        const form = document.getElementById('manual-checkin-form');
        clearErrors(form);
        document.getElementById('manual-plaza-id').value = spotId;
        document.getElementById('manual-patente').value = '';
        document.getElementById('manual-cliente').value = '';

        const tariffs = d?.tarifas || state.openParkingDetail?.tarifas || [];
        const sel = document.getElementById('manual-tipo');
        sel.innerHTML = tariffs.map(t =>
            `<option value="${t.tipo_vehiculo_id}">${esc(t.tipo_nombre)} (Hora: ${fmtMoney(t.precio_hora)} / Fija: ${fmtMoney(t.precio_estadia_fija)})</option>`
        ).join('');

        openModal('modal-manual-checkin');
    }

    async function handleManualDeskCheckin(ev) {
        ev.preventDefault();
        const form = document.getElementById('manual-checkin-form');
        clearErrors(form);

        const plazaId = Number(document.getElementById('manual-plaza-id').value);
        const patente = document.getElementById('manual-patente').value.replace(/[\s\-]+/g, '').toUpperCase();
        const tipoId = Number(document.getElementById('manual-tipo').value);
        const modalidad = document.getElementById('manual-modalidad').value;
        const nombreCliente = document.getElementById('manual-cliente').value.trim();

        if (!PLATE_RE.test(patente)) {
            setFieldError('manual-patente', 'err-manual-patente', 'Ingresa una patente válida de 5 a 10 letras/números.');
            return;
        }

        try {
            const res = await api('/api/owner/manual-checkin', {
                method: 'POST',
                body: {
                    plaza_id: plazaId,
                    patente,
                    tipo_vehiculo_id: tipoId,
                    modalidad,
                    nombre_cliente: nombreCliente || 'Cliente Mostrador',
                },
            });
            closeModal('modal-manual-checkin');
            toast(res.message, 'success');
            if (state.currentView === 'owner') await loadOwnerDashboard();
            if (state.openParkingDetail) await openParkingLiveModal(state.openParkingDetail.id);
        } catch (err) {
            setFieldError(null, 'err-manual-general', err.message);
        }
    }

    /* -------------------- Panel del Administrador Global -------------------- */
    async function loadAdminDashboard() {
        try {
            const data = await api('/api/admin/dashboard');
            const m = data.metricas;

            document.getElementById('admin-kpis').innerHTML = `
                <div class="kpi-card">
                    <div class="kpi-label">Comunidad EVA</div>
                    <div class="kpi-value">${m.total_usuarios}</div>
                    <div class="kpi-sub">${m.total_conductores} conductores · ${m.total_propietarios} propietarios</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Locales Activos</div>
                    <div class="kpi-value">${m.estacionamientos_activos}</div>
                    <div class="kpi-sub">${m.plazas_ocupadas_red} / ${m.plazas_totales_red} bahías ocupadas en red</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Operaciones</div>
                    <div class="kpi-value">${m.estadias_activas} en vivo</div>
                    <div class="kpi-sub">${m.estadias_finalizadas} estadías históricas</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Volumen Transaccionado</div>
                    <div class="kpi-value" style="color:#059669;">${fmtMoney(m.volumen_facturado)}</div>
                    <div class="kpi-sub">Total facturado en la red E.V.A</div>
                </div>
            `;

            document.getElementById('admin-parkings-wrap').innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Estacionamiento</th>
                            <th>Titular (1:1)</th>
                            <th>Ocupación</th>
                            <th>Recaudación</th>
                            <th>Estado</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(data.estacionamientos || []).map(p => `
                            <tr>
                                <td>#${p.id}</td>
                                <td><strong>${esc(p.nombre)}</strong><br><span style="font-size:0.8rem; color:var(--text-muted);">${esc(p.direccion)}, ${esc(p.ciudad)}</span></td>
                                <td>${esc(p.propietario_nombre)}<br><span style="font-size:0.78rem; color:var(--text-muted);">${esc(p.propietario_email)}</span></td>
                                <td>${p.plazas_ocupadas} / ${p.plazas_activas}</td>
                                <td><strong>${fmtMoney(p.ingresos_historicos)}</strong></td>
                                <td>${p.activo ? '<span class="role-badge USUARIO">Operativo</span>' : '<span class="role-badge PROPIETARIO">Pausado</span>'}</td>
                                <td>
                                    <button class="btn btn-outline btn-sm" onclick="EVA.toggleAdminParking(${p.id}, ${!p.activo})">
                                        ${p.activo ? 'Pausar' : 'Habilitar'}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;

            document.getElementById('admin-users-wrap').innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Usuario</th>
                            <th>Rol</th>
                            <th>Saldo Billetera</th>
                            <th>Estado</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(data.usuarios || []).map(u => `
                            <tr>
                                <td><strong>${esc(u.nombre)}</strong><br><span style="font-size:0.78rem; color:var(--text-muted);">${esc(u.email)}</span></td>
                                <td><span class="role-badge ${esc(u.rol)}">${esc(u.rol)}</span></td>
                                <td>${fmtMoney(u.saldo_billetera)}</td>
                                <td>${u.activo ? 'Activo' : 'Suspendido'}</td>
                                <td>
                                    ${u.id === state.user.id ? '-' : `
                                        <button class="btn btn-outline btn-sm" onclick="EVA.toggleAdminUser(${u.id}, ${!u.activo})">
                                            ${u.activo ? 'Suspender' : 'Activar'}
                                        </button>
                                    `}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;

            document.getElementById('admin-vtypes-wrap').innerHTML = `
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Categoría</th>
                            <th>Estado</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(data.tipos_vehiculo || []).map(tv => `
                            <tr>
                                <td><strong>${esc(tv.nombre)}</strong></td>
                                <td>${tv.activo ? 'Activa' : 'Inactiva'}</td>
                                <td>
                                    <button class="btn btn-outline btn-sm" onclick="EVA.toggleAdminVehicleType(${tv.id}, ${!tv.activo})">
                                        ${tv.activo ? 'Desactivar' : 'Activar'}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function toggleAdminUser(userId, activo) {
        try {
            const res = await api(`/api/admin/users/${userId}/status`, { method: 'PATCH', body: { activo } });
            toast(res.message, 'success');
            await loadAdminDashboard();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function toggleAdminParking(parkingId, activo) {
        try {
            const res = await api(`/api/admin/parkings/${parkingId}/status`, { method: 'PATCH', body: { activo } });
            toast(res.message, 'success');
            await loadAdminDashboard();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function handleCreateVehicleType(ev) {
        ev.preventDefault();
        const form = document.getElementById('admin-vtype-form');
        clearErrors(form);
        const nombre = document.getElementById('adm-vt-nombre').value.trim();
        const descripcion = document.getElementById('adm-vt-desc').value.trim();

        if (nombre.length < 2) {
            setFieldError('adm-vt-nombre', 'err-adm-vt-nombre', 'Ingresa al menos 2 caracteres.');
            return;
        }

        try {
            const res = await api('/api/admin/vehicle-types', {
                method: 'POST',
                body: { nombre, descripcion },
            });
            document.getElementById('adm-vt-nombre').value = '';
            document.getElementById('adm-vt-desc').value = '';
            toast(res.message, 'success');
            const vt = await api('/api/vehicle-types');
            state.vehicleTypes = vt.tipos_vehiculo || [];
            await loadAdminDashboard();
        } catch (err) {
            setFieldError('adm-vt-nombre', 'err-adm-vt-nombre', err.message);
        }
    }

    async function toggleAdminVehicleType(typeId, activo) {
        try {
            const res = await api(`/api/admin/vehicle-types/${typeId}/status`, { method: 'PATCH', body: { activo } });
            toast(res.message, 'success');
            const vt = await api('/api/vehicle-types');
            state.vehicleTypes = vt.tipos_vehiculo || [];
            await loadAdminDashboard();
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    /* -------------------- Motor de Relojes en Tiempo Real (1s + Sync 15s) -------------------- */
    function tickLiveClocks() {
        const now = Date.now();
        let ownerLiveSum = 0;
        let hasOwnerNodes = false;

        document.querySelectorAll('[data-live-stay="1"]').forEach(node => {
            const baseSec = Number(node.getAttribute('data-base-sec') || 0);
            const syncMs = Number(node.getAttribute('data-sync-ms') || now);
            const modalidad = node.getAttribute('data-modalidad') || 'HORA';
            const tarifa = Number(node.getAttribute('data-tarifa') || 0);

            const elapsedSec = baseSec + Math.max(0, Math.floor((now - syncMs) / 1000));
            const dynamicAmount = computeDynamicAmount(modalidad, tarifa, elapsedSec);

            const timerEl = node.querySelector('.spot-timer');
            const amountEl = node.querySelector('.spot-amount');
            if (timerEl) timerEl.textContent = fmtDuration(elapsedSec);
            if (amountEl) amountEl.textContent = fmtMoney(dynamicAmount);

            if (node.getAttribute('data-owner-live') === '1') {
                hasOwnerNodes = true;
                ownerLiveSum += dynamicAmount;
            }
        });

        if (hasOwnerNodes) {
            const kpiEl = document.getElementById('owner-live-ongoing-kpi');
            if (kpiEl) kpiEl.textContent = fmtMoney(ownerLiveSum);
        }
    }

    async function periodicBackgroundSync() {
        try {
            if (state.openParkingDetail) {
                const selectedId = state.selectedSpotForCheckin?.id || null;
                await openParkingLiveModal(state.openParkingDetail.id, selectedId);
            } else if (state.currentView === 'owner' && state.user?.rol === 'PROPIETARIO') {
                await loadOwnerDashboard();
            } else if (state.user?.rol === 'USUARIO' && state.myActiveStays.length > 0) {
                await refreshSessionUser();
            }
        } catch (_) {
            // Silencioso en sincronización periódica
        }
    }

    /* -------------------- Inicialización -------------------- */
    async function init() {
        renderNavbar();
        try {
            const vtRes = await api('/api/vehicle-types');
            state.vehicleTypes = vtRes.tipos_vehiculo || [];
        } catch (_) {
            state.vehicleTypes = [];
        }

        await refreshSessionUser();
        renderFiltersBar();
        await loadCatalog();

        setInterval(tickLiveClocks, 1000);
        setInterval(periodicBackgroundSync, 15000);
    }

    document.addEventListener('DOMContentLoaded', init);

    return {
        switchView,
        openModal,
        closeModal,
        openDeviceAccessModal,
        copyText,
        openAuthModal,
        switchAuthTab,
        toggleOwnerRegisterFields,
        fillDemoLogin,
        handleLogin,
        handleRegister,
        handleLogout,
        handleSearchSubmit,
        resetSearchFilters,
        loadCatalog,
        focusParkingOnMap,
        openParkingLiveModal,
        selectSpotForCheckin,
        cancelSpotSelection,
        updateCheckinPreview,
        quickTopupAndRetryCheckin,
        handleStartUserStay,
        handleCheckoutStay,
        topupAndCheckoutNow,
        pickReviewStar,
        submitStayReview,
        openQuickReviewFromHistory,
        loadMyStays,
        loadMyVehicles,
        handleCreateVehicle,
        handleDeleteVehicle,
        setQuickDeposit,
        loadWallet,
        handleWalletDeposit,
        loadOwnerDashboard,
        handleSaveOwnerParking,
        handleSaveOwnerTariffs,
        openManualDeskModal,
        handleManualDeskCheckin,
        loadAdminDashboard,
        toggleAdminUser,
        toggleAdminParking,
        handleCreateVehicleType,
        toggleAdminVehicleType,
    };
})();
