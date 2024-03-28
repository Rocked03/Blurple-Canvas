from abc import ABCMeta, abstractmethod
import aiosqlite, asyncio

class aioSQL(metaclass=ABCMeta):

    @property
    @abstractmethod
    def __name(self): pass

    @property
    @abstractmethod
    def __setup(self): pass

    async def c(self, func, *args):
        async with aiosqlite.connect(f'sql/{self.__name}.db') as conn:
            async with conn.cursor() as cursor:
                result = await (getattr(self, func))(cursor, *args)
                await conn.commit()
        return result

    async def setup(self, cursor):
        await cursor.execute(f'CREATE TABLE if not exists {self._aioSQL__name} ({self._aioSQL__setup})')