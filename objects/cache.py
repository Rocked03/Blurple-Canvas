import asyncio

from objects.canvas import Canvas
from objects.pixel import Pixel
from sql.sqlManager import SQLManager
from objects.timer import Timer


class Cache:
    def __init__(
        self, sql_manager: SQLManager, *, canvas_id: int = None, canvas: Canvas = None
    ):
        self.canvas: Canvas = canvas
        self.queue: set[Pixel] = set()

        self.setup_event = asyncio.Event()
        asyncio.create_task(self.setup(sql_manager, self.setup_event, canvas_id))

        self.queue_event = asyncio.Event()
        asyncio.create_task(self.cycle_queue())

        self.force_refresh_event = asyncio.Event()
        self.force_refresh_event.set()

    async def setup(
        self, sql_manager: SQLManager, event: asyncio.Event, canvas_id: int = None
    ):
        timer = Timer()
        if not self.canvas:
            self.canvas = await sql_manager.fetch_canvas_by_id(canvas_id)
        print(f"Loading cache for canvas {self.canvas})")
        self.canvas.is_cache = True
        pixels = await sql_manager.fetch_pixels(self.canvas.id, self.canvas.bbox)
        self.canvas.pixels = {pixel.xy: pixel for pixel in pixels}
        timer.mark(
            f"Cache for canvas {self.canvas.name} ({self.canvas.id}) loaded", time=True
        )

        event.set()

    async def force_refresh(self, sql_manager: SQLManager):
        await self.setup_event.wait()
        self.force_refresh_event.clear()
        await self.setup(sql_manager, self.force_refresh_event)

    async def cycle_queue(self):
        await self.setup_event.wait()
        while True:
            await self.queue_event.wait()
            self.queue_event.clear()
            await self.force_refresh_event.wait()
            pixels = list(self.queue)
            self.queue.clear()

            for pixel in pixels:
                self.canvas.pixels[pixel.xy] = pixel

    async def add_pixel(self, pixel: Pixel):
        await self.setup_event.wait()
        self.queue.add(pixel)

    async def get_canvas(self):
        await self.setup_event.wait()
        return self.canvas
