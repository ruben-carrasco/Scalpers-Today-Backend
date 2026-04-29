from scalper_today.domain.entities import EconomicEvent, Importance


def test_economic_event_properties():
    event = EconomicEvent(
        id="123",
        time="10:00",
        title="NFP",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        actual="100K",
        forecast="150K",
        previous="120K",
        surprise="negative",
        url="http://example.com",
    )

    assert event.id == "123"
    assert event.importance == 3
    assert event.title == "NFP"


def test_event_is_high_impact():
    e_high = EconomicEvent(
        id="1", time="1", title="1", country="1", currency="1", importance=Importance.HIGH
    )
    e_low = EconomicEvent(
        id="2", time="2", title="2", country="2", currency="2", importance=Importance.LOW
    )

    assert e_high.is_high_impact is True
    assert e_low.is_high_impact is False


def test_event_has_data():
    e_data = EconomicEvent(
        id="1",
        time="1",
        title="1",
        country="1",
        currency="1",
        importance=Importance.LOW,
        actual="1.0",
    )
    e_no_data = EconomicEvent(
        id="2", time="2", title="2", country="2", currency="2", importance=Importance.LOW, actual=""
    )
    e_none = EconomicEvent(
        id="3",
        time="3",
        title="3",
        country="3",
        currency="3",
        importance=Importance.LOW,
        actual=None,
    )

    assert e_data.has_data is True
    assert e_no_data.has_data is False
    assert e_none.has_data is False
