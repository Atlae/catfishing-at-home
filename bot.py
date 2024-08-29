# This example requires the 'message_content' intent.

from collections import defaultdict
import typing
import discord
from discord.ext import commands
import random
from thefuzz import fuzz

import catfishing

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='^', intents=intents)

@bot.hybrid_command()
async def test(ctx):
    """A simple test command."""
    await ctx.send('Hello, world!')

@bot.hybrid_command()
async def catfish(ctx, page: typing.Optional[str] = None, players: commands.Greedy[discord.Member] = None):
    """Play catfishing"""
    await ctx.defer()

    CAT = "🐈"
    FISH = "🐟"
    CLOSE_UN_OEUF = "🥚"
    CONGRATS = "🎉"
    catfish_record = ""
    fail_color = 0xef4444
    success_color = 0x41deb7
    close_enough_color = 0xdcd34d
    pages = []

    if not players:
        players = [ctx.author]
    elif ctx.author not in players:
        players.append(ctx.author)
    
    for round in range(1, 11):
        page = catfishing.get_article(page) if page else catfishing.get_random_article()
        pages.append(page)
        print(page.title)
        categories = catfishing.get_categories(page.title)
        while not categories or len(categories) < 2:
            pages.pop()
            page = catfishing.get_random_article()
            pages.append(page)
            categories = catfishing.get_categories(page.title)
        first_embed = discord.Embed(title="Catfishing", description=f"{"\n".join(categories)}", color=0x022c22)
        first_embed.set_author(name=f"Players: {', '.join([player.display_name for player in players])} | Round {round}/10\nGuess the article from the categories")
        first_embed.set_footer(text="Powered by Wikipedia, inspired by Matthew at catfishing.net, original concept by Sumana Harihareswara, name and original implementation by Kevan Davis, lastly written by me, @atlae")
        await ctx.send(embed=first_embed)
        
        response = await bot.wait_for("message", check=lambda message: message.author in players)
        result_color: int
        print(response.content, page.title, fuzz.partial_ratio(response.content.lower(), page.title.lower()))
        if fuzz.partial_ratio(response.content.lower(), page.title.lower()) >= 85 or catfishing.get_categories(response.content) == categories:
            catfish_record += CAT
            result_color = success_color
        elif fuzz.partial_ratio(response.content.lower(), page.title.lower()) >= 75:
            catfish_record += CLOSE_UN_OEUF
            result_color = close_enough_color
        else:
            catfish_record += FISH
            result_color = fail_color
        if round == 5:
            catfish_record += "\n"
        congrats_emoji = CONGRATS if round == 10 and win_count >= 8 else ""

        win_count = catfish_record.count(CAT) + catfish_record.count(CLOSE_UN_OEUF) * 0.5
        second_embed = discord.Embed(title=page.title, 
                                     description=catfishing.get_condensed_summary(page.title) + f"\n\n[Read more]({page.fullurl})", 
                                     color=result_color)
        if (thumbnail := catfishing.get_thumbnail(page.title)):
            second_embed.set_thumbnail(url=thumbnail)
        second_embed.set_author(name=f"Players: {', '.join([player.display_name for player in players])} | Round {round}/10\nThe article was")
        second_embed.add_field(name="Record", value=f"""{win_count}/{round} {congrats_emoji}
{catfish_record}

{win_count} Correct
""")
        second_embed.set_footer(text="Powered by Wikipedia, inspired by Matthew at catfishing.net, original concept by Sumana Harihareswara, name and original implementation by Kevan Davis, lastly written by me, @atlae")
        await ctx.send(embed=second_embed)
        page = None
        if round == 10:
            await ctx.send("Thanks for playing! 🐈🐟🎉")
            await ctx.send(f"""catfishing (at home)
{win_count}/{round} {congrats_emoji}
{"\n".join([catfish_record.replace("\n", "")[i] + " [" + page.title + "](" + page.fullurl + ")" for i, page in enumerate(pages)])}""",
suppress_embeds=True)


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

@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name="catfishing"))
    print(f'We have logged in as {bot.user}')

from dotenv import load_dotenv
import os

load_dotenv()

bot.run(os.getenv('TOKEN'))
