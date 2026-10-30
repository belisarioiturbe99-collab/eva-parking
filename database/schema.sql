-- ============================================================================
-- E.V.A (Estacionamiento Virtual Automatizado)
-- Script DDL de Creación de Base de Datos Relacional (MySQL / MariaDB - XAMPP)
-- Arquitectura en 3 Capas - Taller Integrador II (UNSTA 2026)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS eva_parking
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE eva_parking;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS resenas;
DROP TABLE IF EXISTS comprobantes;
DROP TABLE IF EXISTS movimientos_billetera;
DROP TABLE IF EXISTS estadias;
DROP TABLE IF EXISTS tarifas;
DROP TABLE IF EXISTS plazas;
DROP TABLE IF EXISTS estacionamientos;
DROP TABLE IF EXISTS vehiculos;
DROP TABLE IF EXISTS tipos_vehiculo;
DROP TABLE IF EXISTS usuarios;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Tabla de Usuarios (Roles autenticados: ADMIN, PROPIETARIO, USUARIO)
-- El rol Visitante navega sin sesión ni registro en esta tabla.
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('ADMIN', 'PROPIETARIO', 'USUARIO') NOT NULL DEFAULT 'USUARIO',
    saldo_billetera DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Catálogo Global de Tipos de Vehículo
CREATE TABLE tipos_vehiculo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    icono VARCHAR(30) NOT NULL DEFAULT 'car',
    descripcion VARCHAR(150) DEFAULT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB;

-- 3. Vehículos Registrados por Usuarios Conductores
CREATE TABLE vehiculos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo_vehiculo_id INT NOT NULL,
    patente VARCHAR(15) NOT NULL UNIQUE,
    descripcion VARCHAR(100) DEFAULT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vehiculo_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_vehiculo_tipo
        FOREIGN KEY (tipo_vehiculo_id) REFERENCES tipos_vehiculo(id)
) ENGINE=InnoDB;

-- 4. Estacionamientos (Relación 1 a 1 con el usuario PROPIETARIO)
CREATE TABLE estacionamientos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    propietario_id INT NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    ciudad VARCHAR(80) NOT NULL DEFAULT 'San Miguel de Tucumán',
    latitud DECIMAL(10, 7) NOT NULL DEFAULT -26.8303700,
    longitud DECIMAL(10, 7) NOT NULL DEFAULT -65.2038100,
    cantidad_plazas INT NOT NULL DEFAULT 10,
    horario_texto VARCHAR(80) NOT NULL DEFAULT '24 Horas',
    techado TINYINT(1) NOT NULL DEFAULT 1,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_estacionamiento_propietario
        FOREIGN KEY (propietario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. Plazas Individuales (Estilo Restaurante: ocupada=0 Verde / ocupada=1 Rojo)
CREATE TABLE plazas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estacionamiento_id INT NOT NULL,
    numero INT NOT NULL,
    codigo VARCHAR(15) NOT NULL,
    ocupada TINYINT(1) NOT NULL DEFAULT 0,
    activa TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uk_plaza_est_numero (estacionamiento_id, numero),
    UNIQUE KEY uk_plaza_est_codigo (estacionamiento_id, codigo),
    CONSTRAINT fk_plaza_estacionamiento
        FOREIGN KEY (estacionamiento_id) REFERENCES estacionamientos(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6. Matriz de Tarifas por Estacionamiento y Tipo de Vehículo
CREATE TABLE tarifas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estacionamiento_id INT NOT NULL,
    tipo_vehiculo_id INT NOT NULL,
    precio_hora DECIMAL(10, 2) NOT NULL,
    precio_estadia_fija DECIMAL(10, 2) NOT NULL,
    UNIQUE KEY uk_tarifa_est_tipo (estacionamiento_id, tipo_vehiculo_id),
    CONSTRAINT fk_tarifa_estacionamiento
        FOREIGN KEY (estacionamiento_id) REFERENCES estacionamientos(id) ON DELETE CASCADE,
    CONSTRAINT fk_tarifa_tipo_vehiculo
        FOREIGN KEY (tipo_vehiculo_id) REFERENCES tipos_vehiculo(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 7. Estadías (Control de Tiempos en Vivo y Montos Acumulados)
CREATE TABLE estadias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estacionamiento_id INT NOT NULL,
    plaza_id INT NOT NULL,
    usuario_id INT DEFAULT NULL,
    vehiculo_id INT DEFAULT NULL,
    tipo_vehiculo_id INT NOT NULL,
    patente_snapshot VARCHAR(15) NOT NULL,
    nombre_cliente_snapshot VARCHAR(100) DEFAULT NULL,
    modalidad ENUM('HORA', 'ESTADIA_FIJA') NOT NULL DEFAULT 'HORA',
    tarifa_aplicada DECIMAL(10, 2) NOT NULL,
    fecha_ingreso DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_salida DATETIME DEFAULT NULL,
    minutos_transcurridos INT DEFAULT NULL,
    monto_total DECIMAL(10, 2) DEFAULT NULL,
    origen ENUM('APP_USUARIO', 'MOSTRADOR_PROPIETARIO') NOT NULL DEFAULT 'APP_USUARIO',
    estado ENUM('ACTIVA', 'FINALIZADA') NOT NULL DEFAULT 'ACTIVA',
    INDEX idx_estadia_est_estado (estacionamiento_id, estado),
    INDEX idx_estadia_plaza_estado (plaza_id, estado),
    INDEX idx_estadia_usuario_estado (usuario_id, estado),
    CONSTRAINT fk_estadia_estacionamiento
        FOREIGN KEY (estacionamiento_id) REFERENCES estacionamientos(id) ON DELETE CASCADE,
    CONSTRAINT fk_estadia_plaza
        FOREIGN KEY (plaza_id) REFERENCES plazas(id),
    CONSTRAINT fk_estadia_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT fk_estadia_vehiculo
        FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id) ON DELETE SET NULL,
    CONSTRAINT fk_estadia_tipo_vehiculo
        FOREIGN KEY (tipo_vehiculo_id) REFERENCES tipos_vehiculo(id)
) ENGINE=InnoDB;

-- 8. Movimientos de Billetera Virtual (Recargas, Débitos y Acreditaciones)
CREATE TABLE movimientos_billetera (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    estadia_id INT DEFAULT NULL,
    tipo ENUM('RECARGA', 'PAGO_ESTADIA', 'ACREDITACION_PROPIETARIO') NOT NULL,
    monto DECIMAL(12, 2) NOT NULL,
    saldo_posterior DECIMAL(12, 2) NOT NULL,
    descripcion VARCHAR(200) NOT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mov_usuario_fecha (usuario_id, creado_en),
    CONSTRAINT fk_movimiento_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_movimiento_estadia
        FOREIGN KEY (estadia_id) REFERENCES estadias(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 9. Comprobantes / Tickets Digitales Imprimibles (EP4-HU2)
CREATE TABLE comprobantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estadia_id INT NOT NULL UNIQUE,
    numero_ticket VARCHAR(30) NOT NULL UNIQUE,
    metodo_pago ENUM('BILLETERA_VIRTUAL', 'EFECTIVO_MOSTRADOR') NOT NULL DEFAULT 'BILLETERA_VIRTUAL',
    monto_pagado DECIMAL(10, 2) NOT NULL,
    emitido_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comprobante_estadia
        FOREIGN KEY (estadia_id) REFERENCES estadias(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 10. Reseñas y Calificaciones Verificadas (EP5-HU1 - La carpeta roja)
CREATE TABLE resenas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    estadia_id INT NOT NULL UNIQUE,
    usuario_id INT NOT NULL,
    estacionamiento_id INT NOT NULL,
    estrellas TINYINT NOT NULL,
    comentario VARCHAR(300) DEFAULT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_estrellas CHECK (estrellas BETWEEN 1 AND 5),
    CONSTRAINT fk_resena_estadia
        FOREIGN KEY (estadia_id) REFERENCES estadias(id) ON DELETE CASCADE,
    CONSTRAINT fk_resena_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_resena_estacionamiento
        FOREIGN KEY (estacionamiento_id) REFERENCES estacionamientos(id) ON DELETE CASCADE
) ENGINE=InnoDB;
