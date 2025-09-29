import discord
from discord.ext import commands
from discord import app_commands, ui, TextStyle
import random
import logging
import os

# --- CONFIGURACIÓN DE LOGS ---
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- CONSTANTES Y LÓGICA DE JUEGO ---
SIMBOLO_X = '❌'
SIMBOLO_O = '⭕'
CASILLA_VACIA_INT = '-'
EMOJI_VACIA = '⬜'

# --- DATOS PARA EL JUEGO DE DUELO ---
DUELOS_DATA = {
    "¡Luchas como un granjero!": {
        "correcta": "¡Qué apropiado! ¡Tú peleas como una vaca!",
        "incorrectas": ["¡No soy un granjero!", "¡Tu mamá es una granjera!", "¡Cállate!"]
    },
    "¡Pronto detendré tu absurdo comportamiento de pirata!": {
        "correcta": "Si quisiera un sermón, iría a la iglesia.",
        "incorrectas": ["¡No soy un pirata!", "¿Ah, sí?", "¡Eso es imposible!"]
    },
    "¡Mi pañuelo limpiará tu sangre!": {
        "correcta": "Ah, ¿entonces ya has elegido uno?",
        "incorrectas": ["¡Qué asco!", "¡No vas a tocarme!", "¡Qué amenaza tan tonta!"]
    },
    "¡He hablado con simios más educados que tú!": {
        "correcta": "Me alegra que asistieras a tu reunión familiar.",
        "incorrectas": ["¡No soy un simio!", "¿Y qué?", "¡Estás mintiendo!"]
    },
    "¡No hay palabras para describir mi náusea!": {
        "correcta": "Sí que las hay, solo que nunca las aprendiste.",
        "incorrectas": ["¿Te sientes mal?", "¡Pues vete!", "¡Hueles peor!"]
    }
}

def get_winner(board: list, symbol: str) -> bool:
    """Verifica si hay un ganador en el tablero."""
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    return any(all(board[i]==symbol for i in combo) for combo in wins)

def is_draw(board: list) -> bool:
    """Verifica si el juego terminó en empate."""
    return CASILLA_VACIA_INT not in board

def get_ia_move(board: list, ia_symbol: str, player_symbol: str) -> int:
    """Obtiene el próximo movimiento de la IA usando estrategia básica."""
    # Primero intenta ganar, luego bloquear al jugador
    for symbol_check in [ia_symbol, player_symbol]:
        for i in range(9):
            if board[i] == CASILLA_VACIA_INT:
                board[i] = symbol_check
                if get_winner(board, symbol_check):
                    board[i] = CASILLA_VACIA_INT
                    return i
                board[i] = CASILLA_VACIA_INT
    
    # Estrategia: centro, esquinas, luego cualquier casilla
    if board[4] == CASILLA_VACIA_INT: return 4
    corners = [i for i in [0,2,6,8] if board[i]==CASILLA_VACIA_INT]
    if corners: return random.choice(corners)
    empty_cells = [i for i in range(9) if board[i]==CASILLA_VACIA_INT]
    return random.choice(empty_cells) if empty_cells else -1

# --- BOT ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# --- VIEWS Y MODALS ---
class TicTacToeView(ui.View):
    def __init__(self, player1: discord.User, player2: discord.User = None):
        super().__init__(timeout=300)
        self.board = [CASILLA_VACIA_INT]*9
        self.players = (player1, player2) if player2 else (player1, None)
        self.symbols = {}
        self.current_player_index = 0
        self.is_ai_game = player2 is None
        self.message = None

        # Se asigna el bot como jugador 2 si es IA
        if self.is_ai_game:
            self.players = (player1, bot.user)
        self.symbols[self.players[0]] = SIMBOLO_X
        self.symbols[self.players[1]] = SIMBOLO_O

        for i in range(9):
            button = ui.Button(style=discord.ButtonStyle.secondary, label=EMOJI_VACIA, custom_id=str(i), row=i//3)
            button.callback = self.button_callback
            self.add_item(button)

    def update_board_display(self, winner: discord.User = None):
        """Actualiza la visualización del tablero."""
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
        """Procesa un movimiento del jugador."""
        try:
            logger.info(f"[TicTacToe] Jugador {interaction.user.name} movió a la casilla {index}.")
            self.board[index] = symbol
            
            if get_winner(self.board, symbol):
                self.update_board_display(winner=interaction.user)
                await interaction.edit_original_response(content=self.get_status_message(winner=interaction.user), view=self)
                logger.info(f"[TicTacToe] Partida finalizada. Ganador: {interaction.user.name}.")
                self.stop()
                return
                
            if is_draw(self.board):
                self.update_board_display()
                await interaction.edit_original_response(content=self.get_status_message(is_draw_game=True), view=self)
                logger.info("[TicTacToe] Partida finalizada en empate.")
                self.stop()
                return
                
            self.current_player_index = 1 - self.current_player_index
            
            if self.is_ai_game:
                await self.process_ia_move(interaction)
            else:
                self.update_board_display()
                await interaction.edit_original_response(content=self.get_status_message(), view=self)
                
        except Exception as e:
            logger.exception(f"Error en process_move: {e}")
            await interaction.followup.send("Ocurrió un error procesando el movimiento.", ephemeral=True)

    async def process_ia_move(self, interaction: discord.Interaction):
        """Procesa el movimiento de la IA."""
        try:
            ia_user = self.players[1]
            ia_symbol = self.symbols[ia_user]
            player_symbol = self.symbols[self.players[0]]
            ia_index = get_ia_move(self.board, ia_symbol, player_symbol)
            
            if ia_index != -1:
                self.board[ia_index] = ia_symbol
                logger.info(f"[TicTacToe] IA movió a la casilla {ia_index}.")
                
                if get_winner(self.board, ia_symbol):
                    self.update_board_display(winner=ia_user)
                    await interaction.edit_original_response(content=self.get_status_message(winner=ia_user), view=self)
                    logger.info(f"[TicTacToe] Partida finalizada. Ganador: {ia_user.name} (IA).")
                    self.stop()
                    return
                    
                if is_draw(self.board):
                    self.update_board_display()
                    await interaction.edit_original_response(content=self.get_status_message(is_draw_game=True), view=self)
                    logger.info("[TicTacToe] Partida finalizada en empate.")
                    self.stop()
                    return
                    
            self.current_player_index = 0
            self.update_board_display()
            await interaction.edit_original_response(content=self.get_status_message(), view=self)
            
        except Exception as e:
            logger.exception(f"Error en process_ia_move: {e}")

    async def button_callback(self, interaction: discord.Interaction):
        """Callback para los botones del tablero."""
        try:
            current_player = self.players[self.current_player_index]
            if interaction.user != current_player:
                await interaction.response.send_message("¡Espera tu turno! 🕰️", ephemeral=True)
                return
                
            index = int(interaction.data['custom_id'])
            if self.board[index] != CASILLA_VACIA_INT:
                await interaction.response.send_message("Esa casilla ya está ocupada. Elige otra.", ephemeral=True)
                return
                
            await interaction.response.defer()
            symbol = self.symbols[current_player]
            await self.process_move(interaction, index, symbol)
            
        except Exception as e:
            logger.exception(f"Error en button_callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Ocurrió un error inesperado.", ephemeral=True)

    async def on_timeout(self):
        """Se ejecuta cuando expira el timeout."""
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ La partida ha expirado por inactividad. ⌛", view=self)
                logger.warning(f"[TicTacToe] Partida entre {self.players[0].name} y {self.players[1].name} ha expirado.")
            except discord.NotFound:
                logger.warning("Mensaje no encontrado durante timeout de TicTacToe")
            except Exception as e:
                logger.exception(f"Error durante timeout de TicTacToe: {e}")

# --- MODAL Y VIEW PARA ADIVINA EL NÚMERO ---
class GuessNumberModal(ui.Modal, title='Adivina el Número'):
    def __init__(self, view):
        super().__init__()
        self.view = view
    
    guess = ui.TextInput(label='Escribe tu número aquí', style=TextStyle.short, placeholder='Ej: 25')
    
    async def on_submit(self, interaction: discord.Interaction):
        await self.view.process_guess(interaction, self.guess.value)

class AdivinaNumeroView(ui.View):
    def __init__(self, author: discord.User):
        super().__init__(timeout=180)
        self.author = author
        self.numero_secreto = random.randint(1, 50)
        self.intentos = 0
        self.max_intentos = 7
        self.message = None
        logger.info(f"[AdivinaElNumero] Nueva partida para {author.name}. Número: {self.numero_secreto}")

    async def on_timeout(self):
        """Se ejecuta cuando expira el timeout."""
        for item in self.children: 
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(content=f"⌛ ¡El tiempo se acabó! El número era **{self.numero_secreto}**.", view=self)
                logger.warning(f"[AdivinaElNumero] Partida de {self.author.name} ha expirado.")
            except discord.NotFound:
                logger.warning("Mensaje no encontrado durante timeout de AdivinaNumero")
            except Exception as e:
                logger.exception(f"Error durante timeout de AdivinaNumero: {e}")

    @ui.button(label="Hacer un intento", style=discord.ButtonStyle.primary, emoji="🤔")
    async def guess_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("No puedes jugar en la partida de otra persona.", ephemeral=True)
            return
        
        # Pasar la vista al modal
        modal = GuessNumberModal(self)
        await interaction.response.send_modal(modal)

    async def process_guess(self, interaction: discord.Interaction, guess_str: str):
        """Procesa un intento de adivinanza."""
        try:
            guess = int(guess_str)
            if not 1 <= guess <= 50:
                await interaction.response.send_message("El número debe estar entre 1 y 50.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Introduce un número válido.", ephemeral=True)
            return
            
        self.intentos += 1
        logger.info(f"[AdivinaElNumero] {self.author.name} intentó: {guess} (intento {self.intentos})")
        
        if guess == self.numero_secreto:
            self.stop()
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                content=f"🌟 ¡Felicidades {self.author.mention}! Adivinaste el número **{self.numero_secreto}** en {self.intentos} intentos!", 
                view=self
            )
            logger.info(f"[AdivinaElNumero] {self.author.name} ganó en {self.intentos} intentos.")
            return
            
        if self.intentos >= self.max_intentos:
            self.stop()
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                content=f"💔 Se acabaron tus intentos. El número era **{self.numero_secreto}**.", 
                view=self
            )
            logger.info(f"[AdivinaElNumero] {self.author.name} perdió. Número era {self.numero_secreto}.")
            return
            
        pista = "demasiado bajo ⬇️" if guess < self.numero_secreto else "demasiado alto ⬆️"
        intentos_restantes = self.max_intentos - self.intentos
        
        await interaction.response.edit_message(
            content=f"Tu número ({guess}) es **{pista}**. Te quedan **{intentos_restantes}** intentos."
        )

# --- VISTA PARA DUELO DE INSULTOS ---
class DueloView(ui.View):
    def __init__(self, retador: discord.User, retado: discord.User):
        super().__init__(timeout=300)
        self.players = (retador, retado)
        self.scores = {retador.id: 3, retado.id: 3}
        self.current_player_index = 0
        self.current_insulto = None
        self.message = None
        
        # Copiamos los insultos para no modificar el original
        self.insultos_disponibles = list(DUELOS_DATA.keys())
        
        self.setup_turn()

    def get_status_message(self, result_text: str = "") -> str:
        """Genera el mensaje de estado del duelo."""
        atacante = self.players[self.current_player_index]
        defensor = self.players[1 - self.current_player_index]
        
        header = f"🤺 **Duelo de Insultos entre {self.players[0].mention} y {self.players[1].mention}** 🤺\n"
        scores = f"❤️ {self.players[0].name}: **{self.scores[self.players[0].id]}** | ❤️ {self.players[1].name}: **{self.scores[self.players[1].id]}**\n\n"
        
        if result_text:
            return f"{header}{scores}{result_text}"

        turn_info = f"Turno de **{atacante.mention}**. ¡Elige una respuesta para el insulto de **{defensor.mention}**!\n"
        insulto_text = f"> **{self.current_insulto}**"
        
        return f"{header}{scores}{turn_info}{insulto_text}"
        
    def setup_turn(self):
        """Prepara la interfaz para el turno actual."""
        self.clear_items()
        
        if not self.insultos_disponibles: # Reinicia si se acaban
            self.insultos_disponibles = list(DUELOS_DATA.keys())
            
        self.current_insulto = random.choice(self.insultos_disponibles)
        self.insultos_disponibles.remove(self.current_insulto)
        
        datos_insulto = DUELOS_DATA[self.current_insulto]
        opciones_correctas = [datos_insulto['correcta']]
        opciones_incorrectas = random.sample(datos_insulto['incorrectas'], 2) # Elegimos 2 incorrectas
        
        opciones = opciones_correctas + opciones_incorrectas
        random.shuffle(opciones)
        
        select_options = [discord.SelectOption(label=op, value=op) for op in opciones]
        select = ui.Select(placeholder="Elige tu respuesta ingeniosa...", options=select_options)
        
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        """Callback para cuando un jugador elige una respuesta."""
        atacante = self.players[self.current_player_index]
        defensor = self.players[1 - self.current_player_index]
        
        if interaction.user != atacante:
            await interaction.response.send_message("¡No es tu turno de responder!", ephemeral=True)
            return

        selected_answer = interaction.data['values'][0]
        correct_answer = DUELOS_DATA[self.current_insulto]['correcta']

        if selected_answer == correct_answer:
            # La respuesta fue correcta, el defensor pierde un punto
            self.scores[defensor.id] -= 1
            logger.info(f"[Duelo] {atacante.name} respondió correctamente. {defensor.name} pierde una vida.")
            result_text = f"✅ ¡Correcto! **{defensor.name}** pierde una vida."
        else:
            # La respuesta fue incorrecta, el atacante pierde un punto
            self.scores[atacante.id] -= 1
            logger.info(f"[Duelo] {atacante.name} respondió incorrectamente y pierde una vida.")
            result_text = f"❌ ¡Incorrecto! La respuesta era:\n> *{correct_answer}*\n**{atacante.name}** pierde una vida."

        if self.scores[defensor.id] <= 0:
            await self.game_over(interaction, winner=atacante, loser=defensor)
            return
        elif self.scores[atacante.id] <= 0:
            await self.game_over(interaction, winner=defensor, loser=atacante)
            return
        
        # Cambiar de turno
        self.current_player_index = 1 - self.current_player_index
        self.setup_turn()
        
        await interaction.response.edit_message(content=self.get_status_message(result_text=result_text), view=self)

    async def game_over(self, interaction: discord.Interaction, winner: discord.User, loser: discord.User):
        """Finaliza el juego y declara un ganador."""
        self.stop()
        for item in self.children:
            item.disabled = True
        
        final_message = (
            f"🤺 **¡Duelo finalizado!** 🤺\n"
            f"🏆 **{winner.mention}** ha derrotado a **{loser.mention}** con su ingenio superior! 🏆"
        )
        await interaction.response.edit_message(content=final_message, view=self)
        logger.info(f"[Duelo] Partida finalizada. Ganador: {winner.name}.")

    async def on_timeout(self):
        self.stop()
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ El duelo ha expirado por inactividad. ⌛", view=self)
                logger.warning(f"[Duelo] Duelo entre {self.players[0].name} y {self.players[1].name} ha expirado.")
            except discord.NotFound:
                pass

# --- EVENTOS Y COMANDOS ---
@bot.event
async def on_ready():
    logger.info(f'Bot conectado como {bot.user} (ID: {bot.user.id})')
    print(f'Bot conectado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Sincronizados {len(synced)} comandos slash.")
        print(f"Sincronizados {len(synced)} comandos slash.")
    except Exception as e:
        logger.exception("Error sincronizando comandos:")
        print(f"Error sincronizando comandos: {e}")

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Error en comando: {error}")

@bot.tree.command(name="adivinar", description="Inicia un juego para adivinar un número entre 1 y 50.")
async def adivinar_command(interaction: discord.Interaction):
    try:
        view = AdivinaNumeroView(interaction.user)
        await interaction.response.send_message(
            f"🎉 **¡Adivina el número!** {interaction.user.mention}, he pensado en un número entre 1 y 50. Tienes {view.max_intentos} intentos.", 
            view=view
        )
        view.message = await interaction.original_response()
        logger.info(f"[Comando] Usuario {interaction.user.name} inició juego de adivinanza.")
    except Exception as e:
        logger.exception(f"Error en comando adivinar: {e}")
        await interaction.response.send_message("Ocurrió un error iniciando el juego.", ephemeral=True)

@app_commands.describe(oponente="Opcional: Menciona a un jugador para JvJ. Si se omite, jugarás contra la IA.")
async def tictactoe_command(interaction: discord.Interaction, oponente: discord.Member = None):
    try:
        if oponente == interaction.user:
            await interaction.response.send_message("No puedes jugar contra ti mismo. 😅", ephemeral=True)
            return
            
        if oponente == bot.user:
            oponente = None
            
        view = TicTacToeView(player1=interaction.user, player2=oponente)
        
        if oponente is None:
            initial_message = f"**¡Tres en Raya contra la IA!** 🤖\n{interaction.user.mention} eres {SIMBOLO_X}."
        else:
            initial_message = f"**¡Tres en Raya JvJ!** 🤝\n{interaction.user.mention} ({SIMBOLO_X}) vs {oponente.mention} ({SIMBOLO_O})."
            
        initial_message += f"\n\nTurno de **{interaction.user.mention}** ({SIMBOLO_X}). ¡Haz clic en una casilla!"
        
        await interaction.response.send_message(content=initial_message, view=view)
        view.message = await interaction.original_response()
        
        logger.info(f"[Comando] Usuario {interaction.user.name} inició TicTacToe {'vs IA' if oponente is None else f'vs {oponente.name}'}.")
        
    except Exception as e:
        logger.exception(f"Error en comando tictactoe: {e}")
        await interaction.response.send_message("Ocurrió un error iniciando el juego.", ephemeral=True)

@bot.tree.command(name="duelo", description="Reta a otro miembro a un duelo de insultos.")
@app_commands.describe(oponente="El miembro al que quieres retar.")
async def duelo_command(interaction: discord.Interaction, oponente: discord.Member):
    try:
        if oponente == interaction.user:
            await interaction.response.send_message("No puedes retarte a ti mismo, genio. 😒", ephemeral=True)
            return
        if oponente.bot:
            await interaction.response.send_message("No puedes retar a un bot. No tienen sentimientos que herir. 🤖", ephemeral=True)
            return
            
        view = DueloView(retador=interaction.user, retado=oponente)
        initial_message = view.get_status_message()
        
        await interaction.response.send_message(content=initial_message, view=view)
        view.message = await interaction.original_response()
        
        logger.info(f"[Comando] Usuario {interaction.user.name} inició un duelo contra {oponente.name}.")
        
    except Exception as e:
        logger.exception(f"Error en comando duelo: {e}")
        await interaction.response.send_message("Ocurrió un error iniciando el duelo.", ephemeral=True)

# Registro de los comandos
bot.tree.add_command(app_commands.Command(name="tictactoe", description="Inicia Tres en Raya.", callback=tictactoe_command))
bot.tree.add_command(app_commands.Command(name="duelo", description="Reta a otro miembro a un duelo de insultos.", callback=duelo_command))


if __name__ == "__main__":
    try:
        # Recuerda reemplazar 'TU_TOKEN_AQUÍ' con tu token real
        bot.run('TU_TOKEN_AQUÍ')
    except Exception as e:
        logger.exception(f"Error crítico al iniciar el bot: {e}")
        print(f"Error crítico: {e}")