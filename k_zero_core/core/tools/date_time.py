"""
Herramienta: Fecha y hora del sistema.
"""
import datetime


def obtener_hora_actual() -> str:
    """
    Obtiene la fecha y hora actual del sistema local del usuario.

    Returns:
        Fecha y hora en formato legible con zona horaria.
    """
    ahora = datetime.datetime.now()
    zona = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname()
    return ahora.strftime(f"%A, %d de %B de %Y — %H:%M:%S ({zona})")
