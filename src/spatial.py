from html import entities
import math
import geopandas as gpd
import networkx as nx
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

class RoadNetwork:
    """
    * Nodes   — unique vertices extracted from LineString coordinate lists.
                Each node carries (x, y) attributes.
    * Edges   — directed according to the `oneway` field:
                  'B' = two edges (both directions)
                  'F' = one edge  (start → end)
                  'T' = one edge  (end → start)
    * Weight  — `Time_car` (minutes, pre-computed in the GeoJSON).
                This already encodes speed limits and road class, matching
                the paper's 30 km/h impedance model.
    * Filter  — pedestrian-only fclass values are excluded so routing
                stays on drivable roads (Vehicle Travel Mode).
    """

    CRS = "EPSG:32651"

    _PEDESTRIAN_FCLASSES = {
    "footway", "pedestrian", "cycleway", "bridleway",
    "path", "steps", "track",
    }

    def __init__(self):
        self.graph = nx.DiGraph()
        self._node_map = {}
        self._next_id = 0

    def load(self, geojson_path):
        """
        Creates the RoadNetwork graph
        """

        gdf = gpd.read_file(geojson_path)

        gdf = gdf[~gdf["fclass"].isin(self._PEDESTRIAN_FCLASSES)] #filter the road data

        self.road_count = len(gdf)

        self.geometry_types = (
            gdf.geometry.geom_type
            .value_counts()
            .to_dict()
        )

        added_edges = 0

        for _, row in gdf.iterrows():

            geom = row.geometry

            if geom is None or geom.is_empty:
                continue

            try:
                time_car = float(row["Time_car"])
            except Exception:
                continue

            oneway = str(row.get("oneway", "B")).strip().upper()

            lines = [geom] if geom.geom_type == "LineString" else geom.geoms

            for line in lines:

                coords = list(line.coords)

                if len(coords) < 2:
                    continue

            # Build graph using EVERY segment
                segment_count = len(coords) - 1
                segment_time = time_car / max(segment_count, 1)

                for i in range(segment_count):

                    u = self._get_or_add_node(coords[i])
                    v = self._get_or_add_node(coords[i + 1])

                    if u == v:
                        continue

                    if oneway == "F":
                        self.graph.add_edge(u, v, time_car=segment_time)

                    elif oneway == "T":
                        self.graph.add_edge(v, u, time_car=segment_time)

                    else:
                        self.graph.add_edge(u, v, time_car=segment_time)
                        self.graph.add_edge(v, u, time_car=segment_time)

    def _get_or_add_node(self, coord: tuple) -> int:
        """Return existing node ID for coord, or register a new one."""
        key = (round(coord[0], 4), round(coord[1], 4))

        if key not in self._node_map:
            self._node_map[key] = self._next_id
            self.graph.add_node(
                self._next_id,
                x=key[0],
                y=key[1]
            )
            self._next_id += 1
        return self._node_map[key]

    def snap(self, entities) -> None:
        """
        Assign each SpatialObject the nearest road-network node ID. Uses brute-force nearest-neighbour over all graph nodes.
        """
        # Build a list of (node_id, x, y) once for reuse
        
        node_list = [
            (nid, data["x"], data["y"])
                for nid, data in self.graph.nodes(data=True)
        ]

        for entity in entities:

            best_id = None
            best_d = float("inf")

            for nid, x, y in node_list:

                d = math.hypot(
                    entity.x - x,
                    entity.y - y
                )

                if d < best_d:
                    best_d = d
                    best_id = nid

        entity.node_id = best_id

    def shortest_time(self, origin_node, dest_node):

        try:
            return nx.shortest_path_length(
                self.graph,
                origin_node,
                dest_node,
                weight="time_car"
            )

        except:
            return None
