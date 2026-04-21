"""Trip spec dataclass invariants."""
from backend.routing.trip_spec import DaySegment, Itinerary, TripSpec


def test_loop_detection():
    assert TripSpec(days=2, miles_per_day=7, start="A").is_loop
    assert TripSpec(days=2, miles_per_day=7, start="A", end="A").is_loop
    assert not TripSpec(days=2, miles_per_day=7, start="A", end="B").is_loop


def test_target_m_per_day_conversion():
    spec = TripSpec(days=3, miles_per_day=10, start="A")
    # 1 mile = 1609.344 meters
    assert abs(spec.target_m_per_day - 16093.44) < 1.0


def test_day_segment_length_miles():
    day = DaySegment(
        day_index=0,
        path=[1, 2, 3],
        length_m=16_093.44,  # 10 miles
        gain_m=500,
        camp_node=3,
        camp_name="X",
    )
    assert abs(day.length_miles - 10.0) < 0.01


def test_itinerary_total_length_miles():
    days = [
        DaySegment(day_index=i, path=[1], length_m=8046.72, gain_m=100,
                   camp_node=1, camp_name=f"C{i}")
        for i in range(3)
    ]
    it = Itinerary(days=days, total_length_m=3 * 8046.72, total_gain_m=300, score=5.0)
    # 3 × 5 miles = 15 miles total
    assert abs(it.total_length_miles - 15.0) < 0.01
