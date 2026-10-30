"""Repositorio SQL para Usuarios y Movimientos de Billetera Virtual."""


def find_by_email(cursor, email: str) -> dict:
    cursor.execute(
        """
        SELECT id, nombre, email, password_hash, rol, saldo_billetera, activo, creado_en
        FROM usuarios
        WHERE email = %s
        """,
        (email,),
    )
    return cursor.fetchone()


def find_by_id(cursor, user_id: int, for_update: bool = False) -> dict:
    lock = " FOR UPDATE" if for_update else ""
    cursor.execute(
        f"""
        SELECT id, nombre, email, password_hash, rol, saldo_billetera, activo, creado_en
        FROM usuarios
        WHERE id = %s{lock}
        """,
        (user_id,),
    )
    return cursor.fetchone()


def create_user(cursor, nombre: str, email: str, password_hash: str, rol: str) -> int:
    cursor.execute(
        """
        INSERT INTO usuarios (nombre, email, password_hash, rol, saldo_billetera, activo)
        VALUES (%s, %s, %s, %s, 0.00, 1)
        """,
        (nombre, email, password_hash, rol),
    )
    return cursor.lastrowid


def update_profile(cursor, user_id: int, nombre: str) -> None:
    cursor.execute(
        "UPDATE usuarios SET nombre = %s WHERE id = %s",
        (nombre, user_id),
    )


def update_wallet_balance(cursor, user_id: int, new_balance) -> None:
    cursor.execute(
        "UPDATE usuarios SET saldo_billetera = %s WHERE id = %s",
        (new_balance, user_id),
    )


def insert_wallet_movement(
    cursor,
    usuario_id: int,
    estadia_id,
    tipo: str,
    monto,
    saldo_posterior,
    descripcion: str,
) -> int:
    cursor.execute(
        """
        INSERT INTO movimientos_billetera
            (usuario_id, estadia_id, tipo, monto, saldo_posterior, descripcion)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (usuario_id, estadia_id, tipo, monto, saldo_posterior, descripcion),
    )
    return cursor.lastrowid


def list_wallet_movements(cursor, usuario_id: int, limit: int = 30) -> list:
    cursor.execute(
        """
        SELECT id, estadia_id, tipo, monto, saldo_posterior, descripcion, creado_en
        FROM movimientos_billetera
        WHERE usuario_id = %s
        ORDER BY id DESC
        LIMIT %s
        """,
        (usuario_id, limit),
    )
    return cursor.fetchall()


def list_all_users(cursor) -> list:
    cursor.execute(
        """
        SELECT
            u.id, u.nombre, u.email, u.rol, u.saldo_billetera, u.activo, u.creado_en,
            e.nombre AS estacionamiento_nombre,
            (SELECT COUNT(*) FROM vehiculos v WHERE v.usuario_id = u.id AND v.activo = 1) AS total_vehiculos
        FROM usuarios u
        LEFT JOIN estacionamientos e ON e.propietario_id = u.id
        ORDER BY u.id ASC
        """
    )
    return cursor.fetchall()


def toggle_user_active(cursor, user_id: int, activo: int) -> None:
    cursor.execute(
        "UPDATE usuarios SET activo = %s WHERE id = %s",
        (activo, user_id),
    )
