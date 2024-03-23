from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator, Any, Optional
from typing import TYPE_CHECKING

from asyncpg import Connection, UndefinedFunctionError
from discord import Client

from objects.coordinates import BoundingBox
from objects.stats import Ranking, UserStats

if TYPE_CHECKING:
    from objects.canvas import Canvas
    from objects.color import Color, Palette
    from objects.guild import Participation, Guild
    from objects.historyRecord import HistoryRecord
    from objects.info import Info
    from objects.pixel import Pixel
    from objects.user import User, Cooldown


class SQLManager:
    def __init__(self, conn: Connection, bot: Client = None):
        self.conn = conn
        self.bot = bot

    async def close(self):
        await self.conn.close()

    async def fetch_canvas_all(self) -> Generator[Canvas, Any, None]:
        rows = await self.conn.fetch("SELECT * FROM canvas")

        from objects.canvas import Canvas

        return (Canvas(bot=self.bot, **rename_invalid_keys(row)) for row in rows)

    async def fetch_canvas_by_id(self, canvas_id: int) -> Optional[Canvas]:
        from objects.canvas import Canvas

        row = await self.conn.fetchrow("SELECT * FROM canvas WHERE id = $1", canvas_id)

        if row is None:
            return None

        return Canvas(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_canvas_by_name(self, canvas_name: str) -> Optional[Canvas]:
        from objects.canvas import Canvas

        if not canvas_name.isdigit():
            row = await self.conn.fetchrow(
                "SELECT * FROM canvas WHERE LOWER(name) LIKE $1", canvas_name.lower()
            )
        else:
            row = await self.conn.fetchrow(
                "SELECT * FROM canvas "
                "WHERE LOWER(name) LIKE $1 OR id = $2 "
                "ORDER BY CASE WHEN id = $2 THEN 1 ELSE 0 END DESC",
                canvas_name.lower(),
                int(canvas_name),
            )

        if row is None:
            return None

        return Canvas(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_canvas_by_event(
        self, event_id: int, canvas_ids: list[int] = None
    ) -> list[Canvas]:
        if canvas_ids:
            rows = await self.conn.fetch(
                "SELECT * FROM canvas WHERE event_id = $1 OR id = ANY($2)",
                event_id,
                canvas_ids,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT * FROM canvas WHERE event_id = $1", event_id
            )

        from objects.canvas import Canvas

        return [Canvas(bot=self.bot, **rename_invalid_keys(row)) for row in rows]

    async def fetch_colors(
        self, *, color_ids: list[int] = None, color_codes: list[str] = None
    ) -> Palette:
        if color_ids:
            rows = await self.conn.fetch(
                "SELECT c.*, p.guild_id, p.event_id, g.invite FROM color c "
                "LEFT JOIN participation p ON c.id = p.color_id "
                "LEFT JOIN guild g ON p.guild_id = g.id "
                "WHERE c.id = ANY($1)",
                color_ids,
            )
        elif color_codes:
            rows = await self.conn.fetch(
                "SELECT c.*, p.guild_id, p.event_id, g.invite FROM color c "
                "LEFT JOIN participation p ON c.id = p.color_id "
                "LEFT JOIN guild g ON p.guild_id = g.id "
                "WHERE c.code = ANY($1) "
                "ORDER BY c.id DESC",
                color_codes,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT c.*, p.guild_id, p.event_id, g.invite FROM color c "
                "LEFT JOIN participation p ON c.id = p.color_id "
                "LEFT JOIN guild g ON p.guild_id = g.id "
            )

        from objects.color import Color, Palette

        return Palette(Color(bot=self.bot, **rename_invalid_keys(row)) for row in rows)

    async def fetch_color_by_id(self, color_id: int) -> Color:
        return (await self.fetch_colors(color_ids=[color_id]))[0]

    async def fetch_colors_by_code(self, color_code: str) -> Palette:
        return await self.fetch_colors(color_codes=[color_code])

    async def fetch_colors_by_participation(self, event_id: int = None) -> Palette:
        if event_id:
            rows = await self.conn.fetch(
                "SELECT c.*, p.guild_id, p.event_id, g.invite FROM color c "
                "LEFT JOIN participation p ON c.id = p.color_id "
                "LEFT JOIN guild g ON p.guild_id = g.id "
                "WHERE p.event_id = $1 OR c.global = TRUE OR c.code = 'edit'",
                event_id,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT c.*, p.guild_id, p.event_id, g.invite FROM color c "
                "LEFT JOIN participation p ON c.id = p.color_id "
                "LEFT JOIN guild g ON p.guild_id = g.id "
                "WHERE c.global = TRUE OR c.code = 'edit'"
            )
        from objects.color import Color, Palette

        return Palette(Color(bot=self.bot, **rename_invalid_keys(row)) for row in rows)

    async def fetch_history_records(
        self, canvas_id: int, *, user_id: int = None
    ) -> Generator[HistoryRecord, Any, None]:
        if user_id:
            rows = await self.conn.fetch(
                "SELECT * FROM history WHERE canvas_id = $1 AND user_id = $2 ORDER BY timestamp",
                canvas_id,
                user_id,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT * FROM history WHERE canvas_id = $1 ORDER BY timestamp",
                canvas_id,
            )

        from objects.historyRecord import HistoryRecord

        return (HistoryRecord(bot=self.bot, **rename_invalid_keys(row)) for row in rows)

    async def fetch_participation(self, guild_id: int, event_id: int) -> Participation:
        row = await self.conn.fetchrow(
            (
                "SELECT p.*, g.manager_role, g.invite, c.code, c.name, c.emoji_name, c.emoji_id "
                "FROM participation p "
                "LEFT JOIN guild g ON p.guild_id = g.id "
                "LEFT JOIN public.color c ON c.id = p.color_id "
                "WHERE guild_id = $1 AND event_id = $2"
            ),
            guild_id,
            event_id,
        )

        from objects.guild import Participation

        return Participation(bot=self.bot, **rename_invalid_keys(row)) if row else None

    async def fetch_participation_by_event(self, event_id: int) -> list[Participation]:
        rows = await self.conn.fetch(
            (
                "SELECT p.*, g.manager_role, g.invite, c.code, c.name, c.emoji_name, c.emoji_id "
                "FROM participation p "
                "LEFT JOIN guild g ON p.guild_id = g.id "
                "LEFT JOIN public.color c ON c.id = p.color_id "
                "WHERE event_id = $1"
            ),
            event_id,
        )

        from objects.guild import Participation

        return [Participation(bot=self.bot, **rename_invalid_keys(row)) for row in rows]

    async def fetch_info(self) -> Info:
        row = await self.conn.fetchrow("SELECT * FROM info")
        from objects.info import Info

        return Info(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_pixels(self, canvas_id: int, bbox: BoundingBox) -> list[Pixel]:
        pixels = await self.conn.fetch(
            (
                "SELECT p.x, p.y, p.color_id "
                "FROM pixels p "
                "WHERE canvas_id = $1 AND "
                "x >= $2 AND x <= $4 AND y >= $3 AND y <= $5"
            ),
            canvas_id,
            *bbox.to_tuple(),
        )
        colors = {
            c["id"]: rename_invalid_keys(c)
            for c in await self.conn.fetch(
                "SELECT * FROM color WHERE id = ANY($1)",
                list(set(p["color_id"] for p in pixels)),
            )
        }
        for c in colors:
            colors[c].pop("_id")

        from objects.pixel import Pixel

        return [
            Pixel(
                bot=self.bot,
                **rename_invalid_keys(pixel),
                **colors[pixel["color_id"]],
            )
            for pixel in pixels
        ]

    async def fetch_user(self, user_id: int, *, insert_on_fail: User = None) -> User:
        row = await self.conn.fetchrow(
            "SELECT u.*, b.date_added, "
            "c.name, c.locked, c.event_id, c.width, c.height, c.cooldown_length "
            "FROM public.user u "
            "LEFT JOIN blacklist b ON u.id = b.user_id "
            "LEFT JOIN canvas c ON u.current_canvas_id = c.id "
            "WHERE u.id = $1",
            user_id,
        )
        if row:
            from objects.user import User

            return User(bot=self.bot, **rename_invalid_keys(row))
        elif insert_on_fail:
            await self.insert_user(insert_on_fail)
            return insert_on_fail
        else:
            return await self.insert_empty_user(user_id)

    async def fetch_guild(
        self, guild_id: int, *, insert_on_fail: Guild = None
    ) -> Guild:
        row = await self.conn.fetchrow(
            "SELECT * FROM guild WHERE id = $1",
            guild_id,
        )
        if row:
            from objects.guild import Guild

            guild = Guild(bot=self.bot, **rename_invalid_keys(row))
            if insert_on_fail and (
                insert_on_fail.invite or insert_on_fail.manager_role_id
            ):
                await self.update_guild(
                    guild,
                    invite=insert_on_fail.invite,
                    manager_role_id=insert_on_fail.manager_role_id,
                )
            return guild
        elif insert_on_fail:
            await self.insert_guild(insert_on_fail)
            return insert_on_fail
        else:
            return await self.insert_empty_guild(guild_id)

    async def fetch_cooldown(self, user_id: int, canvas_id: int) -> Cooldown:
        row = await self.conn.fetchrow(
            "SELECT * FROM cooldown WHERE user_id = $1 and canvas_id = $2",
            user_id,
            canvas_id,
        )

        from objects.user import Cooldown

        return Cooldown(bot=self.bot, **rename_invalid_keys(row)) if row else None

    async def fetch_blacklist(self):
        from objects.user import Blacklist

        rows = await self.conn.fetch("SELECT * FROM blacklist")
        return [Blacklist(bot=self.bot, **rename_invalid_keys(row)) for row in rows]

    async def fetch_leaderboard(
        self,
        canvas_id: int,
        *,
        user_id: int = None,
        max_rank: int = None,
        limit: int = None,
    ) -> list[Ranking]:
        if max_rank is not None:
            if limit is not None and limit < max_rank:
                limit = max_rank
            rankings = await self.conn.fetch(
                "WITH ranked AS (SELECT * FROM leaderboard WHERE canvas_id = $1), "
                "min_excluded_rank AS ("
                "   SELECT MAX(rank) AS rank "
                "   FROM (SELECT rank FROM ranked ORDER BY rank LIMIT $2) AS top_ranks) "
                "SELECT DISTINCT * FROM ("
                "   SELECT * FROM ranked "
                "   WHERE rank < (SELECT rank FROM min_excluded_rank) and rank <= $3 "
                "   UNION ALL "
                "   SELECT * FROM ranked WHERE user_id = $4 "
                ") as combined "
                "ORDER BY rank",
                canvas_id,
                limit + 1 if limit else None,
                max_rank,
                user_id if user_id else -1,
            )
        elif user_id is not None:
            rankings = await self.conn.fetch(
                "SELECT * FROM leaderboard "
                "WHERE canvas_id = $1 AND user_id = $2 "
                "LIMIT $3",
                canvas_id,
                user_id,
                limit,
            )
        else:
            rankings = await self.conn.fetch(
                "SELECT * FROM leaderboard WHERE canvas_id = $1 "
                "ORDER BY rank LIMIT $2",
                canvas_id,
                limit,
            )

        return [Ranking(bot=self.bot, **rename_invalid_keys(row)) for row in rankings]

    async def fetch_leaderboard_guild(
        self,
        canvas_id: int,
        guild_id: int,
        *,
        user_id: int = None,
        max_rank: int = None,
        limit: int = None,
    ) -> list[Ranking]:
        if max_rank is not None:
            if limit is not None and limit < max_rank:
                limit = max_rank
            rankings = await self.conn.fetch(
                "WITH ranked AS (SELECT * FROM leaderboard_guild WHERE canvas_id = $1 and guild_id = $5), "
                "min_excluded_rank AS ("
                "   SELECT MAX(rank) AS rank "
                "   FROM (SELECT rank FROM ranked ORDER BY rank LIMIT $2) AS top_ranks) "
                "SELECT DISTINCT * FROM ("
                "   SELECT * FROM ranked "
                "   WHERE rank < (SELECT rank FROM min_excluded_rank) and rank <= $3 "
                "   UNION ALL "
                "   SELECT * FROM ranked WHERE user_id = $4 "
                ") as combined "
                "ORDER BY rank",
                canvas_id,
                limit + 1 if limit else None,
                max_rank,
                user_id if user_id else -1,
                guild_id,
            )
        elif user_id is not None:
            rankings = await self.conn.fetch(
                "SELECT * FROM leaderboard_guild "
                "WHERE canvas_id = $1 AND user_id = $2 AND guild_id = $4 "
                "LIMIT $3",
                canvas_id,
                user_id,
                limit,
                guild_id,
            )
        else:
            rankings = await self.conn.fetch(
                "SELECT * FROM leaderboard_guild WHERE canvas_id = $1 and guild_id = $3 "
                "ORDER BY rank LIMIT $2",
                canvas_id,
                limit,
                guild_id,
            )

        return [Ranking(bot=self.bot, **rename_invalid_keys(row)) for row in rankings]

    async def fetch_ranking(
        self, canvas_id: int, user_id: int, *, guild_id: int = None
    ) -> Ranking:
        if guild_id is None:
            ranking = await self.fetch_leaderboard(canvas_id=canvas_id, user_id=user_id)
        else:
            ranking = await self.fetch_leaderboard_guild(
                canvas_id=canvas_id, user_id=user_id, guild_id=guild_id
            )
        return ranking[0] if ranking else None

    async def fetch_user_stats(self, user_id: int, canvas_id: int):
        row = await self.conn.fetchrow(
            "SELECT u.*, code, emoji_name, emoji_id, global, name, rgba "
            "FROM user_stats u LEFT JOIN color c "
            "ON u.most_frequent_color_id = c.id "
            "WHERE user_id = $1 AND canvas_id = $2",
            user_id,
            canvas_id,
        )

        rows = rename_invalid_keys(row)
        rows["total_pixels"] = int(rows["total_pixels"])
        return UserStats(bot=self.bot, **rows) if row else None

    async def insert_color(self, color: Color) -> int:
        return (
            await self.conn.fetch(
                (
                    "INSERT INTO color (code, emoji_name, emoji_id, global, name, rgba) "
                    "VALUES ($1, $2, $3, $4, $5, $6) "
                    "RETURNING id"
                ),
                color.code,
                color.emoji_name,
                color.emoji_id,
                color.is_global,
                color.name,
                color.rgba,
            )
        )[0]["id"]

    async def insert_participation(self, participation: Participation):
        await self.conn.execute(
            (
                "INSERT INTO participation (guild_id, event_id, color_id) "
                "VALUES ($1, $2, $3)"
            ),
            participation.guild_id,
            participation.event.id,
            participation.color.id,
        )

    async def insert_guild(self, guild: Guild):
        await self.conn.execute(
            ("INSERT INTO guild (id, manager_role, invite) " "VALUES ($1, $2, $3)"),
            guild.id,
            guild.manager_role,
            guild.invite,
        )

    async def insert_empty_guild(self, guild_id: int) -> Guild:
        from objects.guild import Guild

        guild = Guild(
            _id=guild_id,
            manager_role=None,
            invite=None,
        )
        await self.insert_guild(guild)
        return guild

    async def insert_history_record(self, history_record: HistoryRecord):
        await self.conn.execute(
            (
                "INSERT INTO history (canvas_id, user_id, x, y, color_id, timestamp) "
                "VALUES ($1, $2, $3, $4, $5, $6)"
            ),
            history_record.pixel.canvas.id,
            history_record.user.id,
            history_record.pixel.x,
            history_record.pixel.y,
            history_record.pixel.color.id,
            history_record.timestamp,
        )

    async def insert_user(self, user: User):
        await self.conn.execute(
            (
                "INSERT INTO public.user (id, current_canvas_id, skip_confirm, cooldown_remind) "
                "VALUES ($1, $2, $3, $4)"
            ),
            user.id,
            user.current_canvas.id,
            user.skip_confirm,
            user.cooldown_remind,
        )

    async def insert_empty_user(self, user_id: int) -> User:
        from objects.user import User

        user = User(
            _id=user_id,
            current_canvas_id=None,
            skip_confirm=False,
            cooldown_remind=False,
        )
        await self.insert_user(user)
        return user

    async def insert_canvas(self, canvas: Canvas):
        if canvas.id:
            await self.conn.execute(
                (
                    "INSERT INTO canvas (id, name, event_id, width, height, cooldown_length) "
                    "VALUES ($1, $2, $3, $4, $5, $6)"
                ),
                canvas.id,
                canvas.name,
                canvas.event.id,
                canvas.width,
                canvas.height,
                canvas.cooldown_length,
            )
            return canvas.id
        else:
            returning = await self.conn.fetch(
                (
                    "INSERT INTO canvas (name, event_id, width, height, cooldown_length) "
                    "VALUES ($1, $2, $3, $4, $5) "
                    "RETURNING id"
                ),
                canvas.name,
                canvas.event.id,
                canvas.width,
                canvas.height,
                canvas.cooldown_length,
            )
            return returning[0]["id"]

    async def create_canvas_partition(self, canvas: Canvas):
        name = f"public.pixels_{canvas.id}"
        await self.conn.execute(
            f"CREATE TABLE {name} "
            f"PARTITION OF pixels "
            f"(PRIMARY KEY (canvas_id, x, y))"
            f"FOR VALUES IN ({canvas.id})",
        )

    async def update_guild(
        self, guild: Guild, invite: str = None, manager_role_id: int = None
    ):
        await self.conn.execute(
            "UPDATE guild SET manager_role = COALESCE($1, manager_role), invite = COALESCE($2, invite) WHERE id = $3",
            manager_role_id,
            invite,
            guild.id,
        )

    async def update_canvas(self, canvas: Canvas):
        await self.conn.execute(
            "UPDATE canvas "
            "SET name = $1, event_id = $2, cooldown_length = $3 WHERE id = $4",
            canvas.name,
            canvas.event.id,
            canvas.cooldown_length,
            canvas.id,
        )

    async def create_pixels(self, canvas: Canvas, color: Color):
        await self.conn.execute(
            "INSERT INTO pixels (canvas_id, x, y, color_id) "
            "SELECT $1, x, y, $2 FROM generate_series(0, $3) x, generate_series(0, $4) y",
            canvas.id,
            color.id,
            canvas.width - 1,
            canvas.height - 1,
        )

    async def set_pixel(self, pixel: Pixel):
        await self.set_pixels([pixel])

    async def set_pixels(self, pixels: list[Pixel]):
        await self.conn.executemany(
            "UPDATE pixels SET color_id = $1 WHERE canvas_id = $2 AND x = $3 AND y = $4",
            [(pixel.color.id, pixel.canvas.id, pixel.x, pixel.y) for pixel in pixels],
        )

    async def update_pixel(
        self,
        *,
        pixel: Pixel,
        user_id: int,
        timestamp: datetime = None,
        guild_id: int = None,
    ):
        if timestamp is None:
            timestamp = datetime.now(tz=timezone.utc)
        await self.update_pixels(
            pixels=[pixel], user_id=user_id, timestamp=timestamp, guild_id=guild_id
        )

    async def update_pixels(
        self,
        *,
        pixels: list[Pixel],
        user_id: int,
        timestamp: datetime = None,
        guild_id: int = None,
    ):
        if timestamp is None:
            timestamp = datetime.now(tz=timezone.utc)
        from objects.historyRecord import HistoryRecord

        records = [
            HistoryRecord(
                pixel=pixel, user_id=user_id, guild_id=guild_id, timestamp=timestamp
            )
            for pixel in pixels
        ]
        await self.conn.executemany(
            "INSERT INTO history (canvas_id, user_id, x, y, color_id, timestamp, guild_id) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            [
                (
                    record.pixel.canvas.id,
                    record.user.id,
                    record.pixel.x,
                    record.pixel.y,
                    record.pixel.color.id,
                    record.timestamp,
                    record.guild.id,
                )
                for record in records
            ],
        )

        await self.set_pixels(pixels)

    async def set_current_canvas(self, user: User):
        await self.fetch_user(user.id, insert_on_fail=user)
        await self.conn.execute(
            "UPDATE public.user SET current_canvas_id = $1 WHERE id = $2",
            user.current_canvas.id,
            user.id,
        )

    async def set_skip_confirm(self, user: User):
        await self.fetch_user(user.id, insert_on_fail=user)
        await self.conn.execute(
            "UPDATE public.user SET skip_confirm = $1 WHERE id = $2",
            user.skip_confirm,
            user.id,
        )

    async def set_cooldown_remind(self, user: User):
        await self.fetch_user(user.id, insert_on_fail=user)
        await self.conn.execute(
            "UPDATE public.user SET cooldown_remind = $1 WHERE id = $2",
            user.cooldown_remind,
            user.id,
        )

    async def add_cooldown(self, cooldown: Cooldown):
        await self.conn.execute(
            "INSERT INTO cooldown (user_id, canvas_id, cooldown_time) VALUES ($1, $2, $3)",
            cooldown.user.id,
            cooldown.canvas.id,
            cooldown.cooldown_time,
        )

    async def set_cooldown(self, cooldown: Cooldown):
        await self.conn.execute(
            "UPDATE cooldown SET cooldown_time = $1 WHERE user_id = $2",
            cooldown.cooldown_time,
            cooldown.user.id,
        )

    async def clear_cooldown(self, user_id: int):
        await self.conn.execute(
            "DELETE FROM cooldown WHERE user_id = $1",
            user_id,
        )

    async def add_blacklist(self, user_id: int):
        await self.conn.execute(
            "INSERT INTO blacklist (user_id, date_added) VALUES ($1, $2)",
            user_id,
            datetime.now(tz=timezone.utc),
        )

    async def remove_blacklist(self, user_id: int):
        await self.conn.execute(
            "DELETE FROM blacklist WHERE user_id = $1",
            user_id,
        )

    async def lock_canvas(self, canvas: Canvas):
        await self.conn.execute(
            "UPDATE canvas SET locked = TRUE WHERE id = $1",
            canvas.id,
        )

    async def unlock_canvas(self, canvas: Canvas):
        await self.conn.execute(
            "UPDATE canvas SET locked = FALSE WHERE id = $1",
            canvas.id,
        )

    async def trigger_delete_surpassed_cooldowns(self):
        try:
            await self.conn.execute("SELECT delete_surpassed_cooldowns()")
        except UndefinedFunctionError:
            await self.conn.execute(
                "CREATE OR REPLACE FUNCTION delete_surpassed_cooldowns() VOID AS $$"
                "BEGIN "
                "   DELETE FROM cooldown "
                "   WHERE cooldown_time < NOW(); "
                "END; "
                "$$ LANGUAGE plpgsql;"
            )
            await self.conn.execute("SELECT delete_surpassed_cooldowns()")


def rename_invalid_keys(data: dict) -> dict:
    renames = {
        "id": "_id",
        "global": "_global",
    }
    return {renames.get(k, k) if k in renames else k: v for k, v in data.items()}
