from dataclasses import dataclass

MODE_NAMES = {
    0x00: "daily",
    0x01: "24h",
    0x02: "custom",
    0x03: "timer",
    0x04: "disabled",
}

@dataclass(slots=True)
class HeadSnapshot:
    mode: int
    hour: int
    minute: int
    dosed_tenths_ml: int
    extra: bytes

    def mode_label(self) -> str:
        return MODE_NAMES.get(self.mode, f"0x{self.mode:02X}")

    def dosed_ml(self) -> float:
        return self.dosed_tenths_ml / 10

@dataclass(slots=True)
class DoserStatus:
    message_id: tuple[int, int] | None
    response_mode: int | None
    weekday: int | None
    hour: int | None
    minute: int | None
    heads: list[HeadSnapshot]
    tail_targets: list[int]
    tail_flag: int | None
    tail_raw: bytes
    lifetime_totals_tenths_ml: list[int]
    raw_payload: bytes = b""

    def lifetime_totals_ml(self) -> list[float]:
        return [total / 10.0 for total in self.lifetime_totals_tenths_ml]

    def update_from(self, other: 'DoserStatus') -> None:
        if other.heads:
            self.heads = other.heads
        if other.tail_targets:
            self.tail_targets = other.tail_targets
        if other.lifetime_totals_tenths_ml:
            self.lifetime_totals_tenths_ml = other.lifetime_totals_tenths_ml
        if other.message_id is not None:
            self.message_id = other.message_id
        if other.response_mode is not None:
            self.response_mode = other.response_mode
        if other.weekday is not None:
            self.weekday = other.weekday
        if other.hour is not None:
            self.hour = other.hour
        if other.minute is not None:
            self.minute = other.minute
        if other.tail_flag is not None:
            self.tail_flag = other.tail_flag
        if other.tail_raw:
            self.tail_raw = other.tail_raw
        if other.raw_payload:
            self.raw_payload = other.raw_payload
