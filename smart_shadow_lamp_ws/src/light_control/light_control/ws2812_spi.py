from __future__ import annotations

from collections.abc import Callable, Sequence


DEFAULT_SPI_BUS = 1
DEFAULT_SPI_DEVICE = 0
DEFAULT_SPI_HZ = 2_400_000
DEFAULT_RESET_BYTES = 80


def _encode_byte(value: int) -> list[int]:
    bits: list[int] = []
    clamped = max(0, min(255, int(value)))
    for bit in range(7, -1, -1):
        bits.extend((1, 1, 0) if (clamped & (1 << bit)) else (1, 0, 0))
    return bits


def _pack_bits(bits: Sequence[int]) -> bytes:
    out = bytearray()
    current = 0
    count = 0
    for bit in bits:
        current = (current << 1) | int(bool(bit))
        count += 1
        if count == 8:
            out.append(current)
            current = 0
            count = 0
    if count:
        out.append(current << (8 - count))
    return bytes(out)


def encode_ws2812_frame(
    pixels: Sequence[tuple[int, int, int]],
    *,
    reset_bytes: int = DEFAULT_RESET_BYTES,
) -> bytes:
    bits: list[int] = []
    for red, green, blue in pixels:
        for value in (green, red, blue):
            bits.extend(_encode_byte(value))
    return _pack_bits(bits) + bytes(max(0, int(reset_bytes)))


class SpiWs2812Driver:
    def __init__(
        self,
        *,
        led_count: int,
        bus: int = DEFAULT_SPI_BUS,
        device: int = DEFAULT_SPI_DEVICE,
        max_speed_hz: int = DEFAULT_SPI_HZ,
        reset_bytes: int = DEFAULT_RESET_BYTES,
        spi_factory: Callable[[], object] | None = None,
    ) -> None:
        if spi_factory is None:
            import spidev

            spi_factory = spidev.SpiDev
        self.led_count = led_count
        self.reset_bytes = reset_bytes
        self.spi = spi_factory()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = max_speed_hz
        self.spi.mode = 0

    def show(self, frame) -> None:
        pixels = list(frame.pixels[: self.led_count])
        if len(pixels) < self.led_count:
            pixels.extend([(0, 0, 0)] * (self.led_count - len(pixels)))
        self.spi.writebytes(list(encode_ws2812_frame(pixels, reset_bytes=self.reset_bytes)))

    def close(self) -> None:
        close = getattr(self.spi, "close", None)
        if callable(close):
            close()
