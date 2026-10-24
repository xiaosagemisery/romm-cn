from pydantic import ConfigDict, computed_field

from .base import BaseModel, UTCDatetime


class PlatformSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    fs_slug: str
    rom_count: int
    name: str
    igdb_slug: str | None
    moby_slug: str | None
    hltb_slug: str | None
    libretro_slug: str | None
    custom_name: str | None = None
    description: str | None = None
    igdb_id: int | None = None
    sgdb_id: int | None = None
    moby_id: int | None = None
    launchbox_id: int | None = None
    ss_id: int | None = None
    ra_id: int | None = None
    hasheous_id: int | None = None
    tgdb_id: int | None = None
    flashpoint_id: int | None = None
    category: str | None = None
    generation: int | None = None
    family_name: str | None = None
    family_slug: str | None = None
    url: str | None = None
    url_logo: str | None = None
    created_at: UTCDatetime
    updated_at: UTCDatetime
    fs_size_bytes: int
    is_unidentified: bool
    is_identified: bool
    missing_from_fs: bool

    @computed_field  # type: ignore
    @property
    def display_name(self) -> str:
        return self.custom_name or self.name
