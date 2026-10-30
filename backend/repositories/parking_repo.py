"""Repositorio SQL para Estacionamientos, Plazas (Estilo Restaurante), Tarifas y Reseñas."""


def list_parkings_public(
    cursor,
    search: str = None,
    tipo_vehiculo_id: int = None,
    max_precio_hora: float = None,
    solo_techado: bool = False,
    solo_disponibles: bool = False,
) -> list:
    params = []
    conditions = ["e.activo = 1"]

    if search:
        like_term = f"%{search}%"
        conditions.append("(e.nombre LIKE %s OR e.direccion LIKE %s OR e.ciudad LIKE %s)")
        params.extend([like_term, like_term, like_term])

    if solo_techado:
        conditions.append("e.techado = 1")

    if tipo_vehiculo_id:
        if max_precio_hora is not None:
            conditions.append(
                """
                EXISTS (
                    SELECT 1 FROM tarifas tf
                    WHERE tf.estacionamiento_id = e.id
                      AND tf.tipo_vehiculo_id = %s
                      AND tf.precio_hora <= %s
                )
                """
            )
            params.extend([tipo_vehiculo_id, max_precio_hora])
        else:
            conditions.append(
                """
                EXISTS (
                    SELECT 1 FROM tarifas tf
                    WHERE tf.estacionamiento_id = e.id
                      AND tf.tipo_vehiculo_id = %s
                )
                """
            )
            params.append(tipo_vehiculo_id)
    elif max_precio_hora is not None:
        conditions.append(
            """
            EXISTS (
                SELECT 1 FROM tarifas tf
                WHERE tf.estacionamiento_id = e.id
                  AND tf.precio_hora <= %s
            )
            """
        )
        params.append(max_precio_hora)

    having_clause = "HAVING plazas_libres > 0" if solo_disponibles else ""
    where_sql = " AND ".join(conditions)

    cursor.execute(
        f"""
        SELECT
            e.id, e.propietario_id, e.nombre, e.direccion, e.ciudad,
            e.latitud, e.longitud, e.cantidad_plazas, e.horario_texto, e.techado, e.activo,
            u.nombre AS propietario_nombre,
            COALESCE(SUM(CASE WHEN p.activa = 1 THEN 1 ELSE 0 END), 0) AS plazas_totales,
            COALESCE(SUM(CASE WHEN p.activa = 1 AND p.ocupada = 0 THEN 1 ELSE 0 END), 0) AS plazas_libres,
            COALESCE(SUM(CASE WHEN p.activa = 1 AND p.ocupada = 1 THEN 1 ELSE 0 END), 0) AS plazas_ocupadas,
            (SELECT MIN(t2.precio_hora) FROM tarifas t2 WHERE t2.estacionamiento_id = e.id) AS precio_desde_hora,
            (SELECT ROUND(AVG(r.estrellas), 1) FROM resenas r WHERE r.estacionamiento_id = e.id) AS promedio_estrellas,
            (SELECT COUNT(*) FROM resenas r WHERE r.estacionamiento_id = e.id) AS total_resenas
        FROM estacionamientos e
        INNER JOIN usuarios u ON u.id = e.propietario_id
        LEFT JOIN plazas p ON p.estacionamiento_id = e.id
        WHERE {where_sql}
        GROUP BY e.id, u.id, u.nombre
        {having_clause}
        ORDER BY plazas_libres DESC, e.id ASC
        """,
        tuple(params),
    )
    return cursor.fetchall()


def find_parking_by_id(cursor, parking_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            e.id, e.propietario_id, e.nombre, e.direccion, e.ciudad,
            e.latitud, e.longitud, e.cantidad_plazas, e.horario_texto, e.techado, e.activo,
            u.nombre AS propietario_nombre,
            (SELECT ROUND(AVG(r.estrellas), 1) FROM resenas r WHERE r.estacionamiento_id = e.id) AS promedio_estrellas,
            (SELECT COUNT(*) FROM resenas r WHERE r.estacionamiento_id = e.id) AS total_resenas
        FROM estacionamientos e
        INNER JOIN usuarios u ON u.id = e.propietario_id
        WHERE e.id = %s
        """,
        (parking_id,),
    )
    return cursor.fetchone()


def find_parking_by_owner(cursor, propietario_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            e.id, e.propietario_id, e.nombre, e.direccion, e.ciudad,
            e.latitud, e.longitud, e.cantidad_plazas, e.horario_texto, e.techado, e.activo
        FROM estacionamientos e
        WHERE e.propietario_id = %s
        """,
        (propietario_id,),
    )
    return cursor.fetchone()


def create_parking(
    cursor,
    propietario_id: int,
    nombre: str,
    direccion: str,
    ciudad: str,
    latitud: float,
    longitud: float,
    cantidad_plazas: int,
    horario_texto: str,
    techado: int,
) -> int:
    cursor.execute(
        """
        INSERT INTO estacionamientos
            (propietario_id, nombre, direccion, ciudad, latitud, longitud, cantidad_plazas, horario_texto, techado, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """,
        (
            propietario_id,
            nombre,
            direccion,
            ciudad,
            latitud,
            longitud,
            cantidad_plazas,
            horario_texto,
            techado,
        ),
    )
    return cursor.lastrowid


def update_parking(
    cursor,
    parking_id: int,
    nombre: str,
    direccion: str,
    ciudad: str,
    latitud: float,
    longitud: float,
    cantidad_plazas: int,
    horario_texto: str,
    techado: int,
) -> None:
    cursor.execute(
        """
        UPDATE estacionamientos
        SET nombre = %s, direccion = %s, ciudad = %s, latitud = %s, longitud = %s,
            cantidad_plazas = %s, horario_texto = %s, techado = %s
        WHERE id = %s
        """,
        (
            nombre,
            direccion,
            ciudad,
            latitud,
            longitud,
            cantidad_plazas,
            horario_texto,
            techado,
            parking_id,
        ),
    )


def list_all_spots(cursor, parking_id: int, for_update: bool = False) -> list:
    lock = " FOR UPDATE" if for_update else ""
    cursor.execute(
        f"""
        SELECT id, estacionamiento_id, numero, codigo, ocupada, activa
        FROM plazas
        WHERE estacionamiento_id = %s
        ORDER BY numero ASC{lock}
        """,
        (parking_id,),
    )
    return cursor.fetchall()


def create_spot(cursor, parking_id: int, numero: int, codigo: str) -> int:
    cursor.execute(
        """
        INSERT INTO plazas (estacionamiento_id, numero, codigo, ocupada, activa)
        VALUES (%s, %s, %s, 0, 1)
        """,
        (parking_id, numero, codigo),
    )
    return cursor.lastrowid


def set_spot_active(cursor, spot_id: int, activa: int) -> None:
    cursor.execute(
        "UPDATE plazas SET activa = %s WHERE id = %s",
        (activa, spot_id),
    )


def list_spots_with_live_stay(cursor, parking_id: int) -> list:
    cursor.execute(
        """
        SELECT
            p.id, p.estacionamiento_id, p.numero, p.codigo, p.ocupada, p.activa,
            es.id AS estadia_id,
            es.usuario_id AS estadia_usuario_id,
            es.patente_snapshot,
            es.nombre_cliente_snapshot,
            es.modalidad,
            es.tarifa_aplicada,
            es.fecha_ingreso,
            es.origen,
            tv.id AS tipo_vehiculo_id,
            tv.nombre AS tipo_vehiculo_nombre,
            tv.icono AS tipo_vehiculo_icono,
            CASE
                WHEN es.id IS NOT NULL THEN GREATEST(0, TIMESTAMPDIFF(SECOND, es.fecha_ingreso, NOW()))
                ELSE 0
            END AS segundos_transcurridos
        FROM plazas p
        LEFT JOIN estadias es ON es.plaza_id = p.id AND es.estado = 'ACTIVA'
        LEFT JOIN tipos_vehiculo tv ON tv.id = es.tipo_vehiculo_id
        WHERE p.estacionamiento_id = %s AND p.activa = 1
        ORDER BY p.numero ASC
        """,
        (parking_id,),
    )
    return cursor.fetchall()


def list_tariffs(cursor, parking_id: int) -> list:
    cursor.execute(
        """
        SELECT
            t.id, t.estacionamiento_id, t.tipo_vehiculo_id,
            t.precio_hora, t.precio_estadia_fija,
            tv.nombre AS tipo_nombre, tv.icono AS tipo_icono
        FROM tarifas t
        INNER JOIN tipos_vehiculo tv ON tv.id = t.tipo_vehiculo_id
        WHERE t.estacionamiento_id = %s AND tv.activo = 1
        ORDER BY tv.id ASC
        """,
        (parking_id,),
    )
    return cursor.fetchall()


def list_tariffs_for_parkings(cursor, parking_ids: list) -> list:
    if not parking_ids:
        return []
    placeholders = ", ".join(["%s"] * len(parking_ids))
    cursor.execute(
        f"""
        SELECT
            t.estacionamiento_id, t.tipo_vehiculo_id,
            t.precio_hora, t.precio_estadia_fija,
            tv.nombre AS tipo_nombre, tv.icono AS tipo_icono
        FROM tarifas t
        INNER JOIN tipos_vehiculo tv ON tv.id = t.tipo_vehiculo_id
        WHERE t.estacionamiento_id IN ({placeholders}) AND tv.activo = 1
        ORDER BY tv.id ASC
        """,
        tuple(parking_ids),
    )
    return cursor.fetchall()


def find_tariff(cursor, parking_id: int, tipo_vehiculo_id: int) -> dict:
    cursor.execute(
        """
        SELECT id, estacionamiento_id, tipo_vehiculo_id, precio_hora, precio_estadia_fija
        FROM tarifas
        WHERE estacionamiento_id = %s AND tipo_vehiculo_id = %s
        """,
        (parking_id, tipo_vehiculo_id),
    )
    return cursor.fetchone()


def upsert_tariff(
    cursor, parking_id: int, tipo_vehiculo_id: int, precio_hora, precio_estadia_fija
) -> None:
    cursor.execute(
        """
        INSERT INTO tarifas (estacionamiento_id, tipo_vehiculo_id, precio_hora, precio_estadia_fija)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            precio_hora = VALUES(precio_hora),
            precio_estadia_fija = VALUES(precio_estadia_fija)
        """,
        (parking_id, tipo_vehiculo_id, precio_hora, precio_estadia_fija),
    )


def delete_tariff(cursor, parking_id: int, tipo_vehiculo_id: int) -> None:
    cursor.execute(
        "DELETE FROM tarifas WHERE estacionamiento_id = %s AND tipo_vehiculo_id = %s",
        (parking_id, tipo_vehiculo_id),
    )


def list_reviews(cursor, parking_id: int, limit: int = 15) -> list:
    cursor.execute(
        """
        SELECT
            r.id, r.estadia_id, r.estrellas, r.comentario, r.creado_en,
            u.nombre AS usuario_nombre
        FROM resenas r
        INNER JOIN usuarios u ON u.id = r.usuario_id
        WHERE r.estacionamiento_id = %s
        ORDER BY r.id DESC
        LIMIT %s
        """,
        (parking_id, limit),
    )
    return cursor.fetchall()


def list_all_parkings_admin(cursor) -> list:
    cursor.execute(
        """
        SELECT
            e.id, e.nombre, e.direccion, e.ciudad, e.cantidad_plazas, e.techado, e.activo, e.creado_en,
            u.nombre AS propietario_nombre, u.email AS propietario_email,
            COALESCE(SUM(CASE WHEN p.activa = 1 AND p.ocupada = 1 THEN 1 ELSE 0 END), 0) AS plazas_ocupadas,
            COALESCE(SUM(CASE WHEN p.activa = 1 THEN 1 ELSE 0 END), 0) AS plazas_activas,
            (SELECT COALESCE(SUM(es.monto_total), 0) FROM estadias es WHERE es.estacionamiento_id = e.id AND es.estado = 'FINALIZADA') AS ingresos_historicos
        FROM estacionamientos e
        INNER JOIN usuarios u ON u.id = e.propietario_id
        LEFT JOIN plazas p ON p.estacionamiento_id = e.id
        GROUP BY e.id, u.id, u.nombre, u.email
        ORDER BY e.id ASC
        """
    )
    return cursor.fetchall()


def toggle_parking_active(cursor, parking_id: int, activo: int) -> None:
    cursor.execute(
        "UPDATE estacionamientos SET activo = %s WHERE id = %s",
        (activo, parking_id),
    )
