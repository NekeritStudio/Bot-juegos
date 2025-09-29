import discord
from discord.ext import commands
from discord import app_commands, ui
import random

import logging

# --- CONFIGURACIÓN DE LOGS ---

# 1. Crear y configurar el logger principal
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO) # Nivel mínimo de registro (INFO, WARNING, ERROR, CRITICAL)

# 2. Crear un manejador para escribir los logs en un archivo
file_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')

# 3. Crear un formato para los mensajes de log
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
file_handler.setFormatter(formatter)

# 4. Añadir el manejador al logger
logger.addHandler(file_handler)

# --- CONSTANTES Y LÓGICA DE JUEGO ---

# Símbolos para el tablero
SIMBOLO_X = '❌'
SIMBOLO_O = '⭕'
CASILLA_VACIA_INT = '-' # Marcador interno
EMOJI_VACIA = '⬜'    # Emoji para el botón sin marcar

# Lógica principal del juego (para un array de 9 elementos)
def get_winner(board: list, symbol: str) -> bool:
    """Verifica si el símbolo dado tiene una línea ganadora."""
    wins = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Filas
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columnas
        (0, 4, 8), (2, 4, 6)              # Diagonales
    ]
    return any(all(board[i] == symbol for i in combo) for combo in wins)

def is_draw(board: list) -> bool:
    """Verifica si el tablero está lleno sin ganador."""
    return CASILLA_VACIA_INT not in board

def get_ia_move(board: list, ia_symbol: str, player_symbol: str) -> int:
    """Implementa la lógica de la IA (Ganar > Bloquear > Centro > Esquina)."""
    
    # 1. Intentar ganar o bloquear
    for symbol_check in [ia_symbol, player_symbol]:
        for i in range(9):
            if board[i] == CASILLA_VACIA_INT:
                board[i] = symbol_check
                if get_winner(board, symbol_check):
                    board[i] = CASILLA_VACIA_INT
                    return i
                board[i] = CASILLA_VACIA_INT

    # 2. Centro (4)
    if board[4] == CASILLA_VACIA_INT:
        return 4

    # 3. Esquinas (0, 2, 6, 8)
    corners = [i for i in [0, 2, 6, 8] if board[i] == CASILLA_VACIA_INT]
    if corners:
        return random.choice(corners)

    # 4. Movimiento aleatorio
    empty_cells = [i for i in range(9) if board[i] == CASILLA_VACIA_INT]
    return random.choice(empty_cells) if empty_cells else -1


# --- CLASE VIEW (EL TABLERO INTERACTIVO) ---

class TicTacToeView(ui.View):
    def __init__(self, player1: discord.User, player2: discord.User = None):
        super().__init__(timeout=300) # El juego expira después de 5 minutos de inactividad

        # 1. Estado del juego
        self.board = [CASILLA_VACIA_INT] * 9
        self.players = (player1, player2) if player2 else (player1, bot.user)
        self.current_player_index = 0
        self.symbols = {self.players[0]: SIMBOLO_X, self.players[1]: SIMBOLO_O}
        self.is_ai_game = (player2 is None)
        self.message = None # Para guardar el mensaje del juego y poder editarlo en on_timeout

        # 2. Configuración de botones (3 filas de 3)
        for i in range(9):
            button = ui.Button(
                style=discord.ButtonStyle.secondary, 
                label=EMOJI_VACIA, 
                custom_id=str(i), # Usamos el índice como ID
                row=i // 3
            )
            button.callback = self.button_callback
            self.add_item(button)

    def update_board_display(self, winner: discord.User = None):
        """Actualiza el estilo y estado de cada botón en la View."""
        for item in self.children:
            if isinstance(item, ui.Button):
                index = int(item.custom_id)
                symbol = self.board[index]

                if symbol == SIMBOLO_X:
                    item.style = discord.ButtonStyle.danger
                    item.label = SIMBOLO_X
                    item.disabled = True
                elif symbol == SIMBOLO_O:
                    item.style = discord.ButtonStyle.success
                    item.label = SIMBOLO_O
                    item.disabled = True
                else:
                    item.label = EMOJI_VACIA
                    item.disabled = False
                
                # Deshabilitar todos los botones si el juego ha terminado
                if winner or is_draw(self.board):
                    item.disabled = True

    def get_status_message(self, winner: discord.User = None, is_draw_game: bool = False) -> str:
        """Genera el mensaje de estado del juego."""
        if winner:
            return f"🎉 **{winner.mention} ha ganado la partida con {self.symbols[winner]}!** 🎉"
        if is_draw_game:
            return "🤝 **¡Es un empate!** 🤝"
            
        current_player = self.players[self.current_player_index]
        symbol = self.symbols[current_player]
        return f"Turno de **{current_player.mention}** ({symbol}). ¡Elige tu casilla!"

    async def process_move(self, interaction: discord.Interaction, index: int, symbol: str):
        """Procesa un movimiento humano, verifica el estado y cambia el turno/llama a la IA."""
        
        # 1. Realizar movimiento
        logger.info(f"[TicTacToe] Jugador {interaction.user.name} movió a la casilla {index}.")
        self.board[index] = symbol
        
        # 2. Verificar si el jugador humano ganó
        if get_winner(self.board, symbol):
            self.update_board_display(winner=interaction.user)
            await interaction.edit_original_response(content=self.get_status_message(winner=interaction.user), view=self)
            logger.info(f"[TicTacToe] Partida finalizada. Ganador: {interaction.user.name}.")
            self.stop()
            return
            
        # 3. Verificar empate
        if is_draw(self.board):
            self.update_board_display()
            await interaction.edit_original_response(content=self.get_status_message(is_draw_game=True), view=self)
            logger.info("[TicTacToe] Partida finalizada en empate.")
            self.stop()
            return
            
        # 4. Cambiar turno
        self.current_player_index = 1 - self.current_player_index
        
        # 5. Si es contra IA, procesar el movimiento de la IA
        if self.is_ai_game:
            await self.process_ia_move(interaction)
        else: # Si es JvJ
            self.update_board_display()
            await interaction.edit_original_response(content=self.get_status_message(), view=self)


    async def process_ia_move(self, interaction: discord.Interaction):
        """Maneja el turno de la IA y actualiza la View."""
        
        ia_user = self.players[1]
        ia_symbol = self.symbols[ia_user]
        player_symbol = self.symbols[self.players[0]]
        
        # Obtener y realizar el movimiento de la IA
        ia_index = get_ia_move(self.board, ia_symbol, player_symbol)
        
        if ia_index != -1:
            self.board[ia_index] = ia_symbol
            
            # Verificar si ganó la IA
            if get_winner(self.board, ia_symbol):
                self.update_board_display(winner=ia_user)
                await interaction.edit_original_response(content=self.get_status_message(winner=ia_user), view=self)
                logger.info(f"[TicTacToe] Partida finalizada. Ganador: {ia_user.name} (IA).")
                self.stop()
                return

            # Verificar empate después de la IA
            if is_draw(self.board):
                self.update_board_display()
                await interaction.edit_original_response(content=self.get_status_message(is_draw_game=True), view=self)
                logger.info("[TicTacToe] Partida finalizada en empate.")
                self.stop()
                return
        
        # Devolver el turno al jugador
        self.current_player_index = 0
        self.update_board_display()
        await interaction.edit_original_response(content=self.get_status_message(), view=self)


    async def button_callback(self, interaction: discord.Interaction):
        """Manejador para el clic de los botones."""
        
        # 1. Comprobar turno
        current_player = self.players[self.current_player_index]
        if interaction.user != current_player:
            await interaction.response.send_message("¡Espera tu turno! 🕰️", ephemeral=True)
            return

        # 2. Comprobar casilla
        index = int(interaction.data['custom_id'])
        if self.board[index] != CASILLA_VACIA_INT:
            await interaction.response.send_message("Esa casilla ya está ocupada. Elige otra.", ephemeral=True)
            return
            
        # Deferir la respuesta para manejar el tiempo de la IA (máximo 3 segundos)
        await interaction.response.defer()

        # 3. Procesar el movimiento
        symbol = self.symbols[current_player]
        await self.process_move(interaction, index, symbol)

    async def on_timeout(self):
        """Deshabilita los botones al finalizar el tiempo de espera."""
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ La partida ha expirado por inactividad. ⌛", view=self)
                logger.warning(f"[TicTacToe] Partida entre {self.players[0].name} y {self.players[1].name} ha expirado.")
            except discord.NotFound:
                # El mensaje pudo haber sido borrado, no hay nada que hacer.
                pass


# --- BOT Y COMANDO SLASH ---

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents) 
# --- CLASE COG PARA ADIVINA EL NÚMERO ---



# --- FIN DEL COG DE ADIVINA EL NÚMERO ---
@bot.event
async def on_ready():
    """Sincroniza los comandos slash con Discord al iniciar."""
    logger.info(f'Bot conectado como {bot.user} (ID: {bot.user.id})')
    print(f'Bot conectado como {bot.user}') # Mantenemos el print para feedback visual inmediato en consola
    try:
        logger.info("Cargando Cogs...")
        logger.info("AdivinaNumero Cog cargado.")

        # Sincronizar los comandos. Puede tardar unos minutos en aparecer.
        synced = await bot.tree.sync()
        logger.info(f"Sincronizados {len(synced)} comandos slash.")
    except Exception as e:
        logger.exception("Error al cargar cogs o sincronizar comandos:")

@bot.tree.command(name="tictactoe", description="Inicia una partida de Tres en Raya contra un jugador o la IA.")
# --- COMPONENTES PARA ADIVINA EL NÚMERO (MODERNO) ---

class GuessNumberModal(ui.Modal, title='Adivina el Número'):
    """Modal para que el usuario ingrese su número."""
    guess = ui.TextInput(label='Escribe tu número aquí', style=discord.TextStyle.short, placeholder='Ej: 25')

    async def on_submit(self, interaction: discord.Interaction):
        # Pasamos la interacción y el valor al método de la View para procesarlo.
        # self.view se refiere a la AdivinaNumeroView que abrió este modal.
        await self.view.process_guess(interaction, self.guess.value)

class AdivinaNumeroView(ui.View):
    def __init__(self, author: discord.User):
        super().__init__(timeout=180) # 3 minutos para jugar
        self.author = author
        self.numero_secreto = random.randint(1, 50)
        self.intentos = 0
        self.max_intentos = 7
        self.message = None
        
        logger.info(f"[AdivinaElNumero] Nueva partida para {author.name}. El número secreto es {self.numero_secreto}.")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(
                content=f"⌛ ¡El tiempo se acabó! El número secreto era **{self.numero_secreto}**.",
                view=self
            )

    @ui.button(label="Hacer un intento", style=discord.ButtonStyle.primary, emoji="🤔")
    async def guess_button(self, interaction: discord.Interaction, button: ui.Button):
        # Solo el autor del juego puede interactuar
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("No puedes jugar en la partida de otra persona.", ephemeral=True)
            return
        
        # Abrir el modal para que el usuario adivine
        await interaction.response.send_modal(GuessNumberModal())

    async def process_guess(self, interaction: discord.Interaction, guess_str: str):
        # Validar que la entrada sea un número
        try:
            guess = int(guess_str)
        except ValueError:
            await interaction.response.send_message("Por favor, introduce un número válido.", ephemeral=True)
            return

        self.intentos += 1
        intentos_restantes = self.max_intentos - self.intentos

        # Comprobar si ganó
        if guess == self.numero_secreto:
            logger.info(f"[AdivinaElNumero] {self.author.name} ganó en {self.intentos} intentos.")
            self.stop() # Detiene la View y deshabilita los botones
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                content=f"🌟 ¡Felicidades, **{self.author.name}**! Adivinaste el número (**{self.numero_secreto}**) en **{self.intentos}** intentos! 🥳",
                view=self
            )
            return

        # Comprobar si perdió
        if self.intentos >= self.max_intentos:
            logger.info(f"[AdivinaElNumero] {self.author.name} perdió. El número era {self.numero_secreto}.")
            self.stop()
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                content=f"💔 ¡Oh no! Se acabaron tus intentos. El número secreto era **{self.numero_secreto}**.",
                view=self
            )
            return

        # Dar pistas
        pista = "demasiado bajo ⬇️" if guess < self.numero_secreto else "demasiado alto ⬆️"
        await interaction.response.edit_message(
            content=f"Tu número ({guess}) es **{pista}**. Te quedan **{intentos_restantes}** intentos."
        )

@bot.tree.command(name="adivinar", description="Inicia un juego para adivinar un número entre 1 y 50.")
async def adivinar_command(interaction: discord.Interaction):
    view = AdivinaNumeroView(interaction.user)
    await interaction.response.send_message(
        f"🎉 **¡Adivina el número!** {interaction.user.mention}, he elegido un número secreto entre **1 y 50**.\n"
        f"Tienes **{view.max_intentos}** intentos. ¡Haz clic en el botón para empezar!",
        view=view
    )
    view.message = await interaction.original_response()

@app_commands.describe(oponente="Opcional: Menciona a un jugador para JvJ. Si se omite, jugarás contra la IA.")
async def tictactoe_command(interaction: discord.Interaction, oponente: discord.Member = None):
    
    # Manejar caso de desafiarse a sí mismo o desafiar al bot
    if oponente == interaction.user:
        await interaction.response.send_message("No puedes jugar contra ti mismo. 😅", ephemeral=True)
        return
    if oponente == bot.user:
        oponente = None # Se juega contra la IA
        
    # Inicializar la View (el tablero)
    view = TicTacToeView(player1=interaction.user, player2=oponente)
    
    # Determinar el mensaje de inicio
    if oponente is None:
        initial_message = f"**¡Partida de Tres en Raya contra la IA!** 🤖\n{interaction.user.mention} eres {SIMBOLO_X}."
    else:
        initial_message = f"**¡Partida de Tres en Raya JvJ!** 🤝\n{interaction.user.mention} ({SIMBOLO_X}) vs. {oponente.mention} ({SIMBOLO_O})."

    initial_message += f"\n\nTurno de **{interaction.user.mention}** ({SIMBOLO_X}). ¡Haz clic en una casilla!"
    logger.info(f"[TicTacToe] Nueva partida iniciada por {interaction.user.name} contra {'IA' if oponente is None else oponente.name}.")

    # Enviar el mensaje con los botones
    await interaction.response.send_message(
        content=initial_message,
        view=view
    )
    # Guardamos el mensaje para poder editarlo más tarde (ej: en on_timeout)
    view.message = await interaction.original_response()
# --- CLASE VIEW PARA PIEDRA, PAPEL O TIJERA ---

class PPTView(ui.View):
    def __init__(self, player1: discord.User, player2: discord.User = None):
        super().__init__(timeout=120) # 2 minutos para que ambos jueguen
        self.player1 = player1
        self.player2 = player2 if player2 else bot.user
        self.is_ai_game = (player2 is None)
        self.choices = {self.player1.id: None, self.player2.id: None}
        self.message = None

    async def on_timeout(self):
        """Deshabilita los botones si el tiempo se acaba."""
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ La partida de Piedra, Papel o Tijera ha expirado. ⌛", view=self)
                logger.warning(f"[PPT] Partida entre {self.player1.name} y {self.player2.name} ha expirado.")
            except discord.NotFound:
                pass

    def get_winner(self):
        """Determina el ganador de la ronda."""
        p1_choice = self.choices[self.player1.id]
        p2_choice = self.choices[self.player2.id]
        
        if p1_choice == p2_choice:
            return None, "¡Es un empate!"

        win_conditions = {
            "Piedra 🗿": "Tijera ✂️",
            "Tijera ✂️": "Papel 📄",
            "Papel 📄": "Piedra 🗿"
        }

        if win_conditions[p1_choice] == p2_choice:
            return self.player1, f"**{self.player1.name}** gana!"
        else:
            return self.player2, f"**{self.player2.name}** gana!"

    @ui.button(label="Piedra 🗿", style=discord.ButtonStyle.secondary, custom_id="ppt_rock")
    async def rock(self, interaction: discord.Interaction, button: ui.Button):
        await self.process_choice(interaction, "Piedra 🗿")

    @ui.button(label="Papel 📄", style=discord.ButtonStyle.secondary, custom_id="ppt_paper")
    async def paper(self, interaction: discord.Interaction, button: ui.Button):
        await self.process_choice(interaction, "Papel 📄")

    @ui.button(label="Tijera ✂️", style=discord.ButtonStyle.secondary, custom_id="ppt_scissors")
    async def scissors(self, interaction: discord.Interaction, button: ui.Button):
        await self.process_choice(interaction, "Tijera ✂️")

    async def process_choice(self, interaction: discord.Interaction, choice: str):
        # Verificar si el usuario que interactúa es uno de los jugadores
        if interaction.user.id not in [self.player1.id, self.player2.id]:
            await interaction.response.send_message("No eres parte de esta partida.", ephemeral=True)
            return

        # Verificar si el jugador ya ha elegido
        if self.choices[interaction.user.id] is not None:
            await interaction.response.send_message("Ya has hecho tu elección.", ephemeral=True)
            return

        # Guardar la elección del jugador
        self.choices[interaction.user.id] = choice

        # Lógica para juego contra la IA
        if self.is_ai_game:
            self.choices[self.player2.id] = random.choice(["Piedra 🗿", "Papel 📄", "Tijera ✂️"])
            await self.end_game(interaction)
        
        # Lógica para juego JvJ
        else:
            # Informar al jugador que su elección fue registrada (en secreto)
            await interaction.response.send_message(f"Has elegido **{choice}**. Esperando al otro jugador...", ephemeral=True)
            
            # Si ambos jugadores han elegido, terminar el juego
            if all(self.choices.values()):
                # Necesitamos usar follow-up en el mensaje original, no en la interacción efímera
                await self.end_game(interaction, is_pvp=True)

    async def end_game(self, interaction: discord.Interaction, is_pvp: bool = False):
        """Finaliza el juego, muestra los resultados y deshabilita los botones."""
        winner, result_text = self.get_winner()

        p1_choice = self.choices[self.player1.id]
        p2_choice = self.choices[self.player2.id]

        # Deshabilitar botones
        for item in self.children:
            item.disabled = True

        final_message = (
            f"**¡Resultados!**\n"
            f"➡️ {self.player1.mention} eligió: **{p1_choice}**\n"
            f"⬅️ {self.player2.mention} eligió: **{p2_choice}**\n\n"
            f"🎉 **{result_text}** 🎉"
        )
        
        logger.info(f"[PPT] Partida finalizada. {self.player1.name} ({p1_choice}) vs {self.player2.name} ({p2_choice}). Resultado: {result_text}")
        # En JvJ, la interacción es efímera, por lo que editamos el mensaje original.
        # En IA, la interacción no ha sido respondida, así que podemos editarla directamente.
        if is_pvp:
            await self.message.edit(content=final_message, view=self)
        else:
            await interaction.response.edit_message(content=final_message, view=self)
        
        self.stop()
@bot.tree.command(name="ppt", description="Inicia una partida de Piedra, Papel o Tijera.")
@app_commands.describe(oponente="Opcional: Menciona a un jugador para JvJ. Si se omite, jugarás contra la IA.")
async def ppt_command(interaction: discord.Interaction, oponente: discord.Member = None):
    if oponente == interaction.user:
        await interaction.response.send_message("No puedes jugar contra ti mismo. 😅", ephemeral=True)
        return
    if oponente == bot.user:
        oponente = None

    view = PPTView(player1=interaction.user, player2=oponente)

    if oponente is None:
        initial_message = f"**¡Piedra, Papel o Tijera contra la IA!** 🤖\n{interaction.user.mention}, ¡haz tu elección!"
    else:
        initial_message = f"**¡Duelo de Piedra, Papel o Tijera!** ⚔️\n{interaction.user.mention} vs {oponente.mention}\n¡Ambos deben elegir en secreto!"

    logger.info(f"[PPT] Nueva partida iniciada por {interaction.user.name} contra {'IA' if oponente is None else oponente.name}.")
    await interaction.response.send_message(content=initial_message, view=view)
    # Guardamos el mensaje para poder editarlo más tarde
    view.message = await interaction.original_response()

if __name__ == "__main__":
    # Reemplaza 'TU_TOKEN_AQUI' con el token real de tu bot
    bot.run('TU_TOKEN_AQUI')