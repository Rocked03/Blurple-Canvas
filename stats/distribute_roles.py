import asyncio
import discord
import logging
from config import TOKEN

logging.basicConfig(level=logging.INFO)


class Config:
    GUILD_ID = 412754940885467146
    ROLE_ID = 1369961169397219328
    USER_IDS_FILE = "generated/participants.txt"


intents = discord.Intents.default()
intents.members = True  # Required to fetch members

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    logging.info(f"Logged in as {client.user} (ID: {client.user.id})")
    guild = client.get_guild(Config.GUILD_ID)
    if guild is None:
        logging.error(f"Guild with ID {Config.GUILD_ID} not found.")
        await client.close()
        return

    role = guild.get_role(Config.ROLE_ID)
    if role is None:
        logging.error(f"Role with ID {Config.ROLE_ID} not found in guild.")
        await client.close()
        return

    try:
        with open(Config.USER_IDS_FILE, "r") as f:
            user_ids = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Failed to read user IDs file: {e}")
        await client.close()
        return

    logging.info(f"Assigning role to {len(user_ids)} users...")

    for user_id_str in user_ids:
        try:
            user_id = int(user_id_str)
            member = guild.get_member(user_id)
            if member is None:
                # Try fetching member from API if not in cache
                member = await guild.fetch_member(user_id)
            if member is None:
                logging.warning(f"User ID {user_id} not found in guild, skipping.")
                continue
            if role in member.roles:
                logging.info(f"User {user_id} already has the role, skipping.")
                continue
            await member.add_roles(role, reason="Role assignment script")
            logging.info(f"Role assigned to user {user_id}")
        except discord.NotFound:
            logging.warning(f"User ID {user_id} not found (NotFound), skipping.")
        except discord.Forbidden:
            logging.warning(
                f"Missing permissions to assign role to user {user_id}, skipping."
            )
        except Exception as e:
            logging.warning(f"Failed to assign role to user {user_id}: {e}")

    logging.info("Role assignment complete, logging out.")
    await client.close()


def main():
    client.run(TOKEN)


if __name__ == "__main__":
    main()
