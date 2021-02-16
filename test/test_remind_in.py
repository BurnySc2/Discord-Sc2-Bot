import random

import pytest
from hypothesis import given, settings, example
import hypothesis.strategies as st
import arrow


from commands.public_remind import Remind


def create_time_shift_string(_day, _hour, _minute, _second):
    days = "d day days".split(" ")
    hours = "h hour hours".split(" ")
    minutes = "m min mins minute minutes".split(" ")
    seconds = "s sec secs second seconds".split(" ")
    space = ["", " "]

    shift_list = []
    for time, time_strings in zip([_day, _hour, _minute, _second], [days, hours, minutes, seconds]):
        if time >= 0:
            # Random use of "6 days" or "6days"
            space_characer = random.choice(space)
            time_string = random.choice(time_strings)
            shift_list.append(f"{time}{space_characer}{time_string}")
            # Sometimes insert a space character after "6days"
            if random.choice(space):
                shift_list.append(" ")

    shift = "".join(shift_list)
    return shift.strip()


@pytest.mark.asyncio
@settings(max_examples=100)
@example(_day=1_000_000, _hour=0, _minute=0, _second=0)
@example(_day=0, _hour=1_000_000, _minute=0, _second=0)
@example(_day=0, _hour=0, _minute=1_000_000, _second=0)
@example(_day=0, _hour=0, _minute=0, _second=1_000_000)
@given(
    # Day
    st.integers(min_value=0, max_value=1_000_000),
    # Hour
    st.integers(min_value=0, max_value=1_000_000),
    # Minute
    st.integers(min_value=0, max_value=1_000_000),
    # Second
    st.integers(min_value=0, max_value=1_000_000),
)
async def test_parsing_date_and_time_from_message_success(_day, _hour, _minute, _second):
    # Dont care about [0, 0, 0, 0]
    if not (_day or _hour or _minute or _second):
        return

    r = Remind(client=None)

    time_shift = create_time_shift_string(_day, _hour, _minute, _second)
    result = await r._parse_time_shift_from_message(time_shift)

    assert isinstance(result[0], arrow.Arrow)


@pytest.mark.asyncio
@settings(max_examples=100)
@example(_day=10_000_000, _hour=0, _minute=0, _second=0)
@example(_day=0, _hour=10_000_000, _minute=0, _second=0)
@example(_day=0, _hour=0, _minute=10_000_000, _second=0)
@example(_day=0, _hour=0, _minute=0, _second=10_000_000)
@given(
    # Day
    st.integers(min_value=0),
    # Hour
    st.integers(min_value=0),
    # Minute
    st.integers(min_value=0),
    # Second
    st.integers(min_value=0),
)
async def test_parsing_date_and_time_from_message_failure(_day, _hour, _minute, _second):
    r = Remind(client=None)

    time_shift = create_time_shift_string(_day, _hour, _minute, _second)

    # print(time_shift)
    result = await r._parse_time_shift_from_message(time_shift)

    # Invalid day
    if not (0 <= _day <= 1_000_000):
        assert result is None
    # Invalid hour
    if not (0 <= _hour <= 1_000_000):
        assert result is None
    # Invalid minute
    if not (0 <= _minute <= 1_000_000):
        assert result is None
    # Invalid second
    if not (0 <= _second <= 1_000_000):
        assert result is None
