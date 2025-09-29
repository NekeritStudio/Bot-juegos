import logging
import sys

def setup_logging():
    """
    Configura y devuelve un logger para el bot.

    Esta función configura dos manejadores:
    1. StreamHandler: Muestra los logs en la consola.
    2. FileHandler: Guarda los logs en un archivo 'bot.log'.

    También configura el logger de la biblioteca discord.py para que use
    los mismos manejadores.
    """
    # Configurar un formato común para los logs
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    # Crear un manejador para mostrar los logs en la consola (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # Crear un manejador para escribir los logs en un archivo
    file_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
    file_handler.setFormatter(formatter)

    # Configurar el logger de discord.py para que use nuestros manejadores
    discord_logger =  logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO) # Cambia a logging.DEBUG para ver más detalles
    discord_logger.addHandler(file_handler)
    discord_logger.addHandler(stream_handler)

    # Devolver el logger principal para ser usado en la aplicación
    return logging.getLogger('discord_bot')