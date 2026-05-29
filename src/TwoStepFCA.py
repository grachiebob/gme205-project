from ODCostMatrix import ODCostMatrix

class TwoStepFCA:
    """
    Two-Step Floating Catchment Area (2SFCA) accessibility model:
    """

    CATCHMENT_MIN: float = 15.0   # drive-time threshold

    def __init__(
        self,
        od_matrix: ODCostMatrix,
        dormitories,
        facilities,
        threshold=CATCHMENT_MIN
    ):

        self.od = od_matrix
        self.dormitories = dormitories
        self.facilities = facilities
        self.threshold = threshold

        self.results = {}
        self.supply_ratios = {}

    def run(self) -> None:
        """Execute Step 1 then Step 2 and populate all output attributes."""
        self._step1()
        self._step2()

    def _step1(self):
        """
        Step 1 — Supply-to-Demand Ratio
        -----------------------------------------------
        Rⱼ = Sⱼ / Σₖ Pₖ  for all k : dₖⱼ ≤ d₀

        Sⱼ  = bed_capacity  of facility j
        Pₖ  = population    of demand node k (Demand_Pop)
        d₀  = 15-minute catchment threshold
        """

        dorm_pop = {
            d.name: d.population
            for d in self.dormitories
        }

        for hcf in self.facilities:

            reachable_dorms = self.od.dorms_reaching(hcf.name)

            total_demand = sum(
                dorm_pop.get(d, 0)
                for d in reachable_dorms
            )

            hcf.catchment_population = total_demand

            if total_demand > 0:
                hcf.supply_ratio = hcf.bed_capacity / total_demand
            else:
                hcf.supply_ratio = 0

            self.supply_ratios[hcf.name] = hcf.supply_ratio

    def _step2(self) -> None:
        """
        Step 2 — Accessibility Index 
        --------------------------------------------
        Aᵢ = Σⱼ Rⱼ  for all j : dᵢⱼ ≤ d₀

        Aᵢ scaled to beds per 1 000 residents for readability.
        """

        for dorm in self.dormitories:

            reachable = self.od.reachable_from(dorm.name)

            ai = 0.0

            for hcf_name in reachable:
                ai += self.supply_ratios.get(hcf_name, 0.0)

            ai_per_1000 = ai * 1000.0

            dorm.set_accessibility(ai_per_1000)
            dorm.sum_service = round(ai_per_1000, 5)

            self.results[dorm.name] = ai_per_1000