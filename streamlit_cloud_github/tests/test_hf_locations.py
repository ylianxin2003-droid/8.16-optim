import os
import sys
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class HfLocationsTest(unittest.TestCase):
    def test_catalogue_has_unique_names_and_valid_coordinates(self):
        from hf_locations import HF_LOCATIONS

        self.assertGreaterEqual(len(HF_LOCATIONS), 10)
        self.assertEqual(len(HF_LOCATIONS), len(set(HF_LOCATIONS)))
        for name, location in HF_LOCATIONS.items():
            self.assertEqual(location["name"], name)
            self.assertGreaterEqual(location["lat"], -90.0)
            self.assertLessEqual(location["lat"], 90.0)
            self.assertGreaterEqual(location["lon"], -180.0)
            self.assertLessEqual(location["lon"], 180.0)
            self.assertIn(location["type"], {"city", "corridor"})

    def test_every_preset_scenario_resolves_to_catalogue_locations(self):
        from hf_locations import HF_LOCATIONS, HF_ROUTE_SCENARIOS, resolve_route_scenario

        for scenario_name, endpoints in HF_ROUTE_SCENARIOS.items():
            self.assertIn(endpoints[0], HF_LOCATIONS)
            self.assertIn(endpoints[1], HF_LOCATIONS)
            origin, target = resolve_route_scenario(scenario_name)
            self.assertEqual(origin["name"], endpoints[0])
            self.assertEqual(target["name"], endpoints[1])

    def test_birmingham_to_new_york_is_default_scenario(self):
        from hf_locations import DEFAULT_HF_ROUTE_SCENARIO, resolve_route_scenario

        self.assertEqual(DEFAULT_HF_ROUTE_SCENARIO, "Birmingham → New York")
        origin, target = resolve_route_scenario(DEFAULT_HF_ROUTE_SCENARIO)
        self.assertEqual(origin["name"], "Birmingham, United Kingdom")
        self.assertEqual(target["name"], "New York, United States")
        self.assertAlmostEqual(origin["lat"], 52.4862)
        self.assertAlmostEqual(target["lon"], -74.0060)

    def test_location_names_returns_searchable_display_names(self):
        from hf_locations import location_names

        names = location_names()

        self.assertIn("Birmingham, United Kingdom", names)
        self.assertIn("New York, United States", names)
        self.assertEqual(names, sorted(names))


if __name__ == "__main__":
    unittest.main()
