"""
Add building coordinates from GeoJSON to filtered buildings data.

Input: archive/buildings_filtered_SP26.json
Coordinates: data/ucf_buildings.geojson
Output: archive/buildings_enriched_SP26.json
"""

from pathlib import Path
import json
from typing import Dict, Any, List, Tuple


class BuildingCoordinateProcessor:
    def __init__(self, term_code: str = "SP26"):
        self.term_code = term_code
        self.archive_dir = Path(__file__).parent / "archive"
        self.data_dir = Path(__file__).parent / "data"
        self.geojson_file = self.data_dir / "ucf_buildings.geojson"
        self.buildings_input_file = self.archive_dir / f"buildings_filtered_{term_code}.json"
        self.buildings_output_file = self.archive_dir / f"buildings_enriched_{term_code}.json"

    def load_data(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Load GeoJSON data and filtered buildings data."""
        with open(self.geojson_file, "r") as f:
            geojson_data = json.load(f)

        with open(self.buildings_input_file, "r") as f:
            building_data = json.load(f)

        return geojson_data, building_data

    def save_data(self, data: Dict[str, Any]) -> None:
        """Save the enriched building data."""
        self.archive_dir.mkdir(exist_ok=True)
        with open(self.buildings_output_file, "w") as f:
            json.dump(data, f, indent=2)

    def create_coordinates_map(
        self, geojson_data: Dict[str, Any]
    ) -> Dict[str, List[float]]:
        """Create a mapping from building codes to coordinates."""
        coordinates_map = {}
        for feature in geojson_data.get("features", []):
            building_name = feature.get("properties", {}).get("name", "")
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if building_name and len(coordinates) >= 2:
                coordinates_map[building_name] = coordinates
        return coordinates_map

    def add_coordinates_to_buildings(
        self, building_data: Dict[str, Any], coordinates_map: Dict[str, List[float]]
    ) -> Tuple[Dict[str, Any], int]:
        """Add coordinates to building data."""
        buildings_updated = 0

        for building_code in building_data.get("buildings", {}):
            if building_code in coordinates_map:
                # GeoJSON coordinates are [longitude, latitude]
                building_data["buildings"][building_code]["coordinates"] = {
                    "longitude": coordinates_map[building_code][0],
                    "latitude": coordinates_map[building_code][1],
                }
                buildings_updated += 1
                print(f"  ✓ Added coordinates for: {building_code}")

        return building_data, buildings_updated

    def process(self) -> None:
        """Main processing function."""
        print(f"Loading GeoJSON data from {self.geojson_file}...")
        print(f"Loading buildings data from {self.buildings_input_file}...")
        geojson_data, building_data = self.load_data()

        print("\nCreating coordinates map...")
        coordinates_map = self.create_coordinates_map(geojson_data)
        print(f"Found coordinates for {len(coordinates_map)} buildings in GeoJSON")

        print("\nAdding coordinates to buildings...")
        updated_data, buildings_updated = self.add_coordinates_to_buildings(
            building_data, coordinates_map
        )

        print(f"\nSaving enriched data to {self.buildings_output_file}...")
        self.save_data(updated_data)

        print("\n" + "=" * 50)
        print("Processing complete!")
        print("=" * 50)
        print(f"Added coordinates to {buildings_updated} buildings")

        missing_coordinates = [
            name for name in building_data.get("buildings", {}) 
            if name not in coordinates_map
        ]
        if missing_coordinates:
            print(f"\nBuildings missing coordinates ({len(missing_coordinates)}):")
            for name in missing_coordinates:
                print(f"  - {name}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Add building coordinates to filtered buildings data')
    parser.add_argument('--term', default='SP26', help='Term code (e.g., SP26, FA25)')
    
    args = parser.parse_args()
    
    processor = BuildingCoordinateProcessor(term_code=args.term)
    processor.process()


if __name__ == "__main__":
    main()
