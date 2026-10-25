from .audit_events_handler import DBAuditEventsHandler
from .client_tokens_handler import DBClientTokensHandler
from .collections_handler import DBCollectionsHandler
from .devices_handler import DBDevicesHandler
from .music_playlists_handler import DBMusicPlaylistsHandler
from .notification_channels_handler import DBNotificationChannelsHandler
from .notifications_handler import DBNotificationsHandler
from .permissions_handler import DBPermissionsHandler
from .platforms_handler import DBPlatformsHandler
from .recommendations_handler import DBRecommendationsHandler
from .roms_handler import DBRomsHandler
from .stats_handler import DBStatsHandler
from .users_handler import DBUsersHandler

db_audit_event_handler = DBAuditEventsHandler()
db_client_token_handler = DBClientTokensHandler()
db_collection_handler = DBCollectionsHandler()
db_device_handler = DBDevicesHandler()
db_music_playlist_handler = DBMusicPlaylistsHandler()
db_notification_channel_handler = DBNotificationChannelsHandler()
db_notification_handler = DBNotificationsHandler()
db_permission_handler = DBPermissionsHandler()
db_platform_handler = DBPlatformsHandler()
db_recommendation_handler = DBRecommendationsHandler()
db_rom_handler = DBRomsHandler()
db_stats_handler = DBStatsHandler()
db_user_handler = DBUsersHandler()
