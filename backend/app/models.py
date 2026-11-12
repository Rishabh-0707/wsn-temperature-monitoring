from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator

class Run(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    run_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    source: Literal["cooja", "ns3", "hardware", "manual"] = "cooja"
    simulator: Literal["cooja", "ns3"] | None = None
    started_at: AwareDatetime
    duration_s: float = Field(gt=0, le=604800)
    nodes: int = Field(ge=1, le=32)
    telemetry_complete: bool = False

class Reading(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    run_id: str = Field(default="manual", max_length=100)
    node_id: int = Field(ge=1, le=32)
    temperature: float = Field(ge=-50, le=125)
    sequence_number: int = Field(ge=1, le=4294967295)
    timestamp: AwareDatetime
    boot_id: int = Field(default=0, ge=0, le=4294967295)
    sim_time_us: int | None = Field(default=None, ge=0)
    payload_bytes: int = Field(default=18, ge=1, le=127)

class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    event_id: str = Field(min_length=1, max_length=100)
    type: Literal["tx", "rx", "sample", "ack", "failed", "no_route", "status", "energy", "control", "started", "completed", "initialized", "online", "offline", "forward", "drop", "ack_timeout", "retry", "route_established", "route_changed"]
    node_id: int = Field(ge=0, le=32)
    sim_time_us: int = Field(ge=0)
    boot_id: int = Field(default=0, ge=0, le=4294967295)
    sequence_number: int | None = Field(default=None, ge=1, le=4294967295)
    temperature_centi: int | None = Field(default=None, ge=-5000, le=12500)
    attempt: int | None = Field(default=None, ge=1, le=3)
    payload_bytes: int = Field(default=18, ge=1, le=127)
    sample_uptime_ms: int | None = Field(default=None, ge=0)
    duplicate_or_reordered: int | None = Field(default=None, ge=0, le=1)
    rank: int | None = Field(default=None, ge=0, le=65535)
    parent_mote_id: int | None = Field(default=None, ge=0, le=65535)
    cpu: int | None = Field(default=None, ge=0)
    lpm: int | None = Field(default=None, ge=0)
    deep_lpm: int | None = Field(default=None, ge=0)
    transmit: int | None = Field(default=None, ge=0)
    listen: int | None = Field(default=None, ge=0)
    ticks_per_second: int | None = Field(default=None, gt=0)
    control_kind: Literal["DIS", "DIO", "DAO", "DAO-ACK"] | None = None

    hop_count: int | None = Field(default=None, ge=0, le=32)
    path: list[Annotated[int, Field(ge=0, le=32)]] | None = Field(default=None, max_length=33)
    forwarding_node: int | None = Field(default=None, ge=0, le=32)
    next_hop: int | None = Field(default=None, ge=0, le=32)
    reason: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def required_fields(self):
        required = {
            "tx": ["sequence_number", "temperature_centi", "attempt"],
            "rx": ["sequence_number", "temperature_centi", "attempt"],
            "sample": ["sequence_number"], "ack": ["sequence_number"],
            "failed": ["sequence_number"], "no_route": ["sequence_number"],
            "status": ["rank", "parent_mote_id"],
            "energy": ["cpu", "lpm", "deep_lpm", "transmit", "listen", "ticks_per_second"],
            "control": ["control_kind"],
        }
        if any(getattr(self, f) is None for f in required.get(self.type, [])):
            raise ValueError(f"Missing required fields for {self.type}")
        if self.type in ("tx", "rx", "sample", "ack", "failed", "no_route", "retry", "ack_timeout") and self.node_id == 0:
            raise ValueError("Application data must originate at a sensor")
        return self
