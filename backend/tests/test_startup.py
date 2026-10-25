"""Tests for startup-time auto-enqueue of the recompute task."""

from unittest.mock import AsyncMock

import pytest
import startup
from rq.job import JOB_ID_PATTERN

from handler.metadata.launchbox_handler.types import LAUNCHBOX_METADATA_STORE
from handler.redis_handler import default_queue, high_prio_queue, low_prio_queue
from tasks.registry import get_task
from tasks.scheduled.update_switch_titledb import SWITCH_TITLEDB_STORE
from utils.cache import VersionedCacheStore


@pytest.fixture
def enqueue_task(mocker):
    return mocker.patch.object(startup, "enqueue_task")


def test_enqueue_convert_webp_fires_when_not_queued(enqueue_task):
    """No in-flight bootstrap job -> enqueue the backfill exactly once."""
    startup._enqueue_convert_images_to_webp()

    enqueue_task.assert_called_once_with(
        "convert_images_to_webp",
        job_id=startup.CONVERT_IMAGES_TO_WEBP_JOB_ID,
        unique=True,
    )


@pytest.mark.parametrize("job_id", (startup.CONVERT_IMAGES_TO_WEBP_JOB_ID,))
def test_backfill_job_ids_are_valid_rq_ids(job_id):
    """RQ rejects any job_id not matching [A-Za-z0-9_-]+ (ValueError in set_id),
    which the broad except here would swallow -> backfill silently never
    enqueues. A colon was the original culprit."""
    assert JOB_ID_PATTERN.fullmatch(job_id)


def test_backfill_names_a_registered_task():
    """The name in the payload is all the runner gets, so it has to resolve."""
    assert get_task("convert_images_to_webp") is not None


class TestDropLegacySchedulerState:
    """The old scheduler's keys go on the first start after the migration."""

    @pytest.fixture
    def redis(self, mocker):
        redis = mocker.patch.object(startup, "redis_client")
        redis.scan_iter.return_value = []
        return redis

    def test_removes_the_scheduler_keys_with_no_jobs_left_behind(self, redis):
        redis.zrange.return_value = []

        startup._drop_legacy_scheduler_state()

        redis.delete.assert_called_once_with(*startup.LEGACY_SCHEDULER_KEYS)

    def test_deletes_orphaned_jobs_but_not_queued_ones(self, mocker, redis):
        redis.zrange.return_value = [b"orphan", b"queued"]
        for queue in (high_prio_queue, default_queue):
            mocker.patch.object(queue, "get_job_ids", return_value=[])
        mocker.patch.object(low_prio_queue, "get_job_ids", return_value=["queued"])

        startup._drop_legacy_scheduler_state()

        assert redis.delete.call_args_list[0].args == ("rq:job:orphan",)
        assert redis.delete.call_args_list[-1].args == startup.LEGACY_SCHEDULER_KEYS

    def test_survives_a_redis_failure(self, redis):
        redis.zrange.side_effect = RuntimeError("redis gone")

        startup._drop_legacy_scheduler_state()


class TestRebuildOutdatedMetadataStores:
    """A store an older release wrote is dropped, and its rebuild queued."""

    @pytest.fixture
    def drop_stale(self, mocker):
        """Report only the stores named as stale, whatever order they run in."""

        def patch_drop(*stale: VersionedCacheStore):
            async def drop(_cache, store):
                return store in stale

            return mocker.patch.object(
                startup, "drop_stale_cache_store", new=AsyncMock(side_effect=drop)
            )

        return patch_drop

    async def test_stale_launchbox_store_is_dropped_and_rebuilt(
        self, mocker, drop_stale, enqueue_task
    ):
        mocker.patch.object(startup, "LAUNCHBOX_API_ENABLED", True)
        drop_stale(LAUNCHBOX_METADATA_STORE)

        await startup._rebuild_outdated_metadata_stores()

        enqueue_task.assert_called_once_with(
            "update_launchbox_metadata",
            job_id=startup.UPDATE_LAUNCHBOX_METADATA_JOB_ID,
            unique=True,
        )

    async def test_launchbox_rebuild_waits_on_the_provider_being_enabled(
        self, mocker, drop_stale, enqueue_task
    ):
        """Dropping reclaims the memory; refilling it would serve nobody."""
        mocker.patch.object(startup, "LAUNCHBOX_API_ENABLED", False)
        mocker.patch.object(
            startup,
            "VERSIONED_METADATA_STORES",
            (
                (
                    LAUNCHBOX_METADATA_STORE,
                    "update_launchbox_metadata",
                    startup.UPDATE_LAUNCHBOX_METADATA_JOB_ID,
                    False,
                ),
            ),
        )
        drop_stale(LAUNCHBOX_METADATA_STORE)

        await startup._rebuild_outdated_metadata_stores()

        enqueue_task.assert_not_called()

    async def test_stale_switch_store_is_dropped_and_rebuilt(
        self, drop_stale, enqueue_task
    ):
        drop_stale(SWITCH_TITLEDB_STORE)

        await startup._rebuild_outdated_metadata_stores()

        enqueue_task.assert_called_once_with(
            "update_switch_titledb",
            job_id=startup.UPDATE_SWITCH_TITLEDB_JOB_ID,
            unique=True,
        )

    async def test_current_stores_queue_nothing(self, drop_stale, enqueue_task):
        drop_stale()

        await startup._rebuild_outdated_metadata_stores()

        enqueue_task.assert_not_called()
