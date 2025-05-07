import asyncio
from datetime import datetime, timezone, timedelta

import asyncpg
import cv2
import numpy
from PIL import Image
from asyncpg import Connection

from config import POSTGRES_CREDENTIALS
from objects.color import Palette
from objects.coordinates import Coordinates, BoundingBox
from objects.frame import Frame
from objects.historyRecord import HistoryRecord
from objects.pixel import Pixel
from objects.timer import Timer
from sql.sqlManager import SQLManager

DISTANT_PAST = datetime(1, 1, 1, tzinfo=timezone.utc)
FAR_FUTURE = datetime(9999, 1, 1, tzinfo=timezone.utc)

TIMER = Timer()


class TimelapseConfig:
    canvas: int | None = 2024
    bbox: BoundingBox | None = BoundingBox(Coordinates(0, 0), Coordinates(699, 699))
    frame_id: str | None = None
    start_time: datetime = DISTANT_PAST
    end_time: datetime = FAR_FUTURE

    scale: int = 1
    fps: int = 60
    frequency: int = 450  # in seconds
    end_hang_time: int = 5  # in seconds
    end_card_transition_duration: int = 2  # in seconds
    end_card_length: int = 5  # in seconds

    end_card_path: str | None = "../resources/timelapse/end_card_2024.png"
    end_card_background_color: tuple[int, int, int, int] = (88, 101, 242, 255)

    @property
    def size(self) -> Coordinates:
        return self.bbox.size * self.scale


async def connect(credentials) -> Connection:
    return await asyncpg.connect(**credentials)


async def fetch_frame(config: TimelapseConfig, sql: SQLManager) -> Frame:
    if config.canvas:
        canvas = await sql.fetch_canvas_by_id(config.canvas)
        return await canvas.get_frame(None, config.bbox)
    else:
        return await sql.fetch_frame(config.frame_id)


async def fetch_history_records(
    config: TimelapseConfig, sql: SQLManager, frame: Frame
) -> list[HistoryRecord]:
    history = await sql.fetch_history_records_by_frame(frame, endTime=config.end_time)
    history.sort(key=lambda record: record.timestamp)
    return history


async def fetch_palette(sql: SQLManager, color_ids: list[int]) -> Palette:
    return await sql.fetch_colors(color_ids=color_ids)


def create_image_base_color(
    config: TimelapseConfig, palette: Palette | None, *, scale=False
) -> Image.Image:
    # return create_image_base_empty(config, palette.blank_color.rgba, scale=scale)
    return create_image_base_empty(config, (62, 70, 142, 255), scale=scale)


def create_image_base_empty(
    config: TimelapseConfig,
    color: tuple[int, int, int, int] = (0, 0, 0, 0),
    *,
    scale=False,
) -> Image.Image:
    return Image.new(
        "RGBA",
        (config.bbox.size * (config.scale if scale else 1)).to_tuple(),
        color,
    )


def create_end_card(config: TimelapseConfig) -> Image.Image | None:
    if not config.end_card_path:
        return None

    img = Image.new("RGBA", config.size.to_tuple(), config.end_card_background_color)
    with Image.open(config.end_card_path) as end_card:
        ratio = min(config.size.x / end_card.width, config.size.y / end_card.height)
        end_card = end_card.resize(
            (int(end_card.width * ratio), int(end_card.height * ratio)),
            resample=Image.LANCZOS,
        )
        img.paste(
            end_card,
            (
                (config.size.x - end_card.width) // 2,
                (config.size.y - end_card.height) // 2,
            ),
        )
    return img


def aggregate_history(
    config: TimelapseConfig,
    history: list[HistoryRecord],
    palette: Palette,
    *,
    start_time: datetime,
    end_time: datetime,
) -> list[list[Pixel]]:
    start_time = max(start_time, history[0].timestamp)
    end_time = min(end_time, history[-1].timestamp)

    timestamps: list[list[Pixel]] = []
    next_time = start_time + timedelta(seconds=config.frequency)
    current_pixels: list[Pixel] = []

    for record in history:
        if record.timestamp > end_time:
            break

        while record.timestamp >= next_time:
            timestamps.append(current_pixels)
            current_pixels = []
            next_time += timedelta(seconds=config.frequency)

        pixel = record.pixel
        pixel.color = palette[pixel.color.id]
        current_pixels.append(pixel)

    if current_pixels:
        timestamps.append(current_pixels)

    return timestamps


def generate_frames(
    config: TimelapseConfig, timestamps: list[list[Pixel]], frame: Frame
):
    frames = []
    base = create_image_base_empty(config)
    frames.append(base)

    for pixels in timestamps:
        frame_base = base.copy()
        for pixel in pixels:
            coordinates = frame.justified_coordinates(pixel.coordinates)
            frame_base.paste(
                pixel.color.rgba,
                (*(coordinates.to_tuple()), *((coordinates + 1).to_tuple())),
            )
        frames.append(frame_base)

    return frames


def combine_frames(
    config: TimelapseConfig, frames: list[Image.Image], palette: Palette
):
    image_base = create_image_base_color(config, palette, scale=True)
    image_base_blank = create_image_base_empty(config, scale=True)
    current_frame = image_base_blank.copy()

    combined_frames = []

    for frame in frames:
        frame_scaled = frame.resize(config.size.to_tuple(), resample=Image.NEAREST)

        mask = frame_scaled.copy()
        r, g, b, alpha = mask.split()
        alpha = alpha.point(lambda p: (p != 0) * 255)
        mask = Image.merge("RGBA", (r, g, b, alpha))

        current_frame.paste(image_base_blank, mask=mask)
        current_frame.paste(frame_scaled, mask=frame_scaled)

        full = image_base.copy()
        full.alpha_composite(current_frame)

        combined_frames.append(full)

    return combined_frames


def generate_transition_frames(
    config: TimelapseConfig, final_frame: Image.Image, end_card: Image.Image
):
    transition_frames = []
    transition_length = config.end_card_transition_duration * config.fps

    for i in range(transition_length):
        alpha = int(255 * i / transition_length)
        mask = Image.new("RGBA", config.size.to_tuple(), (0, 0, 0, alpha))

        transition_frame = final_frame.copy()
        transition_frame.paste(end_card, mask=mask)
        transition_frames.append(transition_frame)

    return transition_frames


def combine_all_frames(
    config: TimelapseConfig,
    frames: list[Image.Image],
    transition_frames: list[Image.Image],
    end_card: Image.Image | None,
):
    hang_frames = [frames[-1]] * (config.end_hang_time * config.fps)
    end_card_frames = [end_card] * (config.end_card_length * config.fps)

    all_frames = frames + hang_frames + transition_frames + end_card_frames
    return all_frames


def generate_video(config: TimelapseConfig, frames: list[Image.Image]):
    filename = f"Timelapse {config.canvas} {config.bbox} x{config.scale}"
    video = cv2.VideoWriter(
        f"generated/{filename}.mp4",
        cv2.VideoWriter_fourcc(*"mp4v"),
        config.fps,
        config.size.to_tuple(),
    )

    for frame in frames:
        video.write(cv2.cvtColor(numpy.array(frame), cv2.COLOR_RGB2BGR))

    return video


async def main():
    config = TimelapseConfig()

    conn = await connect(POSTGRES_CREDENTIALS)
    sql = SQLManager(conn)
    TIMER.mark("Connected to SQL")

    frame = await fetch_frame(config, sql)
    TIMER.mark("Fetched frame")

    history = await fetch_history_records(config, sql, frame)
    TIMER.mark("Fetched history records")
    print(f"Total history records: {len(history)}")

    color_ids = {record.pixel.color.id for record in history}
    palette = await fetch_palette(
        sql, list(color_ids) + [1]
    )  # 1 is the default color (blank)
    TIMER.mark("Fetched palette")

    await sql.close()

    end_card = create_end_card(config)
    TIMER.mark("Created end card")

    timestamps = aggregate_history(
        config, history, palette, start_time=config.start_time, end_time=config.end_time
    )
    TIMER.mark("Aggregated history")
    print(f"Total timestamps: {len(timestamps)}")

    print("--- Generating frames... ---")
    frames = generate_frames(config, timestamps, frame)
    TIMER.mark("Generated frames")

    print("--- Combining frames... ---")
    combined_frames = combine_frames(config, frames, palette)
    TIMER.mark("Combined frames")

    if end_card:
        print("--- Generating transition frames... ---")
        transition_frames = generate_transition_frames(
            config, combined_frames[-1], end_card
        )
        TIMER.mark("Generated transition frames")
    else:
        transition_frames = []

    print("--- Creating and saving video... ---")
    all_frames = combine_all_frames(
        config, combined_frames, transition_frames, end_card
    )
    TIMER.mark("Combined all frames")

    video = generate_video(config, all_frames)
    TIMER.mark("Generated video")

    video.release()
    TIMER.mark("Saved video")


if __name__ == "__main__":
    asyncio.run(main())
