import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    """
    Configura el sistema de logging para la aplicación.

    Esta función configura tres manejadores para el logger raíz:
    1. StreamHandler: Muestra los logs de nivel INFO y superior en la consola.
    2. RotatingFileHandler: Guarda los logs de nivel INFO y superior en 'info.log',
       con rotación de archivos para evitar que crezcan indefinidamente.
    3. FileHandler: Guarda los logs de nivel WARNING y superior en 'error.log',
       para un fácil diagnóstico de problemas.

    No devuelve nada, ya que configura el logger raíz que es accesible
    globalmente a través de `logging.getLogger()`.
    """
    # Configurar un formato común para los logs
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    # Obtener el logger raíz. Todos los demás loggers heredarán de este.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Nivel mínimo para que los logs pasen a los handlers

    # Crear un manejador para mostrar los logs en la consola (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO) # Muestra INFO y superior en consola

    # Crear un manejador de archivo rotativo para logs de información
    # Rota cuando el archivo alcanza 5MB, mantiene 5 archivos de respaldo.
    info_handler = RotatingFileHandler(
        filename='info.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    info_handler.setFormatter(formatter)
    info_handler.setLevel(logging.INFO) # Solo logs de INFO y superior

    # Crear un manejador de archivo para logs de error
    error_handler = logging.FileHandler(filename='error.log', encoding='utf-8', mode='a')
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.WARNING) # Solo logs de WARNING y superior

    # Añadir los manejadores al logger raíz
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(info_handler)
    root_logger.addHandler(error_handler)