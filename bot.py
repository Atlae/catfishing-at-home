# This example requires the 'message_content' intent.

from collections import defaultdict
import typing
import discord
from discord.ext import commands
import random
from thefuzz import fuzz

import catfishing as catfish

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='^', intents=intents)

@bot.hybrid_command()
async def test(ctx):
    """A simple test command."""
    await ctx.send('Hello, world!')

#region Catfishing

# Constants for catfishing game
CAT = "🐈"
FISH = "🐟"
CLOSE_UN_OEUF = "🥚"
CONGRATS = "🎉"
FAIL_COLOR = 0xef4444
SUCCESS_COLOR = 0x41deb7
CLOSE_ENOUGH_COLOR = 0xdcd34d

# bot.round = 0
# bot.catfish_record = ""
# bot.pages = []
# bot.win_count = 0
type GameState = dict[str, typing.Any]
bot.game_state = defaultdict(dict[tuple[discord.Member], GameState])

@bot.hybrid_group(fallback='start')
async def catfishing(ctx, players: commands.Greedy[discord.Member] = None,
                     safeword: typing.Optional[str] = 'RIBULOSEBISPHOSPHATECARBOXYLASEOXYGENASE'):
    """Play a game of catfishing. Players must guess the article from the categories provided.
    
    Args:
        players: A list of players to play the game.
        safeword: Want to end early? The default is from https://xkcd.com/1039/.
    """
    await ctx.defer()
    print(bot.game_state)
    players, game_state = await validate_game(ctx, safeword, players)
    for round in range(1, 11):
        game_state["round"] = round
        await play_round(ctx, players, game_state)
    game_state["round"] += 1
    await end_game(ctx, players, game_state)

async def play_round(ctx, players, game_state: dict[str, typing.Any]):
    page = catfish.get_random_article()
    print(bot.game_state)
    print(game_state)
    game_state["pages"].append(page)
    print(page.title)
    categories = catfish.get_categories(page.title)
    while not categories or len(categories) < 4:
        game_state["pages"].pop()
        page = catfish.get_random_article()
        game_state["pages"].append(page)
        categories = catfish.get_categories(page.title)
    
    await ctx.send(embed=embed_builder(players, title="Catfishing", 
                                       description="\n".join(categories), color=0x022c22))
    
    response = await bot.wait_for("message", check=lambda message: message.author in players)

    # if message is in spoiler tags, ignore it
    while response.content.startswith("||") and response.content.endswith("||"):
        response = await bot.wait_for("message", check=lambda message: message.author in players)
    
    if response.content.upper() == game_state["safeword"].upper():
        game_state["catfish_record"] += "🛑"
        await ctx.send("Oh, sorry!")
        await end_game(ctx, players, game_state)

    result_color: int
    print(response.content, page.title, fuzz.partial_ratio(response.content.lower(), page.title.lower()))
    if fuzz.partial_ratio(response.content.lower(), page.title.lower()) >= 85 or catfish.get_categories(response.content) == categories:
        game_state["catfish_record"] += CAT
        result_color = SUCCESS_COLOR
    elif fuzz.partial_ratio(response.content.lower(), page.title.lower()) >= 75:
        game_state["catfish_record"] += CLOSE_UN_OEUF
        result_color = CLOSE_ENOUGH_COLOR
    else:
        game_state["catfish_record"] += FISH
        result_color = FAIL_COLOR
    if game_state["round"] == 5:
        game_state["catfish_record"] += "\n"

    game_state["win_count"] = game_state["catfish_record"].count(CAT) + game_state["catfish_record"].count(CLOSE_UN_OEUF) * 0.5
    game_state["win_count"] = int(game_state["win_count"]) if game_state["win_count"].is_integer() else game_state["win_count"]


    second_embed = embed_builder(players, title=page.title,
                                    description=catfish.get_condensed_summary(page.title) + f"\n\n[Read more]({page.fullurl})", 
                                    color=result_color, thumbnail=catfish.get_thumbnail(page.title))
    second_embed.add_field(name="Record", value=f"""{game_state["win_count"]}/{game_state["round"]}
{game_state["catfish_record"]}

{game_state["win_count"]} Correct
""")
    await ctx.send(embed=second_embed)

def embed_builder(players: list[discord.Member], title: str, description: str, 
                  color: int, thumbnail: str = None) -> discord.Embed:
    """Builds an embed object with the given parameters."""
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_author(name=f"Players: {', '.join([player.display_name for player in players])}")
    embed.set_footer(text="Powered by Wikipedia, inspired by Matthew at catfishing.net, original concept by Sumana Harihareswara, name and original implementation by Kevan Davis, lastly written by me, @atlae")
    return embed

async def validate_game(ctx, safeword: typing.Optional[str], 
                        players: list[discord.Member] = None) -> tuple[tuple[discord.Member], GameState]:
    """Validates the game state and returns it.

    Args:
        ctx (_type_): Interactions context object.
        safeword (typing.Optional[str]): Word to end the game early.
        players (list[discord.Member], optional): List of other players. Defaults to None.

    Raises:
        commands.UserInputError: One or more players are already in a game.

    Returns:
        tuple[tuple[discord.Member], GameState]: Tuple of players and game state, consisting of
            the safeword, round number, catfish record, pages, and win count.
    """
    if not players:
        players = [ctx.author]
    elif ctx.author not in players:
        players.append(ctx.author)
    players = tuple(players)
    if any(player in state for player in players for state in bot.game_state):
        await ctx.send("One or more players are already in a game.", ephemeral=True)
        raise commands.UserInputError("One or more players are already in a game.")
    bot.game_state[players] = {
        "safeword": safeword,
        "round": 0,
        "catfish_record": "",
        "pages": [],
        "win_count": 0
    }
    return players, bot.game_state[players]

@catfishing.command()
async def end(ctx):
    """End the current game of catfishing."""
    for players, game_state in bot.game_state.items():
        if ctx.author in players:
            game_state["catfish_record"] += "🏳️"
            await end_game(ctx, players, game_state)
            return
    await ctx.send("You need to start a game to end it, silly!", ephemeral=True)

async def end_game(ctx, players: list[discord.Member] = None, game_state: GameState = None):
    """End the current game of catfishing."""
    congrats_emoji = CONGRATS if game_state["round"] == 11 and game_state["win_count"] >= 8 else ""
    if game_state["round"] == 0:
        await ctx.send("You need to start a game to end it, silly!", ephemeral=True)
        return
    elif game_state["round"] < 11:
        await ctx.send("Sorry to see you go. Thanks for playing! 🐈🐟🎉")
    else:
        await ctx.send("Thanks for playing! 🐈🐟🎉")
    await ctx.send(f"""catfishing (at home)
    
{game_state["win_count"]}/{game_state["round"]} {congrats_emoji}
{"\n".join([game_state["catfish_record"].replace("\n", "")[i] + " [" + page.title + "](" + page.fullurl + ")" for i, page in enumerate(game_state["pages"])])}""",
suppress_embeds=True)
    del bot.game_state[players] # cleanup
    
#endregion
    
#region Phrasemongering

async def _top_n_users(ctx, n: int = 10, messages: typing.Optional[list[str]] = None) -> defaultdict[str, int]:
    user_message_count = defaultdict(int)
    if messages:
        for message in messages:
            user_message_count[message.author] += 1
    else:
        for channel in ctx.guild.text_channels:
            try:
                async for message in channel.history(limit=1000):
                    user_message_count[message.author] += 1
            except discord.Forbidden:
                print(f"Missing permissions to read messages in {channel.name}")
    return user_message_count

@bot.hybrid_command(name='top')
async def top_n_users(ctx, n: int = 10):
    """Lists the top n users by message count."""
    await ctx.defer()

    user_message_count = await _top_n_users(ctx, n)
    if user_message_count:
        sorted_users = sorted(user_message_count.items(), key=lambda item: item[1], reverse=True)
        top_users_list = "\n".join([f"1. {user.display_name}: {count} messages" for user, count in sorted_users[:n]])
        await ctx.send(f"### Top users by message count:\n\n{top_users_list}")
    else:
        await ctx.send("No messages found in the guild.")

@bot.hybrid_command()
async def phrasemonger(ctx, n: typing.Optional[int] = 10):
    """Sends a message whose content is grabbed from a random message in the guild."""
    await ctx.defer()
    await ctx.send("WARNING: Not entirely functional yet. This command is a work in progress.")
    messages = []
    for channel in ctx.guild.text_channels:
        try:
            print(channel)
            async for message in channel.history(limit=1000):
                messages.append(message)
        except discord.Forbidden:
            print(f"Missing permissions to read messages in {channel.name}")

    top_users = await _top_n_users(ctx, n, messages)
    
    if messages:
        message = random.choice(messages)
        while not message.content:
            message = random.choice(messages)
        author = message.author
        challenge = f"""
> {message.content}

1️⃣ {author}
2️⃣ {random.choice(list(top_users.keys())).display_name}
3️⃣ {random.choice(list(top_users.keys())).display_name}
4️⃣ {random.choice(list(top_users.keys())).display_name}
"""
        print(challenge)
        await ctx.send(challenge)
    else:
        await ctx.send("No messages found in the guild.")

#endregion

@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name="catfishing"))
    print(f'We have logged in as {bot.user}')

from dotenv import load_dotenv
import os

load_dotenv()

bot.run(os.getenv('TOKEN'))
