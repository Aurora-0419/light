from __future__ import annotations

from dataclasses import dataclass

try:
    import rclpy
    from rclpy.node import Node
except Exception:  # pragma: no cover - depends on ROS runtime
    rclpy = None
    Node = object

try:
    from shadow_lamp_interfaces.msg import LightCommand
except Exception:  # pragma: no cover - messages exist after ROS build
    LightCommand = None

from light_control.ws2812_spi import SpiWs2812Driver


@dataclass
class LightCommandPayload:
    mode: str
    brightness: float
    color_temperature: float
    enabled: bool


@dataclass
class Ws2812Frame:
    enabled: bool
    pixels: list[tuple[int, int, int]]


def _scale_rgb(color: tuple[int, int, int], brightness: float) -> tuple[int, int, int]:
    clamped = max(0.0, min(1.0, brightness))
    return tuple(int(channel * clamped) for channel in color)


def build_frame_from_light_command(payload: LightCommandPayload, *, led_count: int = 1) -> Ws2812Frame:
    if not payload.enabled:
        return Ws2812Frame(enabled=False, pixels=[(0, 0, 0)] * led_count)

    base_color_map = {
        "warm_light_mode": (255, 135, 25),
        "cool_light_mode": (180, 210, 255),
        "tracking": (0, 255, 0),
        "shadow": (255, 180, 0),
        "error": (255, 0, 0),
        "idle": (0, 0, 255),
    }
    base = base_color_map.get(payload.mode, (255, 255, 255))
    color = _scale_rgb(base, payload.brightness)
    return Ws2812Frame(enabled=True, pixels=[color] * led_count)


class _LoggingWs2812Driver:
    def show(self, frame: Ws2812Frame) -> None:
        print(f"ws2812 frame enabled={frame.enabled} pixels={frame.pixels[:4]}")


class LightController(Node):
    """Consumes LightCommand and renders minimal WS2812-compatible frames."""

    def __init__(self, driver=None) -> None:
        if LightCommand is None:
            raise RuntimeError("shadow_lamp_interfaces.msg.LightCommand is unavailable; build the ROS workspace first")
        super().__init__("light_controller")
        self.led_count = int(self.declare_parameter("led_count", 60).value)
        self.spi_bus = int(self.declare_parameter("spi_bus", 1).value)
        self.spi_device = int(self.declare_parameter("spi_device", 0).value)
        self.spi_hz = int(self.declare_parameter("spi_hz", 2_400_000).value)
        self.use_spi_driver = bool(self.declare_parameter("use_spi_driver", True).value)
        self.driver = driver or self._make_default_driver()
        self.create_subscription(LightCommand, "/light/command", self._on_light_command, 10)

    def _make_default_driver(self):
        if not self.use_spi_driver:
            return _LoggingWs2812Driver()
        try:
            return SpiWs2812Driver(
                led_count=self.led_count,
                bus=self.spi_bus,
                device=self.spi_device,
                max_speed_hz=self.spi_hz,
            )
        except Exception as exc:  # pragma: no cover - depends on board hardware
            self.get_logger().warning(f"failed to initialize WS2812 SPI driver, falling back to logging: {exc}")
            return _LoggingWs2812Driver()

    def _on_light_command(self, msg) -> None:
        payload = LightCommandPayload(
            mode=msg.mode,
            brightness=msg.brightness,
            color_temperature=msg.color_temperature,
            enabled=msg.enabled,
        )
        frame = build_frame_from_light_command(payload, led_count=self.led_count)
        self.driver.show(frame)


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is unavailable in the current Python environment")
    rclpy.init()
    node = LightController()
    try:
        rclpy.spin(node)
    finally:
        close = getattr(getattr(node, "driver", None), "close", None)
        if callable(close):
            close()
        node.destroy_node()
        rclpy.shutdown()
