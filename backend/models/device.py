from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User


@dataclass(frozen=True)
class DeviceType:
    """A preconfigured device type with its client identifier."""

    platform: str
    client: str


KNOWN_DEVICES: dict[str, DeviceType] = {
    "web": DeviceType(platform="Web", client="web"),
    "grout": DeviceType(platform="muOS", client="grout"),
    "argosy-launcher": DeviceType(platform="Android", client="argosy-launcher"),
}


class Device(BaseModel):
    __tablename__ = "devices"
    __table_args__ = (
        Index(
            "ix_devices_user_client_identifier",
            "user_id",
            "client_device_identifier",
            unique=True,
        ),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    name: Mapped[str | None] = mapped_column(String(255))
    platform: Mapped[str | None] = mapped_column(String(50))
    client: Mapped[str | None] = mapped_column(String(50))
    client_version: Mapped[str | None] = mapped_column(String(50))

    ip_address: Mapped[str | None] = mapped_column(String(45))
    mac_address: Mapped[str | None] = mapped_column(String(17))
    hostname: Mapped[str | None] = mapped_column(String(255))

    # Stable identifier supplied by the client itself (install UUID, hardware ID),
    # used to dedupe re-registrations of the same device across token resets.
    client_device_identifier: Mapped[str | None] = mapped_column(String(255))

    last_seen: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )

    user: Mapped[User] = relationship(lazy="joined")
