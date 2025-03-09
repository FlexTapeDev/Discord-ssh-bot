import discord
from discord.ext import commands
from paramiko import SSHClient, AutoAddPolicy
import asyncio
import json

# Load config
with open("config.json", "r") as file:
    config = json.load(file)

client = SSHClient()
client.set_missing_host_key_policy(AutoAddPolicy())
global synced

# Create bot with command tree (slash commands)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync commands for a specific guild
    print(f"Logged in as {bot.user}")


# Slash command
def ssh_client(command):
    try:
        client.connect(config["sshAddr"], username=config["sshUser"], password=config["sshPass"])
        client.load_system_host_keys()


        stdin, stdout, stderr = client.exec_command(command)

        cmdOutput = stdout.read().decode('utf-8').strip()
        commandList = command.split(";") # [cd books, ls]

        # for i, cmd in enumerate(commandList):
        #     print(i) # Debug
        # print(len(cmdOutput))

        stdin.close()
        stderr.close()
        stdout.close()
        client.close()
        return cmdOutput, commandList
    except Exception as e:
        print(e)


def check_minecraft_server_status():
    command = "ps aux | grep 'playit\\|minecraft' | grep -v grep"
    cmdOutput, _ = ssh_client(command)

    if "playit" in cmdOutput and "minecraft" in cmdOutput:
        return True
    return False    


@bot.tree.command(name="command", description="Run a command on Raspberry PI")
async def command(interaction: discord.Interaction, *, command: str):
    try:

        await interaction.response.defer()

        cmdOutput, commandList = await asyncio.to_thread(ssh_client, command)

        if (isinstance(cmdOutput, str) and len(cmdOutput) < 1024):
                
            embed = discord.Embed(title=f"RASPBERRY PI", description=f"Command(s): **{'\n' + '\n'.join(commandList)}**", color=0xa9dbff)
            embed.add_field(name="Output", value=f"{cmdOutput}", inline=False)

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"```\nMessage over 1024 chars. ({len(cmdOutput)})\n```")
        
    except Exception as e:
        await interaction.followup.send_message(e)


@bot.tree.command(name="startserver", description="Will run the minecraft server.")
async def startserver(interaction: discord.Interaction):
    try:

        await interaction.response.defer()

        if not check_minecraft_server_status():
            try:
                embed = discord.Embed(title="Starting Server...", description="", color=0x58ff0c)
                await interaction.followup.send(embed=embed)

                await asyncio.to_thread(ssh_client, "cd minecraft-forge; ./RUN-FOR-SERVER")

            except Exception as e:
                print(e)

        else:
            await interaction.followup.send("Server already running")

    except Exception as e:
        await interaction.followup.send(e)


@bot.tree.command(name="stopserver", description="Stops the server.")
async def stopserver(interaction: discord.Integration):
    embed = discord.Embed(title="Stopping server...", color=0x9e0000)

    try:    
        if not check_minecraft_server_status():
            await interaction.response.send_message("Server is not running.")
        else:
            await interaction.response.defer()
            await asyncio.to_thread(ssh_client, "pkill -f 'playit-linux-aarch64'")
            await asyncio.to_thread(ssh_client, "sudo pkill -f 'java'")
            await interaction.followup.send(embed=embed)

    except Exception as e:
        print(e)


@bot.tree.command(name="reboot", description="Reboot RaspberryPI (if server is flaky reboot and start server.)")
async def reboot(interaction: discord.Interaction):
    embed = discord.Embed(title="Rebooting...", description="It may take up to 60 seconds.", color=0xff3b3b)
    
    try:
        await interaction.response.send_message(embed=embed)
    except discord.errors.InteractionResponded:
        pass

    try:
        await asyncio.to_thread(ssh_client, "sudo reboot")
    except Exception as e:
        print("Error during reboot:", e)
    
    await asyncio.sleep(60)

if __name__ == "__main__":
    bot.run(config["TOKEN"])