from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Ns3Config(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    nodes: int = Field(default=5, ge=1, le=32)
    topology: Literal['star', 'ladder'] = 'star'
    duration_s: int = Field(default=60, ge=20, le=3600)
    interval_s: float = Field(default=5, ge=2, le=60)
    radio_range_m: float = Field(default=50, gt=0, le=1000)
    seed: int = Field(default=123456, ge=1, le=2147483647)
    payload_bytes: Literal[18] = 18
    radio_model: Literal['RangePropagationLossModel'] = 'RangePropagationLossModel'
    routing_mode: Literal['static-ipv6-bfs'] = 'static-ipv6-bfs'
    loss_model: Literal["udp-receive-discard"] = "udp-receive-discard"
    loss_probability: float = Field(default=0, ge=0, le=1)
    temperature_min_c: float = Field(default=20, ge=-50, le=124)
    temperature_max_c: float = Field(default=35, gt=-50, le=125)
    ack_timeout_s: float = Field(default=1, ge=.1, le=3)
    max_attempts: int = Field(default=3, ge=1, le=3)
    realtime: bool = True

    @model_validator(mode='after')
    def bounds(self):
        if self.temperature_min_c>=self.temperature_max_c:raise ValueError('Temperature minimum must be below maximum')
        return self
