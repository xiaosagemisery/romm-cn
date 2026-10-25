from pydantic import ConfigDict

from ..base import BaseModel, UTCDatetime


class DeviceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    name: str | None
    platform: str | None
    client: str | None
    client_version: str | None
    ip_address: str | None
    mac_address: str | None
    hostname: str | None
    client_device_identifier: str | None
    last_seen: UTCDatetime | None
    created_at: UTCDatetime
    updated_at: UTCDatetime


class DeviceCreateResponse(BaseModel):
    device_id: str
    name: str | None
    created_at: UTCDatetime
