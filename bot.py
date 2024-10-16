import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio

intents=discord.Intents.all()

bot=commands.Bot(command_prefix='a!', intents=intents)

@bot.event
async def on_ready():
    slashes = await bot.tree.sync()
    print(f"Bot is online!")
    print(f"Synced {len(slashes)} slash commands")

@bot.command()
async def load(ctx, extension):
    await bot.load_extension(f"cmds.{extension}")
    await ctx.send(f'已載入 {extension}')

@bot.command()
async def unload(ctx, extension):
    await bot.unload_extension(f"cmds.{extension}")
    await ctx.send(f'已取消載入 {extension}')

@bot.command()
async def reload(ctx, extension):
    await bot.reload_extension(f"cmds.{extension}")
    await ctx.send(f'已重新載入 {extension}')

async def load_extenstions():
    for filename in os.listdir('./cmds'):
        if filename.endswith('.py'):
            await bot.load_extension(f"cmds.{filename[:-3]}")

async def main():
    async with bot:
        await load_extenstions()
        await bot.start(os.environ.get('token'))

async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        return await interaction.response.send_message(f"Command is currently on cooldown! Try again in **{error.retry_after:.2f}** seconds!")
    elif isinstance(error, app_commands.MissingPermissions):
        return await interaction.response.send_message(f"You're missing permissions to use that")
    else:
        print(f"An unexpected error occurred: {error}")

bot.tree.on_error = on_tree_error

if __name__ == '__main__':
    asyncio.run(main())
