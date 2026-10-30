# Diseño de Base de Datos Relacional — E.V.A

La capa de persistencia de **E.V.A** está implementada sobre **MySQL / MariaDB (XAMPP)** utilizando el motor transaccional `InnoDB` y codificación `utf8mb4_unicode_ci`. Los scripts de creación y datos de prueba se encuentran en [`database/schema.sql`](../database/schema.sql) y [`database/seed.sql`](../database/seed.sql).

---

## 1. Resumen de Tablas (Una línea por tabla)

1. **`usuarios`**: Guarda las credenciales encriptadas (`password_hash`), el rol (`ADMIN`, `PROPIETARIO`, `USUARIO`), el estado de cuenta y el saldo actual de la Billetera Virtual.
2. **`tipos_vehiculo`**: Almacena el catálogo maestro de categorías de vehículos soportadas en la plataforma (`Auto`, `Moto`, `Camioneta`, `Utilitario`, etc.).
3. **`vehiculos`**: Registra los múltiples vehículos asociados a cada conductor con validación de patente única normalizada.
4. **`estacionamientos`**: Contiene los datos comerciales, ubicación geográfica (latitud/longitud), horario y capacidad total de plazas del local administrado en relación 1 a 1 por cada propietario.
5. **`plazas`**: Representa cada lugar físico individual (`P-01`..`P-N`) de un estacionamiento y su estado booleano en tiempo real (`ocupada = 0` Verde / `ocupada = 1` Rojo).
6. **`tarifas`**: Define el precio por hora y el precio por estadía fija configurados por cada estacionamiento para cada tipo de vehículo habilitado.
7. **`estadias`**: Registra cada ocupación activa o finalizada vinculando plaza, vehículo, tarifa congelada al ingreso, marca temporal de entrada/salida, origen (`APP_USUARIO` o `MOSTRADOR_PROPIETARIO`) y monto total calculado.
8. **`movimientos_billetera`**: Audita todas las operaciones financieras de recarga de saldo, pago de estadías por conductores y acreditaciones a propietarios.
9. **`comprobantes`**: Guarda los tickets digitales numerados (`EVA-2026-XXXXX`) e imprimibles emitidos al finalizar y abonar cada estadía (`EP4-HU2`).
10. **`resenas`**: Almacena la calificación verificada (1 a 5 estrellas) y el comentario que el conductor deja sobre el estacionamiento tras completar su estadía (`EP5-HU1`).

---

## 2. Diagrama Entidad-Relación (DER)

> *Nota: GitHub renderiza automáticamente el siguiente diagrama Mermaid. Si también deseas adjuntar una captura PNG desde phpMyAdmin Designer o draw.io, guárdala como `docs/img/der-eva.png`.*

```mermaid
erDiagram
    USUARIOS ||--o{ VEHICULOS : "registra"
    USUARIOS ||--o| ESTACIONAMIENTOS : "administra_1_a_1"
    USUARIOS ||--o{ MOVIMIENTOS_BILLETERA : "opera"
    USUARIOS ||--o{ ESTADIAS : "ocupa"
    USUARIOS ||--o{ RESENAS : "califica"

    TIPOS_VEHICULO ||--o{ VEHICULOS : "clasifica"
    TIPOS_VEHICULO ||--o{ TARIFAS : "tarifa_por"
    TIPOS_VEHICULO ||--o{ ESTADIAS : "tipo_en"

    ESTACIONAMIENTOS ||--|{ PLAZAS : "compuesto_por"
    ESTACIONAMIENTOS ||--|{ TARIFAS : "define"
    ESTACIONAMIENTOS ||--o{ ESTADIAS : "registra"
    ESTACIONAMIENTOS ||--o{ RESENAS : "recibe"

    PLAZAS ||--o{ ESTADIAS : "aloja"
    VEHICULOS ||--o{ ESTADIAS : "ingresa_en"
    ESTADIAS ||--o| COMPROBANTES : "emite"
    ESTADIAS ||--o{ MOVIMIENTOS_BILLETERA : "origina"
    ESTADIAS ||--o| RESENAS : "habilita"

    USUARIOS {
        int id PK
        varchar nombre
        varchar email UK
        varchar password_hash
        enum rol
        decimal saldo_billetera
        tinyint activo
        datetime creado_en
    }

    TIPOS_VEHICULO {
        int id PK
        varchar nombre UK
        varchar icono
        varchar descripcion
        tinyint activo
    }

    VEHICULOS {
        int id PK
        int usuario_id FK
        int tipo_vehiculo_id FK
        varchar patente UK
        varchar descripcion
        tinyint activo
        datetime creado_en
    }

    ESTACIONAMIENTOS {
        int id PK
        int propietario_id FK_UK
        varchar nombre
        varchar direccion
        varchar ciudad
        decimal latitud
        decimal longitud
        int cantidad_plazas
        varchar horario_texto
        tinyint techado
        tinyint activo
        datetime creado_en
    }

    PLAZAS {
        int id PK
        int estacionamiento_id FK
        int numero
        varchar codigo
        tinyint ocupada
        tinyint activa
    }

    TARIFAS {
        int id PK
        int estacionamiento_id FK
        int tipo_vehiculo_id FK
        decimal precio_hora
        decimal precio_estadia_fija
    }

    ESTADIAS {
        int id PK
        int estacionamiento_id FK
        int plaza_id FK
        int usuario_id FK
        int vehiculo_id FK
        int tipo_vehiculo_id FK
        varchar patente_snapshot
        varchar nombre_cliente_snapshot
        enum modalidad
        decimal tarifa_aplicada
        datetime fecha_ingreso
        datetime fecha_salida
        int minutos_transcurridos
        decimal monto_total
        enum origen
        enum estado
    }

    MOVIMIENTOS_BILLETERA {
        int id PK
        int usuario_id FK
        int estadia_id FK
        enum tipo
        decimal monto
        decimal saldo_posterior
        varchar descripcion
        datetime creado_en
    }

    COMPROBANTES {
        int id PK
        int estadia_id FK_UK
        varchar numero_ticket UK
        enum metodo_pago
        decimal monto_pagado
        datetime emitido_en
    }

    RESENAS {
        int id PK
        int estadia_id FK_UK
        int usuario_id FK
        int estacionamiento_id FK
        tinyint estrellas
        varchar comentario
        datetime creado_en
    }
```
