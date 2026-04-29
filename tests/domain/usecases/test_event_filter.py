import pytest

from scalper_today.domain.dtos import EventFilterCriteria
from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.domain.usecases import EventFilter


@pytest.fixture
def sample_events():
    return [
        EconomicEvent(
            id="1",
            time="10:00",
            title="Low USD",
            country="US",
            currency="USD",
            importance=Importance.LOW,
            actual="1.0",
        ),
        EconomicEvent(
            id="2",
            time="11:00",
            title="High EUR",
            country="EU",
            currency="EUR",
            importance=Importance.HIGH,
            actual="2.0",
        ),
        EconomicEvent(
            id="3",
            time="12:00",
            title="Med USD None",
            country="US",
            currency="USD",
            importance=Importance.MEDIUM,
            actual=None,
        ),
        EconomicEvent(
            id="4",
            time="13:00",
            title="High GBP",
            country="UK",
            currency="GBP",
            importance=Importance.HIGH,
            actual="",
        ),
    ]


def test_filter_by_importance(sample_events):
    criteria = EventFilterCriteria(importance=3)
    filtered = EventFilter.apply_criteria(sample_events, criteria)

    assert len(filtered) == 2
    assert all(e.importance == Importance.HIGH for e in filtered)


def test_filter_by_country(sample_events):
    criteria = EventFilterCriteria(country="US")
    filtered = EventFilter.apply_criteria(sample_events, criteria)

    assert len(filtered) == 2
    assert all(e.country == "US" for e in filtered)


def test_filter_by_has_data(sample_events):
    # Only events with an 'actual' value that isn't empty/None
    criteria = EventFilterCriteria(has_data=True)
    filtered = EventFilter.apply_criteria(sample_events, criteria)

    assert len(filtered) == 2
    assert "1" in [e.id for e in filtered]
    assert "2" in [e.id for e in filtered]


def test_filter_by_search_term(sample_events):
    criteria = EventFilterCriteria(search="GBP")
    filtered = EventFilter.apply_criteria(sample_events, criteria)

    assert len(filtered) == 1
    assert filtered[0].title == "High GBP"


def test_combined_filters(sample_events):
    criteria = EventFilterCriteria(importance=3, has_data=True)
    filtered = EventFilter.apply_criteria(sample_events, criteria)

    assert len(filtered) == 1
    assert filtered[0].id == "2"  # Only High EUR has data and is HIGH impact
