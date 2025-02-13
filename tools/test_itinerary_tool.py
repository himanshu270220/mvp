from itinerary_tool import itinerary_tool

def test_get_dubai_itinerary():
    # Test getting Dubai itinerary
    dubai_itinerary = itinerary_tool.get_itinerary("dubai")
    assert len(dubai_itinerary) == 5, "Dubai itinerary should have 5 days"
    assert dubai_itinerary[0]["day"] == 1, "First day should be day 1"
    print("Dubai itinerary test passed!")

if __name__ == "__main__":
    test_get_dubai_itinerary()
