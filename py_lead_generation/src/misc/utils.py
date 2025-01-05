from geopy.geocoders import Nominatim


geolocator = Nominatim(user_agent='google-leads')


def get_coords_by_location(location: str) -> tuple[str]:
    loc = geolocator.geocode(location)
    coords = (loc.latitude, loc.longitude)
    coords = list(map(str, coords))
    return coords
