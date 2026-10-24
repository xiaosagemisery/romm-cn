from .client_tokens_handler import DBClientTokensHandler
from .collections_handler import DBCollectionsHandler
from .devices_handler import DBDevicesHandler
from .music_playlists_handler import DBMusicPlaylistsHandler
from .permissions_handler import DBPermissionsHandler
from .platforms_handler import DBPlatformsHandler
from .recommendations_handler import DBRecommendationsHandler
from .roms_handler import DBRomsHandler
from .stats_handler import DBStatsHandler
from .users_handler import DBUsersHandler

db_client_token_handler = DBClientTokensHandler()
db_collection_handler = DBCollectionsHandler()
db_device_handler = DBDevicesHandler()
db_music_playlist_handler = DBMusicPlaylistsHandler()
db_permission_handler = DBPermissionsHandler()
db_platform_handler = DBPlatformsHandler()
db_recommendation_handler = DBRecommendationsHandler()
db_rom_handler = DBRomsHandler()
db_stats_handler = DBStatsHandler()
db_user_handler = DBUsersHandler()
