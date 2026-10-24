import pytest

from handler.notification_channels import messages
from handler.notification_channels.messages import render
from models.notification import NotificationKind

from .fixtures import make_notification


@pytest.fixture(autouse=True)
def base_url(mocker):
    return mocker.patch.object(
        messages, "get_public_base_url", return_value="https://romm.example.com"
    )


def test_a_custom_kind_carries_its_own_text():
    message = render(make_notification(kind="argosy.sync_done"))

    assert message.title == "Maintenance tonight"
    assert message.body == "RomM restarts at 23:00"
    assert message.url == "https://romm.example.com/platforms"


def test_links_nowhere_without_a_shareable_base_url(base_url):
    base_url.return_value = None

    assert render(make_notification()).url is None


def test_ignores_data_of_the_wrong_type():
    message = render(
        make_notification(kind=NotificationKind.SCAN_COMPLETED, data={"new_roms": True})
    )

    assert message.body == "No new games"
