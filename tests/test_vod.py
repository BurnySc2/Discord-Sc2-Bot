import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pytest

from commands.public_vod import Vod


@pytest.mark.asyncio
async def test_parse_api_result():
    example_response = {
        "_id": 34149581248,
        "game": "StarCraft II",
        "viewers": 48,
        "video_height": 1080,
        "average_fps": 60,
        "delay": 0,
        "created_at": "2019-05-17T09:42:30Z",
        "is_playlist": False,
        "stream_type": "live",
        "preview": {
            "small": "https://static-cdn.jtvnw.net/previews-ttv/live_user_musti20045-80x45.jpg",
            "medium": "https://static-cdn.jtvnw.net/previews-ttv/live_user_musti20045-320x180.jpg",
            "large": "https://static-cdn.jtvnw.net/previews-ttv/live_user_musti20045-640x360.jpg",
            "template": "https://static-cdn.jtvnw.net/previews-ttv/live_user_musti20045-{width}x{height}.jpg",
        },
        "channel": {
            "mature": False,
            "partner": False,
            "status": "[GER/TUR] täglich begleitet euch das Mustitier in den Tag oder Schlaf.",
            "broadcaster_language": "de",
            "broadcaster_software": "",
            "display_name": "musti20045",
            "game": "StarCraft II",
            "language": "de",
            "_id": 26043804,
            "name": "musti20045",
            "created_at": "2011-11-10T20:05:22Z",
            "updated_at": "2019-05-17T11:25:15Z",
            "delay": None,
            "logo": "https://static-cdn.jtvnw.net/jtv_user_pictures/musti20045-profile_image-18e1aac25b767dd1-300x300.jpeg",
            "banner": None,
            "video_banner": "https://static-cdn.jtvnw.net/jtv_user_pictures/musti20045-channel_offline_image-6c45b6acc1f2d3c1-1920x1080.jpeg",
            "background": None,
            "profile_banner": "https://static-cdn.jtvnw.net/jtv_user_pictures/musti20045-profile_banner-6539271ad9a596f7-480.jpeg",
            "profile_banner_background_color": "",
            "url": "https://www.twitch.tv/musti20045",
            "views": 335094,
            "followers": 5834,
            "_links": {
                "self": "https://api.twitch.tv/kraken/channels/musti20045",
                "follows": "https://api.twitch.tv/kraken/channels/musti20045/follows",
                "commercial": "https://api.twitch.tv/kraken/channels/musti20045/commercial",
                "stream_key": "https://api.twitch.tv/kraken/channels/musti20045/stream_key",
                "chat": "https://api.twitch.tv/kraken/chat/musti20045",
                "features": "https://api.twitch.tv/kraken/channels/musti20045/features",
                "subscriptions": "https://api.twitch.tv/kraken/channels/musti20045/subscriptions",
                "editors": "https://api.twitch.tv/kraken/channels/musti20045/editors",
                "teams": "https://api.twitch.tv/kraken/channels/musti20045/teams",
                "videos": "https://api.twitch.tv/kraken/channels/musti20045/videos",
            },
        },
        "_links": {"self": "https://api.twitch.tv/kraken/streams/musti20045"},
    }
    test_object = Vod()
    parsed_data = await test_object.vod_parse_api_response(example_response)

    correct_parsed_data = (
        "musti20045",
        "https://www.twitch.tv/musti20045",
        48,
        "2 hours 2 minutes 36 seconds",
        "https://www.twitch.tv/videos/425956092?t=7356s",
    )

    # Last value doesnt have to be correct
    assert parsed_data[:3] == correct_parsed_data[:3]
