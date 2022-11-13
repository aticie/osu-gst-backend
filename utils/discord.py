import os

import aiohttp


async def user_join_guild(user_id: str, access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    guild_id = os.getenv("DISCORD_GUILD_ID")
    async with aiohttp.ClientSession(headers=headers) as sess:
        async with sess.put(f"/guilds/{guild_id}/members/{user_id}") as resp:
            if resp.status != 200:
                print(f"Discord returned non-200: {resp.status}")
                resp_text = await resp.text()
                print(f"Response: {resp_text}")

    return
