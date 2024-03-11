import asyncio

from objects.canvas import Canvas
from objects.pixel import Pixel
from objects.sqlManager import SQLManager
from objects.timer import Timer


class Cache:
    def __init__(
        self, sql_manager: SQLManager, *, canvas_id: int = None, canvas: Canvas = None
    ):
        self.sql_manager: SQLManager = sql_manager

        self.canvas: Canvas = canvas
        self.queue: set[Pixel] = set()

        self.setup_event = asyncio.Event()
        asyncio.create_task(self.setup(canvas_id))

        self.queue_event = asyncio.Event()
        asyncio.create_task(self.cycle_queue())

    async def setup(self, canvas_id: int):
        timer = Timer()
        if not self.canvas:
            self.canvas = await self.sql_manager.fetch_canvas_by_id(canvas_id)
        self.canvas.is_cache = True
        pixels = await self.sql_manager.fetch_pixels(self.canvas.id, self.canvas.bbox)
        self.canvas.pixels = {pixel.xy: pixel for pixel in pixels}
        timer.mark(f"Cache for canvas {canvas_id} loaded", time=True)

        self.setup_event.set()

    async def cycle_queue(self):
        await self.setup_event.wait()
        while True:
            await self.queue_event.wait()
            self.queue_event.clear()
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
