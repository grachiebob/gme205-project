import math
from shapely.geometry import Point

class SpatialObject:

    def __init__(self, name: str, geometry: Point) -> None:
        if not isinstance(geometry, Point):
            raise TypeError(
                f"SpatialObject requires a Shapely Point, got {type(geometry).__name__}"
            )
        self.name: str = name
        self.geometry: Point = geometry
        self.node_id = None

    @property
    def x(self) -> float:
        """Easting in metres (EPSG:32651)."""
        return self.geometry.x

    @property
    def y(self) -> float:
        """Northing in metres (EPSG:32651)."""
        return self.geometry.y

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

class Dormitory(SpatialObject):

    def __init__(self, name, geometry, population, dorm_id, sum_service=0):
        super().__init__(name, geometry)

        self.population = population
        self.dorm_id = dorm_id
        self.sum_service = sum_service

        self.accessibility_index = 0
        self.closest_facility = None
        self.closest_time_min = None
        self.travel_times = {}

    def set_accessibility(self, index: float) -> None:
        """Set the computed 2SFCA Aᵢ (beds / 1 000 residents). Stores data in a Dormitory object."""
        self.accessibility_index = round(index, 5)

    def set_closest(self, facility: "HealthcareFacility", minutes: float) -> None:
        """Record the closest reachable healthcare facility."""
        self.closest_facility = facility
        self.closest_time_min = round(minutes, 4)


class HealthcareFacility(SpatialObject):

    def __init__(self, name, geometry, bed_capacity, fac_id,
                 node_type="Hospital", address=""):
        super().__init__(name, geometry)

        self.bed_capacity = bed_capacity
        self.fac_id = fac_id
        self.node_type = node_type
        self.address = address

        self.supply_ratio = 0
        self.catchment_population = 0