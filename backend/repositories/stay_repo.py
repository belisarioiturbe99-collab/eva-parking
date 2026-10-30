"""Repositorio SQL para Estadías, Comprobantes (Tickets), Reseñas y Métricas."""


def find_spot_for_update(cursor, plaza_id: int) -> dict:
    cursor.execute(
        """
        SELECT p.id, p.estacionamiento_id, p.numero, p.codigo, p.ocupada, p.activa,
               e.activo AS estacionamiento_activo, e.propietario_id, e.nombre AS estacionamiento_nombre
        FROM plazas p
        INNER JOIN estacionamientos e ON e.id = p.estacionamiento_id
        WHERE p.id = %s
        FOR UPDATE
        """,
        (plaza_id,),
    )
    return cursor.fetchone()


def find_active_stay_by_plate(cursor, patente: str) -> dict:
    cursor.execute(
        """
        SELECT id, estacionamiento_id, plaza_id, patente_snapshot
        FROM estadias
        WHERE patente_snapshot = %s AND estado = 'ACTIVA'
        LIMIT 1
        """,
        (patente,),
    )
    return cursor.fetchone()


def create_stay(
    cursor,
    estacionamiento_id: int,
    plaza_id: int,
    usuario_id,
    vehiculo_id,
    tipo_vehiculo_id: int,
    patente_snapshot: str,
    nombre_cliente_snapshot: str,
    modalidad: str,
    tarifa_aplicada,
    origen: str,
) -> int:
    cursor.execute(
        """
        INSERT INTO estadias (
            estacionamiento_id, plaza_id, usuario_id, vehiculo_id, tipo_vehiculo_id,
            patente_snapshot, nombre_cliente_snapshot, modalidad, tarifa_aplicada,
            fecha_ingreso, origen, estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, 'ACTIVA')
        """,
        (
            estacionamiento_id,
            plaza_id,
            usuario_id,
            vehiculo_id,
            tipo_vehiculo_id,
            patente_snapshot,
            nombre_cliente_snapshot,
            modalidad,
            tarifa_aplicada,
            origen,
        ),
    )
    return cursor.lastrowid


def set_spot_occupied(cursor, plaza_id: int, ocupada: int) -> None:
    cursor.execute(
        "UPDATE plazas SET ocupada = %s WHERE id = %s",
        (ocupada, plaza_id),
    )


def find_stay_for_checkout(cursor, estadia_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            es.id, es.estacionamiento_id, es.plaza_id, es.usuario_id, es.vehiculo_id,
            es.tipo_vehiculo_id, es.patente_snapshot, es.nombre_cliente_snapshot,
            es.modalidad, es.tarifa_aplicada, es.fecha_ingreso, es.fecha_salida,
            es.origen, es.estado,
            GREATEST(0, TIMESTAMPDIFF(SECOND, es.fecha_ingreso, NOW())) AS segundos_transcurridos,
            p.codigo AS plaza_codigo,
            e.nombre AS estacionamiento_nombre, e.direccion AS estacionamiento_direccion,
            e.propietario_id,
            tv.nombre AS tipo_vehiculo_nombre
        FROM estadias es
        INNER JOIN plazas p ON p.id = es.plaza_id
        INNER JOIN estacionamientos e ON e.id = es.estacionamiento_id
        INNER JOIN tipos_vehiculo tv ON tv.id = es.tipo_vehiculo_id
        WHERE es.id = %s
        FOR UPDATE
        """,
        (estadia_id,),
    )
    return cursor.fetchone()


def finalize_stay(cursor, estadia_id: int, minutos_transcurridos: int, monto_total) -> None:
    cursor.execute(
        """
        UPDATE estadias
        SET fecha_salida = NOW(),
            minutos_transcurridos = %s,
            monto_total = %s,
            estado = 'FINALIZADA'
        WHERE id = %s
        """,
        (minutos_transcurridos, monto_total, estadia_id),
    )


def create_receipt(
    cursor, estadia_id: int, numero_ticket: str, metodo_pago: str, monto_pagado
) -> int:
    cursor.execute(
        """
        INSERT INTO comprobantes (estadia_id, numero_ticket, metodo_pago, monto_pagado, emitido_en)
        VALUES (%s, %s, %s, %s, NOW())
        """,
        (estadia_id, numero_ticket, metodo_pago, monto_pagado),
    )
    return cursor.lastrowid


def find_receipt_details(cursor, estadia_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            c.id AS comprobante_id, c.numero_ticket, c.metodo_pago, c.monto_pagado, c.emitido_en,
            es.id AS estadia_id, es.usuario_id, es.patente_snapshot, es.nombre_cliente_snapshot,
            es.modalidad, es.tarifa_aplicada, es.fecha_ingreso, es.fecha_salida,
            es.minutos_transcurridos, es.origen,
            p.codigo AS plaza_codigo,
            e.id AS estacionamiento_id, e.nombre AS estacionamiento_nombre,
            e.direccion AS estacionamiento_direccion, e.ciudad AS estacionamiento_ciudad,
            e.propietario_id,
            u_prop.nombre AS propietario_nombre,
            tv.nombre AS tipo_vehiculo_nombre,
            r.id AS resena_id, r.estrellas AS resena_estrellas, r.comentario AS resena_comentario
        FROM comprobantes c
        INNER JOIN estadias es ON es.id = c.estadia_id
        INNER JOIN plazas p ON p.id = es.plaza_id
        INNER JOIN estacionamientos e ON e.id = es.estacionamiento_id
        INNER JOIN usuarios u_prop ON u_prop.id = e.propietario_id
        INNER JOIN tipos_vehiculo tv ON tv.id = es.tipo_vehiculo_id
        LEFT JOIN resenas r ON r.estadia_id = es.id
        WHERE c.estadia_id = %s
        """,
        (estadia_id,),
    )
    return cursor.fetchone()


def list_active_stays_by_user(cursor, usuario_id: int) -> list:
    cursor.execute(
        """
        SELECT
            es.id, es.estacionamiento_id, es.plaza_id, es.patente_snapshot,
            es.modalidad, es.tarifa_aplicada, es.fecha_ingreso, es.origen,
            GREATEST(0, TIMESTAMPDIFF(SECOND, es.fecha_ingreso, NOW())) AS segundos_transcurridos,
            p.codigo AS plaza_codigo,
            e.nombre AS estacionamiento_nombre, e.direccion AS estacionamiento_direccion,
            tv.nombre AS tipo_vehiculo_nombre, tv.icono AS tipo_vehiculo_icono
        FROM estadias es
        INNER JOIN plazas p ON p.id = es.plaza_id
        INNER JOIN estacionamientos e ON e.id = es.estacionamiento_id
        INNER JOIN tipos_vehiculo tv ON tv.id = es.tipo_vehiculo_id
        WHERE es.usuario_id = %s AND es.estado = 'ACTIVA'
        ORDER BY es.fecha_ingreso DESC
        """,
        (usuario_id,),
    )
    return cursor.fetchall()


def list_history_by_user(cursor, usuario_id: int, limit: int = 25) -> list:
    cursor.execute(
        """
        SELECT
            es.id, es.estacionamiento_id, es.patente_snapshot, es.modalidad,
            es.tarifa_aplicada, es.fecha_ingreso, es.fecha_salida,
            es.minutos_transcurridos, es.monto_total,
            p.codigo AS plaza_codigo,
            e.nombre AS estacionamiento_nombre,
            tv.nombre AS tipo_vehiculo_nombre,
            c.numero_ticket, c.metodo_pago,
            r.id AS resena_id, r.estrellas AS resena_estrellas, r.comentario AS resena_comentario
        FROM estadias es
        INNER JOIN plazas p ON p.id = es.plaza_id
        INNER JOIN estacionamientos e ON e.id = es.estacionamiento_id
        INNER JOIN tipos_vehiculo tv ON tv.id = es.tipo_vehiculo_id
        LEFT JOIN comprobantes c ON c.estadia_id = es.id
        LEFT JOIN resenas r ON r.estadia_id = es.id
        WHERE es.usuario_id = %s AND es.estado = 'FINALIZADA'
        ORDER BY es.fecha_salida DESC, es.id DESC
        LIMIT %s
        """,
        (usuario_id, limit),
    )
    return cursor.fetchall()


def list_recent_stays_by_parking(cursor, parking_id: int, limit: int = 25) -> list:
    cursor.execute(
        """
        SELECT
            es.id, es.patente_snapshot, es.nombre_cliente_snapshot, es.modalidad,
            es.tarifa_aplicada, es.fecha_ingreso, es.fecha_salida,
            es.minutos_transcurridos, es.monto_total, es.origen, es.estado,
            p.codigo AS plaza_codigo,
            tv.nombre AS tipo_vehiculo_nombre,
            c.numero_ticket, c.metodo_pago
        FROM estadias es
        INNER JOIN plazas p ON p.id = es.plaza_id
        INNER JOIN tipos_vehiculo tv ON tv.id = es.tipo_vehiculo_id
        LEFT JOIN comprobantes c ON c.estadia_id = es.id
        WHERE es.estacionamiento_id = %s
        ORDER BY es.id DESC
        LIMIT %s
        """,
        (parking_id, limit),
    )
    return cursor.fetchall()


def get_owner_metrics(cursor, parking_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            (SELECT COALESCE(SUM(monto_total), 0) FROM estadias WHERE estacionamiento_id = %s AND estado = 'FINALIZADA') AS ingresos_totales,
            (SELECT COALESCE(SUM(monto_total), 0) FROM estadias WHERE estacionamiento_id = %s AND estado = 'FINALIZADA' AND DATE(fecha_salida) = CURDATE()) AS ingresos_hoy,
            (SELECT COUNT(*) FROM estadias WHERE estacionamiento_id = %s AND estado = 'FINALIZADA') AS estadias_finalizadas,
            (SELECT COUNT(*) FROM estadias WHERE estacionamiento_id = %s AND estado = 'ACTIVA') AS estadias_activas
        """,
        (parking_id, parking_id, parking_id, parking_id),
    )
    return cursor.fetchone()


def find_stay_for_review(cursor, estadia_id: int) -> dict:
    cursor.execute(
        """
        SELECT es.id, es.usuario_id, es.estacionamiento_id, es.estado,
               r.id AS resena_existente_id
        FROM estadias es
        LEFT JOIN resenas r ON r.estadia_id = es.id
        WHERE es.id = %s
        """,
        (estadia_id,),
    )
    return cursor.fetchone()


def create_review(
    cursor,
    estadia_id: int,
    usuario_id: int,
    estacionamiento_id: int,
    estrellas: int,
    comentario: str,
) -> int:
    cursor.execute(
        """
        INSERT INTO resenas (estadia_id, usuario_id, estacionamiento_id, estrellas, comentario)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (estadia_id, usuario_id, estacionamiento_id, estrellas, comentario),
    )
    return cursor.lastrowid


def get_global_metrics(cursor) -> dict:
    cursor.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM usuarios) AS total_usuarios,
            (SELECT COUNT(*) FROM usuarios WHERE rol = 'USUARIO') AS total_conductores,
            (SELECT COUNT(*) FROM usuarios WHERE rol = 'PROPIETARIO') AS total_propietarios,
            (SELECT COUNT(*) FROM estacionamientos WHERE activo = 1) AS estacionamientos_activos,
            (SELECT COUNT(*) FROM plazas p INNER JOIN estacionamientos e ON e.id = p.estacionamiento_id WHERE p.activa = 1 AND e.activo = 1) AS plazas_totales_red,
            (SELECT COUNT(*) FROM plazas p INNER JOIN estacionamientos e ON e.id = p.estacionamiento_id WHERE p.activa = 1 AND p.ocupada = 1 AND e.activo = 1) AS plazas_ocupadas_red,
            (SELECT COUNT(*) FROM estadias WHERE estado = 'ACTIVA') AS estadias_activas,
            (SELECT COUNT(*) FROM estadias WHERE estado = 'FINALIZADA') AS estadias_finalizadas,
            (SELECT COALESCE(SUM(monto_total), 0) FROM estadias WHERE estado = 'FINALIZADA') AS volumen_facturado
        """
    )
    return cursor.fetchone()
