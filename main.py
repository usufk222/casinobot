import discord
from discord import ui
import sqlite3
from bottoken import token
from random import randint

# Connecting to sqlite database
conn = sqlite3.connect("user_data.db")
# creating a cursor to interact with the database
cursor = conn.cursor()  

# Creating a table to store user data   
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id integer PRIMARY KEY,
    balance integer
)""")

# Function to insert or change user data
def update_user_balance(user_id, balance):
    cursor.execute("""
                   INSERT OR REPLACE INTO users (user_id, balance)
                   VALUES (?, ?)""", (user_id, balance))
    conn.commit()

# Function to retrieve user data
def get_user_balance(user_id):
    # Execute a query to retrieve user data
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    # Fetch the result
    result = cursor.fetchone()
    # Return the balance if the user exists, otherwise return None
    return result[0] if result else None

# View for the roulette game
class RouletteView(discord.ui.View):
    def __init__(self, user_id, bet, client, channel):
        super().__init__()
        self.user_id = user_id
        self.bet = bet
        self.client = client
        self.channel = channel

    # bet picker buttons for roulette
    @discord.ui.button(label="Green", style=discord.ButtonStyle.green)
    async def green_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button_click(interaction, "green")

    @discord.ui.button(label="Black", style=discord.ButtonStyle.secondary)
    async def black_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button_click(interaction, "black")

    @discord.ui.button(label="Red", style=discord.ButtonStyle.danger)
    async def red_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button_click(interaction, "red")
    
    async def handle_button_click(self, interaction: discord.Interaction, color: str):
        view = self
        for child in view.children:
            child.disabled = True

        await interaction.response.edit_message(content=f"You chose {color}!", view=view)
        result = self.client.roulette_game(self.user_id, self.bet, color)
        await self.channel.send(f"<@{self.user_id}> {result}")

# class for blackjack game
class BlackjackView(discord.ui.View):
    def __init__(self, user_id, bet, client, channel):
        super().__init__()
        self.user_id = user_id
        self.bet = bet
        self.client = client
        self.channel = channel

        suits = ["H", "A", "S", "C"]
        cards = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.card_values = {
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "10": 10,
            "J": 10,
            "Q": 10,
            "K": 10,
            "A": 11,
        }
        # card initalization
        self.cards_available = [(suit, card) for card in cards for suit in suits]

        # player/dealer initialiation
        self.dealer = {
            "hand": [],
            "value": 0
        }

        self.player = {
            "hand": [],
            "value": 0
        }

        # inital draws
        self.draw(self.player)
        self.draw(self.dealer)
        self.draw(self.player)
        self.draw(self.dealer)

        # dealer must always draw if under 17
        while self.dealer["value"] < 17:
            self.draw(self.dealer)

    def draw(self, player):
        card = self.cards_available.pop(randint(0, len(self.cards_available) - 1))
        player["hand"].append((card[1], self.card_values[card[1]]))
        player["value"] += self.card_values[card[1]]
        if player["value"] > 21:
            self.handle_aces(player)

    def handle_aces(self, player):
        if ('A', 11) in player["hand"]:
            pos = player["hand"].index(('A', 11))
            player["hand"][pos] = ('A', 1)
            player["value"] -= 10

    # user hit/stand buttons
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.secondary)
    async def black_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = self
        self.draw(self.player)
        dealers_show = [view.dealer['hand'][0][0]]
        for i in range(len(view.dealer['hand']) - 1):
            dealers_show.append("#")

        msg_content = f"Your cards: {view.player['hand']} ({view.player['value']})\nDealer's Cards: {dealers_show}"
        if not interaction.response.is_done():
            await interaction.response.edit_message(content=msg_content, view=view)
        else:
            await interaction.message.edit(content=msg_content, view=view)
        if self.player["value"] > 21:
            await self.game_end(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger)
    async def red_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.game_end(interaction)
        
    async def game_end(self, interaction: discord.Interaction):
        view = self
        for child in view.children:
            child.disabled = True
        result = None

        msg_content = f"Your cards: {view.player['hand']} ({view.player['value']})\nDealer's Cards: {view.dealer['hand']} ({view.dealer['value']})"
        if not interaction.response.is_done():
            await interaction.response.edit_message(content=msg_content, view=view)
        else:
            await interaction.message.edit(content=msg_content, view=view)

        if self.dealer["value"] > 21:
            if self.player["value"] > 21:
                await self.channel.send(f"<@{self.user_id}> Both hands are busts, your money is returned.")
            else:
                await self.channel.send(f"<@{self.user_id}> The dealer's hand is a bust, you win!")
                result = 1
        else:
            if self.player["value"] > 21:
                await self.channel.send(f"<@{self.user_id}> Your hand is a bust, you lose!")
                result = 2
            else:
                if self.player["value"] > self.dealer["value"]:
                    await self.channel.send(f"<@{self.user_id}> Your hand is better, you win!")
                    result = 1
                elif self.player["value"] < self.dealer["value"]:
                    await self.channel.send(f"<@{self.user_id}> The dealer's hand is better, you lose!")
                    result = 2
                else:
                    await self.channel.send(f"<@{self.user_id}> The hands are the same value, your money is returned!")

        if result == 1:
            update_user_balance(self.user_id, get_user_balance(self.user_id) + self.bet)
        else:
            update_user_balance(self.user_id, get_user_balance(self.user_id) - self.bet)

class MyClient(discord.Client):
    # Function to get user balance from database
    def get_bal(self, user_id):
        if get_user_balance(user_id) is None:
            update_user_balance(user_id, 10)
            return get_user_balance(user_id)
        else:
            return get_user_balance(user_id)
    
    def dice_game(self, user_id, bet):
        if self.get_bal(user_id) < bet:
            return "Your balance is not enough to bet that much"
        else:
            dice = randint(1, 6)
            user_dice = randint(1, 6)
            if user_dice > dice:
                update_user_balance(user_id, get_user_balance(user_id) + bet)
                return f"You won! Your dice: **{user_dice}**, Bot dice: **{dice}**\n***Your new balance: {get_user_balance(user_id)}***"
            elif user_dice < dice:
                update_user_balance(user_id, get_user_balance(user_id) - bet)
                return f"You lost! Your dice: **{user_dice}**, Bot dice: **{dice}**\n***Your new balance: {get_user_balance(user_id)}***"
            else:
                return f"It's a tie! Your dice: **{user_dice}**, Bot dice: **{dice}**\n***Your new balance: {get_user_balance(user_id)}***"
    
    def blackjack_game(self, user_id, bet):
        if get_user_balance(user_id) < bet:
            return f"<@{user_id}>Your balance is not enough to bet that much"
        else:
            view = BlackjackView()

    def roulette_game(self, user, bet, color):
        spin_num = randint(0, 37)
        if spin_num == 0 or spin_num == 37:
            if color == "green":
                update_user_balance(user, get_user_balance(user) + bet)
                winnings = bet * 17
                return f"The wheel landed on green! You won {winnings}!"
            else:
                update_user_balance(user, get_user_balance(user) - bet)
                return f"The wheel landed on green! You lost {bet}!"
        elif spin_num % 2 == 0:
            if color == "black":
                update_user_balance(user, get_user_balance(user) + bet)
                return f"The wheel landed on black! You won {bet}!"
            else:
                update_user_balance(user, get_user_balance(user) - bet)
                return f"The wheel landed on black! You lost {bet}!"
        else:
            if color == "red":
                update_user_balance(user, get_user_balance(user) + bet)
                return f"The wheel landed on red! You won {bet}!"
            else:
                update_user_balance(user, get_user_balance(user) - bet)
                return f"The wheel landed on red! You lost {bet}!"
 

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    # Function to check if messages are calling the bot
    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        msg = (message.content).lower()

        if message.author == client.user:
            return
        
        # checking user balance
        if msg in ("pr balance", "pr bal"):
            await message.channel.send(f"<@{message.author.id}> balance: {self.get_bal(message.author.id)}")
        
        # gifting other users balance
        if msg.startswith("pr gift"):
            raw_id = msg.split(" ")[3]

            receiver = int(raw_id[2:len(raw_id)-1])
            amount = int(msg.split(" ")[2])
            if amount > self.get_bal(message.author.id):
                await message.channel.send(f"<@{message.author.id}>Your balance is not enough to gift that much")
            else:
                update_user_balance(message.author.id, self.get_bal(message.author.id) - amount)
                update_user_balance(receiver, self.get_bal(receiver) + amount)
                await message.channel.send(f"<@{message.author.id}>The gift has been sent, your new balance is {self.get_bal(message.author.id)}")
        
        # casino game call messages
        if msg.startswith("pr dice"):
            bet = int(msg.split(" ")[2])
            await message.channel.send(f"<@{message.author.id}>\n{self.dice_game(message.author.id, bet)}")

        if msg.startswith("pr roulette"):
            bet = int(msg.split(" ")[2])
            if bet > self.get_bal(message.author.id):
                await message.channel.send(f"<@{message.author.id}>Your balance is not enough to bet that much")
            else:
                view = RouletteView(message.author.id, bet, self, message.channel)
                await message.channel.send("Place your bet!", view=view)  # Send the message with the View

        if msg.startswith("pr blackjack"):
            bet = int(msg.split(" ")[2])
            if bet > self.get_bal(message.author.id):
                await message.channel.send(f"<@{message.author.id}>Your balance is not enough to bet that much")
            else:
                view = BlackjackView(message.author.id, bet, self, message.channel)
                dealers_show = [view.dealer['hand'][0][0]]
                for i in range(len(view.dealer['hand']) - 1):
                    dealers_show.append("#")
                await message.channel.send(f"Your cards: {view.player['hand']} ({view.player['value']})\nDealer's Cards: {dealers_show}", view=view)
                
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(token)
