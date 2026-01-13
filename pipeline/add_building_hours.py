"""
Add building hours to filtered buildings data.

Input: archive/buildings_filtered_SP26.json
Hours: data/building_hours.json
Output: archive/buildings_filtered_SP26.json (updated in place)
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any, Optional


class BuildingHoursProcessor:
    def __init__(self, term_code: str = "SP26"):
        self.term_code = term_code
        self.archive_dir = Path(__file__).parent / "archive"
        self.data_dir = Path(__file__).parent / "data"
        self.buildings_file = self.archive_dir / f"buildings_filtered_{term_code}.json"
        self.hours_file = self.data_dir / "building_hours.json"
        
        # Map day groups to individual days
        self.days_mapping = {
            "M-TH": ["monday", "tuesday", "wednesday", "thursday"],
            "F": ["friday"],
            "SAT": ["saturday"],
            "SUN": ["sunday"],
        }

    def load_data(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Load buildings data and hours data."""
        with open(self.buildings_file, "r") as f:
            buildings_data = json.load(f)

        with open(self.hours_file, "r") as f:
            hours_data = json.load(f)

        return buildings_data, hours_data

    def save_data(self, data: Dict[str, Any]) -> None:
        """Save the updated buildings data."""
        with open(self.buildings_file, "w") as f:
            json.dump(data, f, indent=2)

    def convert_time_format(self, time_str: str) -> Optional[str]:
        """Convert time string from 12-hour format to 24-hour format."""
        if time_str == "LOCKED":
            return None

        time_str = time_str.strip()

        # Handle midnight edge case
        if time_str.upper() in ["12AM", "12:00AM"]:
            return "23:59"

        try:
            # Try parsing with colon (e.g., "7:30AM")
            if ":" in time_str:
                return datetime.strptime(time_str, "%I:%M%p").strftime("%H:%M")
            # Try parsing without colon (e.g., "7AM")
            return datetime.strptime(time_str, "%I%p").strftime("%H:%M")
        except ValueError as e:
            print(f"Error converting time: {time_str}")
            raise e

    def parse_building_hours(
        self, hours_dict: Dict[str, str]
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Parse building hours from day-group format to individual day format.
        
        Input format: {"M-TH": "7:30AM-10:00PM", "F": "7:30AM-6:00PM", ...}
        Output format: {"monday": {"open": "07:30", "close": "22:00"}, ...}
        """
        formatted_hours = {}

        for day_group, hours in hours_dict.items():
            if day_group not in self.days_mapping:
                print(f"Warning: Unknown day group '{day_group}', skipping")
                continue
                
            if hours == "LOCKED":
                for day in self.days_mapping[day_group]:
                    formatted_hours[day] = {"open": None, "close": None}
                continue

            # Split on last hyphen to handle times like "10:00PM"
            parts = hours.rsplit("-", 1)
            if len(parts) != 2:
                print(f"Invalid hours format: {hours}")
                continue

            start_time, end_time = parts
            start_time_24h = self.convert_time_format(start_time.strip())
            end_time_24h = self.convert_time_format(end_time.strip())

            for day in self.days_mapping[day_group]:
                formatted_hours[day] = {"open": start_time_24h, "close": end_time_24h}

        return formatted_hours

    def process(self) -> None:
        """Main processing function."""
        print(f"Loading buildings data from {self.buildings_file}...")
        print(f"Loading hours data from {self.hours_file}...")
        buildings_data, hours_data = self.load_data()

        buildings_updated = 0
        buildings_missing = []
        
        print("\nProcessing building hours...")
        for building_code in buildings_data.get("buildings", {}):
            if building_code in hours_data:
                buildings_data["buildings"][building_code]["hours"] = (
                    self.parse_building_hours(hours_data[building_code])
                )
                buildings_updated += 1
                print(f"  ✓ Updated hours for: {building_code}")
            else:
                buildings_missing.append(building_code)
                print(f"  ✗ Missing hours for: {building_code}")

        print(f"\nSaving updated buildings data...")
        self.save_data(buildings_data)

        print("\n" + "=" * 50)
        print("Processing complete!")
        print("=" * 50)
        print(f"Updated hours for {buildings_updated} buildings")

        if buildings_missing:
            print(f"\nBuildings missing hours ({len(buildings_missing)}):")
            for code in buildings_missing:
                print(f"  - {code}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Add building hours to filtered buildings data')
    parser.add_argument('--term', default='SP26', help='Term code (e.g., SP26, FA25)')
    
    args = parser.parse_args()
    
    processor = BuildingHoursProcessor(term_code=args.term)
    processor.process()


if __name__ == "__main__":
    main()
