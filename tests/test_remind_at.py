import pytest
from hypothesis import given, settings
import hypothesis.strategies as st
import arrow

from commands.public_remind import Remind


def create_date_time_string(_year, _month, _day, _hour, _minute, _second):
    # Mark _year=0 as year not being used
    if _year:
        date = f"{str(_year).zfill(4)}-{str(_month).zfill(2)}-{str(_day).zfill(2)}"
    else:
        date = f"{str(_month).zfill(2)}-{str(_day).zfill(2)}"

    # Mark _second=0 as second not being used
    if _second:
        time = f"{str(_hour).zfill(2)}:{str(_minute).zfill(2)}:{str(_second).zfill(2)}"
    else:
        time = f"{str(_hour).zfill(2)}:{str(_minute).zfill(2)}"

    # Convert input time to date_time combination
    date_time = ""
    if date:
        if time:
            date_time = f"{date} {time}"
        else:
            date_time = f"{date}"
    elif time:
        date_time = f"{time}"

    return date_time


@pytest.mark.asyncio
@settings(max_examples=1_000)
@given(
    # Year
    st.integers(min_value=0, max_value=9999),
    # Month
    st.integers(min_value=1, max_value=12),
    # Day
    st.integers(min_value=1, max_value=28),
    # Hour
    st.integers(min_value=0, max_value=23),
    # Minute
    st.integers(min_value=0, max_value=59),
    # Second
    st.integers(min_value=0, max_value=59),
    # Message
    st.text(min_size=1),
)
async def test_parsing_date_and_time_from_message_success(_year, _month, _day, _hour, _minute, _second, _message):
    # Dont care about empty strings, or just space or just new line characters
    if not _message.strip():
        return
    r = Remind(client=None)

    date_time = create_date_time_string(_year, _month, _day, _hour, _minute, _second)
    my_message = f"{date_time} {_message}"
    result = await r._parse_date_and_time_from_message(my_message)

    assert isinstance(result[0], arrow.Arrow)
    assert result[1] == _message.strip()


@pytest.mark.asyncio
@settings(max_examples=1_000)
@given(
    # Year
    st.integers(),
    # Month
    st.integers(),
    # Day
    st.integers(),
    # Hour
    st.integers(),
    # Minute
    st.integers(),
    # Second
    st.integers(),
    # Message
    st.text(min_size=1),
)
async def test_parsing_date_and_time_from_message_failure(_year, _month, _day, _hour, _minute, _second, _message):
    if not _message.strip():
        return
    r = Remind(client=None)

    date_time = create_date_time_string(_year, _month, _day, _hour, _minute, _second)
    my_message = f"{date_time} {_message}"

    # Invalid date time combination, e.g. 30th of february
    try:
        arrow_time = arrow.get(date_time)
    except:
        return
    _split = date_time.split(" ")
    _date = _split[0]
    _time = _split[1]

    valid_date = False
    try:
        arrow.get(_date)
        valid_date = True
    except:
        pass

    valid_time = False
    try:
        arrow.get(_time)
        valid_time = True
    except:
        pass

    result = await r._parse_date_and_time_from_message(my_message)

    if not date_time:
        assert result is None

    if valid_date:
        # Invalid year
        if not (0 <= _year < 10_000):
            assert result is None
        # Invalid month
        if not (0 < _month <= 12):
            assert result is None
        # Invalid day
        if not (0 < _day <= 31):
            assert result is None

    if valid_time:
        # Invalid hour
        if not (0 <= _hour < 24):
            assert result is None
        # Invalid minute
        if not (0 <= _minute < 60):
            assert result is None
        # Invalid second
        if not (0 <= _second < 60):
            assert result is None
