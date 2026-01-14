"""
Filter buildings based on minimum room count and exclusion list.

Input: archive/buildings_derived_SP26.json
Output: archive/buildings_filtered_SP26.json
"""

from pathlib import Path
import json
from typing import Dict, Any


class BuildingDataFilter:
    def __init__(self, term_code: str = "SP26"):
        self.term_code = term_code
        self.archive_dir = Path(__file__).parent / "archive"
        self.input_file = self.archive_dir / f"buildings_derived_{term_code}.json"
        self.output_file = self.archive_dir / f"buildings_filtered_{term_code}.json"
        
        # UCF buildings to exclude (add building codes as needed)
        self.excluded_buildings = {
            "DPAC",
            "RSH",
            "CROL",
        }
        # Minimum number of rooms (inclusive)
        self.min_rooms = 4

    def load_data(self) -> Dict[str, Any]:
        """Load the buildings derived data."""
        with open(self.input_file, "r") as f:
            return json.load(f)

    def save_data(self, data: Dict[str, Any]) -> None:
        """Save the filtered building data."""
        self.archive_dir.mkdir(exist_ok=True)
        with open(self.output_file, "w") as f:
            json.dump(data, f, indent=2)

    def filter_buildings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter buildings based on room count and exclusion list."""
        filtered_data = {
            "last_updated": data.get("last_updated", ""),
            "term": data.get("term", ""),
            "buildings": {}
        }

        for building_code, building_data in data.get("buildings", {}).items():
            room_count = len(building_data["rooms"])
            print(f"Building: {building_code}, Number of rooms: {room_count}")
            
            if (
                room_count >= self.min_rooms
                and building_code not in self.excluded_buildings
            ):
                filtered_data["buildings"][building_code] = building_data
                print(f"  ✓ Added {building_code} to filtered data")
            else:
                reason = "excluded" if building_code in self.excluded_buildings else "too few rooms"
                print(f"  ✗ Skipped {building_code} ({reason})")

        return filtered_data

    def process(self) -> None:
        """Main processing function."""
        print(f"Loading buildings data from {self.input_file}...")
        data = self.load_data()

        print(f"\nFiltering buildings (minimum {self.min_rooms} rooms)...")
        filtered_data = self.filter_buildings(data)

        print(f"\nSaving filtered data to {self.output_file}...")
        self.save_data(filtered_data)

        original_count = len(data.get("buildings", {}))
        filtered_count = len(filtered_data["buildings"])
        
        print("\n" + "=" * 50)
        print("Filtering complete!")
        print("=" * 50)
        print(f"Original buildings: {original_count}")
        print(f"Filtered buildings: {filtered_count}")
        print(f"Removed: {original_count - filtered_count}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Filter buildings by minimum room count')
    parser.add_argument('--term', default='SP26', help='Term code (e.g., SP26, FA25)')
    
    args = parser.parse_args()
    
    filter_processor = BuildingDataFilter(term_code=args.term)
    filter_processor.process()


if __name__ == "__main__":
    main()
