from postgresql import aioSQL


class ReminderPersist(aioSQL):

    _aioSQL__name = "reminder"
    _aioSQL__setup = "user int"

    async def toggle(self, cursor, user):
        c = await cursor.execute(
            f"SELECT user FROM {self._aioSQL__name} WHERE user=?", (user,)
        )
        data = await c.fetchall()
        if data:
            await cursor.execute(
                f"DELETE FROM {self._aioSQL__name} WHERE user=?", (user,)
            )
        else:
            await cursor.execute(
                f"INSERT INTO {self._aioSQL__name} VALUES (?)", (user,)
            )

        return await self.get(cursor, user)

    async def get(self, cursor, user):
        c = await cursor.execute(
            f"SELECT user FROM {self._aioSQL__name} WHERE user=?", (user,)
        )
        data = await c.fetchall()
        return bool(data)

    async def get_all(self, cursor):
        c = await cursor.execute(f"SELECT * FROM {self._aioSQL__name}")
        data = await c.fetchall()
        return [x[0] for x in data]
