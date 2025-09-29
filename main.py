import discord
from discord.ext import commands
from discord import app_commands, ui
import random

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
        self.board[index] = symbol
        
        # 2. Verificar si el jugador humano ganó
        if get_winner(self.board, symbol):
            self.update_board_display(winner=interaction.user)
            await interaction.edit_original_response(content=self.get_status_message(winner=interaction.user), view=self)
            self.stop()
            return
            
        # 3. Verificar empate
        if is_draw(self.board):
            self.update_board_display()
            await interaction.edit_original_response(content=self.get_status_message(is_draw_game=True), view=self)
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
                self.stop()
                return

            # Verificar empate después de la IA
            if is_draw(self.board):
                self.update_board_display()
                await interaction.edit_original_response(content=self.get_status_message(is_draw_game=True), view=self)
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
        # Aquí puedes intentar editar el mensaje original si el bot aún tiene acceso al objeto del mensaje.


# --- BOT Y COMANDO SLASH ---

intents = discord.Intents.default()
# Reemplaza 'TU_TOKEN_AQUI' en la última línea
bot = commands.Bot(command_prefix='!', intents=intents) 

@bot.event
async def on_ready():
    """Sincroniza los comandos slash con Discord al iniciar."""
    print(f'Bot conectado como {bot.user}')
    try:
        # Sincronizar los comandos. Puede tardar unos minutos en aparecer.
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos slash.")
    except Exception as e:
        print(f"Error al sincronizar: {e}")

@bot.tree.command(name="tictactoe", description="Inicia una partida de Tres en Raya contra un jugador o la IA.")
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

    # Enviar el mensaje con los botones
    await interaction.response.send_message(
        content=initial_message,
        view=view
    )

bot.run('TU_TOKEN_AQUI')