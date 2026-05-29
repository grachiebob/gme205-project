class ODCostMatrix:
    """
    Origin-Destination travel-time matrix = shortest-path travel times from every Dormitory
    (origin) to every HealthcareFacility (destination) using the road network's `time_car` edge weight within the
    15-minute catchment threshold.
    """

    def __init__(self, network, dormitories, facilities, threshold=15.0):
        self.network = network
        self.dormitories = dormitories
        self.facilities = facilities
        self.threshold = threshold
        self.matrix = {d.name: {} for d in dormitories}

    def compute(self) -> None:
        """
        Populate self.matrix and update each Dormitory's travel_times
        and closest_facility attributes.
        """
        for dorm in self.dormitories:

            if dorm.node_id is None:
                print(f"[WARN] {dorm.name} not snapped — skipping.")
                continue

            best_time = None
            best_hcf = None

            for hcf in self.facilities:

                if hcf.node_id is None:
                    continue

                t = self.network.shortest_time(
                    dorm.node_id,
                    hcf.node_id
                )

                if t is None or t > self.threshold:
                    continue

                t = round(t, 4)

                self.matrix[dorm.name][hcf.name] = t
                dorm.travel_times[hcf.name] = t

                if best_time is None or t < best_time:
                    best_time = t
                    best_hcf = hcf

            if best_hcf:
                dorm.set_closest(best_hcf, best_time)

        self.served_dormitories = sum(
            bool(row) for row in self.matrix.values()
        )

    def get(self, dorm_name: str, hcf_name: str) -> float | None:
        """Travel time (min) for a specific pair, or None if outside catchment."""
        return self.matrix.get(dorm_name, {}).get(hcf_name)

    def reachable_from(self, dorm_name: str) -> dict[str, float]:
        """All {HCF_name: minutes} reachable from a given dormitory."""
        return self.matrix.get(dorm_name, {})

    def dorms_reaching(self, hcf_name: str) -> dict[str, float]:
        """All {dorm_name: minutes} that can reach a given HCF."""
        return {
            d: times[hcf_name]
            for d, times in self.matrix.items()
            if hcf_name in times
        }