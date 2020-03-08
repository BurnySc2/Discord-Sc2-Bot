import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pytest, arrow

from commands.public_mmr import Mmr


@pytest.mark.asyncio
async def test_parse_api_result():
    example_response = {
        "division": 71017,
        "server": "kr",
        "rank": 87,
        "race": "t",
        "lvl": "54",
        "portrait_name": "SCret Admirer",
        "last_played": "/Date(1558115348000)/",
        "divName": "Dominion Psi",
        "tier": 1,
        "league": "grandmaster",
        "league_id": 1,
        "mmr": 5779,
        "points": 3845,
        "ach_pts": 3890,
        "wins": 392,
        "losses": 303,
        "clan_tag": "",
        "acc_name": "Polt",
        "ggtracker": None,
        "replaystats": "334545",
        "overwatch": None,
        "acc_id": "97728/1",
        "game_link": "3/5919738718108778496",
        "display_name": "EnVyUsPolt",
        "aligulac": None,
        "note": None,
        "description": "Polt",
        "platform": "twitch.tv",
        "stream_name": "polt",
        "game": "sc2",
        "is_online": True,
        "title": "[한국어|ENG] Try hard.",
        "preview_img": "https://static-cdn.jtvnw.net/previews-ttv/live_user_polt-640x360.jpg",
        "last_online": "/Date(1558115260483)/",
        "viewers": 1539,
        "mode": "SOLO",
    }
    test_object = Mmr()
    result = test_object.format_result(example_response)

    correct_result = ["KR T G87", "5779", "392-303", "0h", "0h", "Polt (EnVyUsPolt)"]

    # The time results can be different as it uses utcnow() which obviously changes in tests, based on when the test is run
    assert result[:3] == correct_result[:3]
    assert result[5:] == correct_result[5:]
