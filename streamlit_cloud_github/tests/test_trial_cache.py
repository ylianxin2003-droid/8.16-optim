import json
import os
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TrialCacheTest(unittest.TestCase):
    def test_legacy_cache_without_forecast_contract_is_rejected(self):
        import trial_cache

        cache_key = "legacy-future-file-time-contract"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / cache_key
            root.mkdir()
            (root / "status.json").write_text(
                json.dumps({
                    "status": {
                        "source": "api",
                        "ok": True,
                        "metadata": {
                            "forecast_downloads": 3,
                            "forecast_request_audit": [{
                                "analysis_time": "2025-01-01T17:55:00+00:00",
                                "valid_time": "2025-01-01T19:25:00+00:00",
                                "downloaded_from_serene": True,
                            }],
                        },
                    },
                    "files": {},
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "incompatible.*forecast contract.*regenerate",
            ):
                trial_cache.load_trial_bundle(cache_key, base_dir=Path(tmpdir))

    def test_saved_cache_records_validated_schema_and_forecast_contract(self):
        import trial_cache
        from data_loader import IcaoProductBundle, LoadStatus

        cache_key = "versioned-contract"
        bundle = IcaoProductBundle(
            products=pd.DataFrame([{
                "time": "2025-01-01T19:25:00Z",
                "actual_output_time": "2025-01-01T17:56:00Z",
                "variable": "TEC",
                "value": 12.0,
            }]),
            status=LoadStatus(source="api", ok=True, message="loaded"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = trial_cache.save_trial_bundle(
                cache_key,
                bundle,
                pd.DataFrame(),
                bundle.products,
                base_dir=Path(tmpdir),
            )
            stored = json.loads((root / "status.json").read_text(encoding="utf-8"))
            loaded, _summary, _data = trial_cache.load_trial_bundle(
                cache_key,
                base_dir=Path(tmpdir),
            )

        self.assertEqual(stored.get("cache_schema_version"), 3)
        self.assertEqual(
            stored.get("forecast_contract_version"),
            "analysis-plus-kp-horizon-evidence-v2",
        )
        self.assertEqual(loaded.status.metadata.get("cache_schema_version"), 3)
        self.assertEqual(
            loaded.status.metadata.get("forecast_contract_version"),
            "analysis-plus-kp-horizon-evidence-v2",
        )
        self.assertTrue(loaded.status.metadata.get("cache_contract_validated"))

    def test_cache_key_is_stable_and_files_round_trip(self):
        import trial_cache
        from data_loader import IcaoProductBundle, LoadStatus

        region = {"lat_min": -90.0, "lat_max": 90.0, "lon_min": -180.0, "lon_max": 180.0}
        key = trial_cache.make_trial_cache_key(
            "2025-01-01T17:55:00",
            region,
            15.0,
            "Full ICAO-style mode",
        )

        self.assertIn("20250101T175500", key)
        self.assertEqual(
            key,
            trial_cache.make_trial_cache_key(
                "2025-01-01T17:55:00Z",
                dict(reversed(region.items())),
                15,
                "Full ICAO-style mode",
            ),
        )

        products = pd.DataFrame([{
            "time": pd.Timestamp("2025-01-01T17:55:00Z"),
            "lat": -90.0,
            "lon": -180.0,
            "variable": "TEC",
            "value": 12.0,
        }])
        indices = pd.DataFrame([{
            "time": pd.Timestamp("2025-01-01T17:55:00Z"),
            "variable": "Kp",
            "value": 8.0,
        }])
        summary = pd.DataFrame([{
            "Domain": "GNSS",
            "Indicator": "Vertical TEC",
            "Status": "OK",
        }])
        data = pd.DataFrame([{
            "time": pd.Timestamp("2025-01-01T17:55:00Z"),
            "variable": "TEC",
            "value": 12.0,
        }])
        bundle = IcaoProductBundle(
            products=products,
            indices=indices,
            kp_horizons=pd.DataFrame([{
                "horizon_minutes": 30,
                "target_time": pd.Timestamp("2025-01-01T18:25:00Z"),
                "interval_start": pd.Timestamp("2025-01-01T18:00:00Z"),
                "value": 8.2,
                "evidence_role": "official_forecast",
            }]),
            status=LoadStatus(
                source="api",
                ok=True,
                message="Loaded from API",
                warnings=["sample warning"],
                metadata={
                    "analysis_time": "2025-01-01T17:55:00+00:00",
                    "loaded_region": region,
                    "token_like_value": "not-a-secret",
                },
            ),
            kp_storm_eligible=True,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = trial_cache.save_trial_bundle(
                key,
                bundle,
                summary,
                data,
                base_dir=Path(tmpdir),
            )
            loaded_bundle, loaded_summary, loaded_data = trial_cache.load_trial_bundle(
                key,
                base_dir=Path(tmpdir),
            )

            self.assertTrue((cache_path / "status.json").exists())
            self.assertEqual(loaded_bundle.status.source, "trial_cache")
            self.assertTrue(loaded_bundle.status.ok)
            self.assertEqual(loaded_bundle.kp_storm_eligible, True)
            self.assertEqual(set(loaded_bundle.products["variable"]), {"TEC"})
            self.assertEqual(
                loaded_bundle.kp_horizons["evidence_role"].tolist(),
                ["official_forecast"],
            )
            self.assertEqual(
                loaded_bundle.kp_horizons["horizon_minutes"].tolist(), [30]
            )
            self.assertEqual(loaded_summary.iloc[0]["Indicator"], "Vertical TEC")
            self.assertEqual(loaded_data.iloc[0]["variable"], "TEC")

            for file_path in cache_path.rglob("*"):
                if file_path.is_file():
                    content = file_path.read_bytes()
                    self.assertNotIn(b"SERENE_API_TOKEN", content)
                    self.assertNotIn(b"your-new-api-token", content)

    def test_missing_cache_raises_file_not_found(self):
        import trial_cache

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                trial_cache.load_trial_bundle("missing-key", base_dir=Path(tmpdir))

    def test_cache_zip_contains_commit_ready_folder_without_secrets(self):
        import trial_cache
        from data_loader import IcaoProductBundle, LoadStatus

        cache_key = "20250101T175500-Quick-Demo-test"
        bundle = IcaoProductBundle(
            products=pd.DataFrame([{
                "time": pd.Timestamp("2025-01-01T17:55:00Z"),
                "variable": "TEC",
                "value": 12.0,
            }]),
            indices=pd.DataFrame([{
                "time": pd.Timestamp("2025-01-01T17:55:00Z"),
                "variable": "Kp",
                "value": 8.0,
            }]),
            status=LoadStatus(
                source="api",
                ok=True,
                message="Loaded from API",
                metadata={
                    "analysis_time": "2025-01-01T17:55:00+00:00",
                    "SERENE_API_TOKEN": "must-not-be-written",
                },
            ),
        )

        archive_bytes = trial_cache.build_trial_bundle_zip(
            cache_key,
            bundle,
            pd.DataFrame([{"Indicator": "Vertical TEC", "Status": "OK"}]),
            bundle.products,
        )

        with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
            names = set(archive.namelist())
            self.assertIn(f"{cache_key}/status.json", names)
            self.assertTrue(any(name.startswith(f"{cache_key}/products.") for name in names))
            for name in names:
                content = archive.read(name)
                self.assertNotIn(b"SERENE_API_TOKEN", content)
                self.assertNotIn(b"must-not-be-written", content)

    def test_generation_utility_uses_global_trial_windows(self):
        import generate_trial_outputs

        times = generate_trial_outputs._analysis_times()

        self.assertIn("2024-10-11T02:55:00", times)
        self.assertIn("2026-01-19T23:55:00", times)
        self.assertEqual(generate_trial_outputs.GLOBAL_REGION, {
            "lat_min": -90.0,
            "lat_max": 90.0,
            "lon_min": -180.0,
            "lon_max": 180.0,
        })

    def test_generation_utility_preserves_kp_horizon_evidence(self):
        import generate_trial_outputs
        import trial_cache
        from data_loader import IcaoProductBundle, LoadStatus

        analysis_time = "2025-01-01T17:55:00"
        bundle = IcaoProductBundle(
            products=pd.DataFrame([{
                "time": analysis_time,
                "lat": 52.0,
                "lon": -2.0,
                "variable": "TEC",
                "value": 100.0,
                "product_kind": "analysis",
                "source": "SERENE AIDA analysis",
            }]),
            indices=pd.DataFrame([{
                "time": "2025-01-01T15:00:00Z",
                "variable": "Kp",
                "value": 7.0,
                "source": "GFZ Kp/ap JSON service",
            }]),
            kp_horizons=pd.DataFrame([
                {
                    "horizon_minutes": 30,
                    "target_time": "2025-01-01T18:25:00Z",
                    "interval_start": "2025-01-01T18:00:00Z",
                    "value": 8.2,
                    "evidence_role": "observed_backtesting",
                    "source": "GFZ observed outcome — backtesting only",
                    "data_status": "definitive",
                },
                {
                    "horizon_minutes": 90,
                    "target_time": "2025-01-01T19:25:00Z",
                    "interval_start": "2025-01-01T18:00:00Z",
                    "value": 7.8,
                    "evidence_role": "observed_backtesting",
                    "source": "GFZ observed outcome — backtesting only",
                    "data_status": "definitive",
                },
            ]),
            status=LoadStatus(
                source="api",
                ok=True,
                message="Loaded controlled test data",
                metadata={"analysis_time": analysis_time},
            ),
            kp_storm_eligible=True,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            def save_into_temp(cache_key, saved_bundle, summary, data):
                return trial_cache.save_trial_bundle(
                    cache_key,
                    saved_bundle,
                    summary,
                    data,
                    base_dir=Path(tmpdir),
                )

            with patch.object(
                generate_trial_outputs,
                "_analysis_times",
                return_value=[analysis_time],
            ):
                with patch.object(
                    generate_trial_outputs,
                    "load_icao_products",
                    return_value=bundle,
                ):
                    with patch.object(
                        generate_trial_outputs,
                        "save_trial_bundle",
                        side_effect=save_into_temp,
                    ):
                        saved = generate_trial_outputs.generate_trial_outputs()

            cache_folders = [path for path in Path(tmpdir).iterdir() if path.is_dir()]
            self.assertEqual(saved, 1)
            self.assertEqual(len(cache_folders), 1)
            loaded_bundle, loaded_summary, _loaded_data = trial_cache.load_trial_bundle(
                cache_folders[0].name,
                base_dir=Path(tmpdir),
            )

        kp_row = loaded_summary[
            loaded_summary["Indicator"] == "Auroral Absorption"
        ].iloc[0]
        self.assertEqual(float(kp_row["+30 min forecast"]), 8.2)
        self.assertIn("backtesting", str(kp_row["+30 min source"]).casefold())
        self.assertEqual(
            loaded_bundle.kp_horizons["horizon_minutes"].tolist(),
            [30, 90],
        )


if __name__ == "__main__":
    unittest.main()
