-- ============================================================================
-- E.V.A (Estacionamiento Virtual Automatizado)
-- Script DML de Datos de Ejemplo para Demo en Vivo (TP5 - UNSTA 2026)
-- Contraseña común de todas las cuentas de prueba: eva1234
-- ============================================================================

USE eva_parking;

-- 1. Usuarios (hash pbkdf2:sha256 correspondiente a 'eva1234')
INSERT INTO usuarios (id, nombre, email, password_hash, rol, saldo_billetera, activo) VALUES
(1, 'Administrador General EVA', 'admin@eva.com', 'pbkdf2:sha256:600000$yZP5m0jZFrKykpiW$add38fb5ccd5a84c1d40ed4dfc2326ed55b7282ebbeb192fc32b02d7bb5e982a', 'ADMIN', 0.00, 1),
(2, 'Carlos Mendoza', 'carlos.dueno@eva.com', 'pbkdf2:sha256:600000$yZP5m0jZFrKykpiW$add38fb5ccd5a84c1d40ed4dfc2326ed55b7282ebbeb192fc32b02d7bb5e982a', 'PROPIETARIO', 18500.00, 1),
(3, 'Laura Santillán', 'laura.duena@eva.com', 'pbkdf2:sha256:600000$yZP5m0jZFrKykpiW$add38fb5ccd5a84c1d40ed4dfc2326ed55b7282ebbeb192fc32b02d7bb5e982a', 'PROPIETARIO', 12200.00, 1),
(4, 'Marcos Villagra', 'marcos.yb@eva.com', 'pbkdf2:sha256:600000$yZP5m0jZFrKykpiW$add38fb5ccd5a84c1d40ed4dfc2326ed55b7282ebbeb192fc32b02d7bb5e982a', 'PROPIETARIO', 6400.00, 1),
(5, 'Juan Pérez', 'juan.conductor@eva.com', 'pbkdf2:sha256:600000$yZP5m0jZFrKykpiW$add38fb5ccd5a84c1d40ed4dfc2326ed55b7282ebbeb192fc32b02d7bb5e982a', 'USUARIO', 15000.00, 1),
(6, 'Sofía Gómez', 'sofia.conductora@eva.com', 'pbkdf2:sha256:600000$yZP5m0jZFrKykpiW$add38fb5ccd5a84c1d40ed4dfc2326ed55b7282ebbeb192fc32b02d7bb5e982a', 'USUARIO', 500.00, 1),
(7, 'Martín Romano', 'martin.conductor@eva.com', 'pbkdf2:sha256:600000$yZP5m0jZFrKykpiW$add38fb5ccd5a84c1d40ed4dfc2326ed55b7282ebbeb192fc32b02d7bb5e982a', 'USUARIO', 9800.00, 1);

-- 2. Tipos de Vehículo
INSERT INTO tipos_vehiculo (id, nombre, icono, descripcion, activo) VALUES
(1, 'Auto', 'car', 'Automóvil sedán, hatchback o coupé estándar', 1),
(2, 'Moto', 'motorcycle', 'Motocicleta o scooter de cualquier cilindrada', 1),
(3, 'Camioneta', 'truck', 'Pick-up, SUV grande o 4x4', 1),
(4, 'Utilitario', 'van', 'Furgón liviano o vehículo comercial', 1);

-- 3. Vehículos de los Conductores
INSERT INTO vehiculos (id, usuario_id, tipo_vehiculo_id, patente, descripcion, activo) VALUES
(1, 5, 1, 'AF420TK', 'Toyota Corolla Blanco', 1),
(2, 5, 2, 'A159BXZ', 'Honda XR 150 Negra', 1),
(3, 6, 3, 'AG881MN', 'Volkswagen Amarok Gris', 1),
(4, 7, 1, 'AE309LP', 'Peugeot 208 Azul', 1);

-- 4. Estacionamientos Afiliados (San Miguel de Tucumán y Yerba Buena)
INSERT INTO estacionamientos (id, propietario_id, nombre, direccion, ciudad, latitud, longitud, cantidad_plazas, horario_texto, techado, activo) VALUES
(1, 2, 'Parking Central Plaza', '25 de Mayo 340', 'San Miguel de Tucumán', -26.8281400, -65.2039200, 12, '24 Horas', 1, 1),
(2, 3, 'Estacionamiento Campus UNSTA', '9 de Julio 165', 'San Miguel de Tucumán', -26.8329500, -65.2062400, 10, 'Lun a Sáb 07:00 - 23:00', 1, 1),
(3, 4, 'Solar Parking Yerba Buena', 'Av. Aconquija 1750', 'Yerba Buena', -26.8142300, -65.2934100, 8, '24 Horas', 0, 1);

-- 5. Plazas de los 3 Estacionamientos
-- Estacionamiento 1 (12 plazas: P-02, P-05 y P-09 ocupadas en tiempo real)
INSERT INTO plazas (id, estacionamiento_id, numero, codigo, ocupada, activa) VALUES
(1, 1, 1, 'P-01', 0, 1),
(2, 1, 2, 'P-02', 1, 1),
(3, 1, 3, 'P-03', 0, 1),
(4, 1, 4, 'P-04', 0, 1),
(5, 1, 5, 'P-05', 1, 1),
(6, 1, 6, 'P-06', 0, 1),
(7, 1, 7, 'P-07', 0, 1),
(8, 1, 8, 'P-08', 0, 1),
(9, 1, 9, 'P-09', 1, 1),
(10, 1, 10, 'P-10', 0, 1),
(11, 1, 11, 'P-11', 0, 1),
(12, 1, 12, 'P-12', 0, 1),
-- Estacionamiento 2 (10 plazas: P-01 ocupada en tiempo real)
(13, 2, 1, 'P-01', 1, 1),
(14, 2, 2, 'P-02', 0, 1),
(15, 2, 3, 'P-03', 0, 1),
(16, 2, 4, 'P-04', 0, 1),
(17, 2, 5, 'P-05', 0, 1),
(18, 2, 6, 'P-06', 0, 1),
(19, 2, 7, 'P-07', 0, 1),
(20, 2, 8, 'P-08', 0, 1),
(21, 2, 9, 'P-09', 0, 1),
(22, 2, 10, 'P-10', 0, 1),
-- Estacionamiento 3 (8 plazas libres)
(23, 3, 1, 'P-01', 0, 1),
(24, 3, 2, 'P-02', 0, 1),
(25, 3, 3, 'P-03', 0, 1),
(26, 3, 4, 'P-04', 0, 1),
(27, 3, 5, 'P-05', 0, 1),
(28, 3, 6, 'P-06', 0, 1),
(29, 3, 7, 'P-07', 0, 1),
(30, 3, 8, 'P-08', 0, 1);

-- 6. Tarifas por Estacionamiento y Tipo de Vehículo
INSERT INTO tarifas (estacionamiento_id, tipo_vehiculo_id, precio_hora, precio_estadia_fija) VALUES
-- Parking Central Plaza
(1, 1, 1800.00, 9500.00),
(1, 2, 900.00, 4500.00),
(1, 3, 2500.00, 13000.00),
(1, 4, 2800.00, 14500.00),
-- Estacionamiento Campus UNSTA
(2, 1, 1500.00, 8000.00),
(2, 2, 750.00, 3800.00),
(2, 3, 2200.00, 11500.00),
-- Solar Parking Yerba Buena
(3, 1, 1600.00, 8500.00),
(3, 2, 800.00, 4000.00),
(3, 3, 2300.00, 12000.00),
(3, 4, 2600.00, 13500.00);

-- 7. Estadías Históricas (Finalizadas) y Estadías Activas (en Tiempo Real)
INSERT INTO estadias (
    id, estacionamiento_id, plaza_id, usuario_id, vehiculo_id, tipo_vehiculo_id,
    patente_snapshot, nombre_cliente_snapshot, modalidad, tarifa_aplicada,
    fecha_ingreso, fecha_salida, minutos_transcurridos, monto_total, origen, estado
) VALUES
-- Estadías finalizadas (con tickets y reseñas)
(1, 2, 14, 5, 1, 1, 'AF420TK', 'Juan Pérez', 'HORA', 1500.00,
    DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_ADD(DATE_SUB(NOW(), INTERVAL 2 DAY), INTERVAL 90 MINUTE),
    90, 2250.00, 'APP_USUARIO', 'FINALIZADA'),
(2, 1, 3, 7, 4, 1, 'AE309LP', 'Martín Romano', 'ESTADIA_FIJA', 9500.00,
    DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 DAY), INTERVAL 320 MINUTE),
    320, 9500.00, 'APP_USUARIO', 'FINALIZADA'),
(3, 3, 23, 5, 2, 2, 'A159BXZ', 'Juan Pérez', 'HORA', 800.00,
    DATE_SUB(NOW(), INTERVAL 18 HOUR), DATE_ADD(DATE_SUB(NOW(), INTERVAL 18 HOUR), INTERVAL 45 MINUTE),
    45, 800.00, 'APP_USUARIO', 'FINALIZADA'),

-- Estadías ACTIVAS en este instante (para lucir el cronómetro y cálculo dinámico en vivo)
-- Juan Pérez estacionado hace 78 minutos en P-02 de Parking Central Plaza (superó 1h -> tarifa proporcional subiendo en vivo)
(4, 1, 2, 5, 1, 1, 'AF420TK', 'Juan Pérez', 'HORA', 1800.00,
    DATE_SUB(NOW(), INTERVAL 78 MINUTE), NULL, NULL, NULL, 'APP_USUARIO', 'ACTIVA'),
-- Martín Romano estacionado hace 25 minutos en P-05 de Parking Central Plaza
(5, 1, 5, 7, 4, 1, 'AE309LP', 'Martín Romano', 'HORA', 1800.00,
    DATE_SUB(NOW(), INTERVAL 25 MINUTE), NULL, NULL, NULL, 'APP_USUARIO', 'ACTIVA'),
-- Cliente presencial ingresado manualmente por el Propietario en P-09 de Parking Central Plaza (Estadía Fija)
(6, 1, 9, NULL, NULL, 3, 'AD774QW', 'Cliente Mostrador', 'ESTADIA_FIJA', 13000.00,
    DATE_SUB(NOW(), INTERVAL 110 MINUTE), NULL, NULL, NULL, 'MOSTRADOR_PROPIETARIO', 'ACTIVA'),
-- Cliente presencial en P-01 de Estacionamiento Campus UNSTA
(7, 2, 13, NULL, NULL, 2, 'A092KLM', 'Alumno Visitante', 'HORA', 750.00,
    DATE_SUB(NOW(), INTERVAL 38 MINUTE), NULL, NULL, NULL, 'MOSTRADOR_PROPIETARIO', 'ACTIVA');

-- 8. Movimientos de Billetera Virtual
INSERT INTO movimientos_billetera (usuario_id, estadia_id, tipo, monto, saldo_posterior, descripcion, creado_en) VALUES
(5, NULL, 'RECARGA', 18050.00, 18050.00, 'Recarga inicial en Billetera Virtual EVA', DATE_SUB(NOW(), INTERVAL 3 DAY)),
(5, 1, 'PAGO_ESTADIA', -2250.00, 15800.00, 'Pago estadía #1 en Estacionamiento Campus UNSTA (P-02)', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(3, 1, 'ACREDITACION_PROPIETARIO', 2250.00, 12200.00, 'Cobro estadía #1 patente AF420TK (P-02)', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(7, NULL, 'RECARGA', 19300.00, 19300.00, 'Recarga en Billetera Virtual EVA', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(7, 2, 'PAGO_ESTADIA', -9500.00, 9800.00, 'Pago estadía fija #2 en Parking Central Plaza (P-03)', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(2, 2, 'ACREDITACION_PROPIETARIO', 9500.00, 18500.00, 'Cobro estadía fija #2 patente AE309LP (P-03)', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(5, 3, 'PAGO_ESTADIA', -800.00, 15000.00, 'Pago estadía #3 en Solar Parking Yerba Buena (P-01)', DATE_SUB(NOW(), INTERVAL 18 HOUR)),
(4, 3, 'ACREDITACION_PROPIETARIO', 800.00, 6400.00, 'Cobro estadía #3 patente A159BXZ (P-01)', DATE_SUB(NOW(), INTERVAL 18 HOUR)),
(6, NULL, 'RECARGA', 500.00, 500.00, 'Saldo inicial de prueba', DATE_SUB(NOW(), INTERVAL 1 DAY));

-- 9. Comprobantes / Tickets Emitidos
INSERT INTO comprobantes (estadia_id, numero_ticket, metodo_pago, monto_pagado, emitido_en) VALUES
(1, 'EVA-2026-00001', 'BILLETERA_VIRTUAL', 2250.00, DATE_SUB(NOW(), INTERVAL 2 DAY)),
(2, 'EVA-2026-00002', 'BILLETERA_VIRTUAL', 9500.00, DATE_SUB(NOW(), INTERVAL 1 DAY)),
(3, 'EVA-2026-00003', 'BILLETERA_VIRTUAL', 800.00, DATE_SUB(NOW(), INTERVAL 18 HOUR));

-- 10. Reseñas Verificadas
INSERT INTO resenas (estadia_id, usuario_id, estacionamiento_id, estrellas, comentario, creado_en) VALUES
(1, 5, 2, 5, 'Excelente ubicación a metros de la facultad, techado y muy rápido el cobro con la billetera.', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(2, 7, 1, 5, 'Plazas amplias y atención impecable en pleno centro. Muy práctico ver los lugares verdes antes de ir.', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(3, 5, 3, 4, 'Muy cómodo para estacionar la moto sobre Av. Aconquija, acceso súper ágil.', DATE_SUB(NOW(), INTERVAL 17 HOUR));
