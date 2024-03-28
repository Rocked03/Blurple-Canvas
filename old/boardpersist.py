from postgresql import aioSQL


class BoardPersist(aioSQL):

    _aioSQL__name = "board"
    _aioSQL__setup = "user int, board str"

    async def update(self, cursor, user, board):
        c = await cursor.execute(f"SELECT DISTINCT user FROM {self._aioSQL__name}")
        if user not in [x for y in await c.fetchall() for x in y]:
            if board:
                await cursor.execute(
                    f"INSERT INTO {self._aioSQL__name} VALUES (?, ?)", (user, board)
                )
        elif board:
            await cursor.execute(
                f"UPDATE {self._aioSQL__name} SET board=? WHERE user=?", (board, user)
            )
        else:
            await cursor.execute(
                f"DELETE FROM {self._aioSQL__name} WHERE user=?", (user,)
            )

        return await self.get(cursor, user)

    async def get(self, cursor, user):
        c = await cursor.execute(
            f"SELECT board FROM {self._aioSQL__name} WHERE user=?", (user,)
        )
        data = await c.fetchall()
        if data:
            return data[0][0]
        else:
            return None

    async def get_all_dict(self, cursor):
        c = await cursor.execute(f"SELECT * FROM {self._aioSQL__name}")
        data = await c.fetchall()
        return {d[0]: d[1] for d in data}
