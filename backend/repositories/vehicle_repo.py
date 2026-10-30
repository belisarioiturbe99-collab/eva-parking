"""Repositorio SQL para Tipos de Vehículo y Vehículos de Usuarios."""


def list_vehicle_types(cursor, only_active: bool = True) -> list:
    where = "WHERE activo = 1" if only_active else ""
    cursor.execute(
        f"""
        SELECT id, nombre, icono, descripcion, activo
        FROM tipos_vehiculo
        {where}
        ORDER BY id ASC
        """
    )
    return cursor.fetchall()


def find_vehicle_type(cursor, type_id: int) -> dict:
    cursor.execute(
        "SELECT id, nombre, icono, descripcion, activo FROM tipos_vehiculo WHERE id = %s",
        (type_id,),
    )
    return cursor.fetchone()


def find_vehicle_type_by_name(cursor, nombre: str) -> dict:
    cursor.execute(
        "SELECT id, nombre, activo FROM tipos_vehiculo WHERE LOWER(nombre) = LOWER(%s)",
        (nombre,),
    )
    return cursor.fetchone()


def create_vehicle_type(cursor, nombre: str, icono: str, descripcion: str) -> int:
    cursor.execute(
        """
        INSERT INTO tipos_vehiculo (nombre, icono, descripcion, activo)
        VALUES (%s, %s, %s, 1)
        """,
        (nombre, icono, descripcion),
    )
    return cursor.lastrowid


def toggle_vehicle_type(cursor, type_id: int, activo: int) -> None:
    cursor.execute(
        "UPDATE tipos_vehiculo SET activo = %s WHERE id = %s",
        (activo, type_id),
    )


def list_user_vehicles(cursor, usuario_id: int) -> list:
    cursor.execute(
        """
        SELECT
            v.id, v.usuario_id, v.tipo_vehiculo_id, v.patente, v.descripcion, v.activo, v.creado_en,
            tv.nombre AS tipo_nombre, tv.icono AS tipo_icono,
            EXISTS(
                SELECT 1 FROM estadias e
                WHERE e.vehiculo_id = v.id AND e.estado = 'ACTIVA'
            ) AS en_estadia_activa
        FROM vehiculos v
        INNER JOIN tipos_vehiculo tv ON tv.id = v.tipo_vehiculo_id
        WHERE v.usuario_id = %s AND v.activo = 1
        ORDER BY v.id DESC
        """,
        (usuario_id,),
    )
    return cursor.fetchall()


def find_vehicle_by_id(cursor, vehicle_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            v.id, v.usuario_id, v.tipo_vehiculo_id, v.patente, v.descripcion, v.activo,
            tv.nombre AS tipo_nombre
        FROM vehiculos v
        INNER JOIN tipos_vehiculo tv ON tv.id = v.tipo_vehiculo_id
        WHERE v.id = %s
        """,
        (vehicle_id,),
    )
    return cursor.fetchone()


def find_by_plate(cursor, patente: str) -> dict:
    cursor.execute(
        "SELECT id, usuario_id, tipo_vehiculo_id, patente, activo FROM vehiculos WHERE patente = %s",
        (patente,),
    )
    return cursor.fetchone()


def create_vehicle(
    cursor, usuario_id: int, tipo_vehiculo_id: int, patente: str, descripcion: str
) -> int:
    cursor.execute(
        """
        INSERT INTO vehiculos (usuario_id, tipo_vehiculo_id, patente, descripcion, activo)
        VALUES (%s, %s, %s, %s, 1)
        """,
        (usuario_id, tipo_vehiculo_id, patente, descripcion),
    )
    return cursor.lastrowid


def reactivate_vehicle(
    cursor, vehicle_id: int, usuario_id: int, tipo_vehiculo_id: int, descripcion: str
) -> None:
    cursor.execute(
        """
        UPDATE vehiculos
        SET usuario_id = %s, tipo_vehiculo_id = %s, descripcion = %s, activo = 1
        WHERE id = %s
        """,
        (usuario_id, tipo_vehiculo_id, descripcion, vehicle_id),
    )


def deactivate_vehicle(cursor, vehicle_id: int, usuario_id: int) -> None:
    cursor.execute(
        "UPDATE vehiculos SET activo = 0 WHERE id = %s AND usuario_id = %s",
        (vehicle_id, usuario_id),
    )
