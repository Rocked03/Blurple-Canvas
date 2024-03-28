import asyncio
from datetime import datetime, timezone
from functools import partial

from objects.user import Cooldown


class CooldownManager:
    def __init__(self):
        self.cooldowns: dict[tuple[int, int], datetime] = {}
        self.waits: dict[tuple[int, int], asyncio.Task] = {}

    async def add_cooldown(
        self,
        cooldown: Cooldown,
        function: partial = None,
    ):
        self.cooldowns[(cooldown.user.id, cooldown.canvas.id)] = cooldown.cooldown_time
        self.waits[(cooldown.user.id, cooldown.canvas.id)] = asyncio.create_task(
            self.wait(cooldown.user.id, cooldown.canvas.id, function)
        )

    async def set_cooldown(
        self,
        cooldown: Cooldown,
        function: partial = None,
    ):
        await self.clear_cooldown(cooldown.user.id, cooldown.canvas.id)
        await self.add_cooldown(cooldown, function)

    async def wait(self, user_id: int, canvas_id: int, function: partial = None):
        cooldown = self.cooldowns.get((user_id, canvas_id))
        await asyncio.sleep((cooldown - datetime.now(timezone.utc)).total_seconds())
        if (user_id, canvas_id) in self.cooldowns:
            del self.cooldowns[(user_id, canvas_id)]
            if function:
                if asyncio.iscoroutinefunction(function):
                    await function()
                else:
                    function()

    async def clear_cooldown(self, user_id: int, canvas_id: int):
        if (user_id, canvas_id) in self.cooldowns:
            del self.cooldowns[(user_id, canvas_id)]
        if (user_id, canvas_id) in self.waits:
            self.waits[(user_id, canvas_id)].cancel()
            del self.waits[(user_id, canvas_id)]

    def __getitem__(self, item):
        if isinstance(item, tuple):
            if len(item) == 2 and item in self.cooldowns:
                return self.cooldowns[item]
        return None
