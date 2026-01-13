"""
Transform subject-sorted course data into building-sorted data.

Input: courses_SP26.json (subject-sorted)
Output: buildings_derived_SP26.json (building-sorted)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class SubjectToBuildingsProcessor:
    def __init__(self, term_code: str = "SP26"):
        self.term_code = term_code
        self.data_dir = Path(__file__).parent / "archive"
        self.input_file = self.data_dir / f"courses_{term_code}.json"
        self.output_file = self.data_dir / f"buildings_derived_{term_code}.json"

    def load_subject_data(self) -> Dict:
        """Load the subject-sorted course data."""
        with open(self.input_file, "r") as f:
            return json.load(f)

    def process_to_buildings(self, subject_data: Dict) -> Dict:
        """
        Transform subject-sorted data into building-sorted data.
        
        Structure:
        {
            "buildings": {
                "BA1": {
                    "rooms": {
                        "O107": [
                            {
                                "course": "ACG 2021",
                                "title": "Principles of Financial Accounting",
                                "time": {"start": "07:30", "end": "08:50"},
                                "days": ["M", "W"],
                                "start_date": "2026-01-12",
                                "end_date": "2026-05-05"
                            }
                        ]
                    },
                    "total_sections": 42
                }
            }
        }
        """
        buildings: Dict[str, Dict[str, Any]] = {}

        for subject in subject_data.get("subjects", []):
            subject_code = subject.get("code", "")
            
            for course in subject.get("courses", []):
                course_number = course.get("number", "")
                course_title = course.get("title", "")
                
                for section in course.get("sections", []):
                    location = section.get("location")
                    if not location:
                        continue
                    
                    building_code = location.get("building", "")
                    room_number = location.get("room", "")
                    
                    if not building_code or not room_number:
                        continue

                    # Initialize building if not exists
                    if building_code not in buildings:
                        buildings[building_code] = {
                            "rooms": {},
                            "total_sections": 0
                        }

                    # Initialize room if not exists
                    if room_number not in buildings[building_code]["rooms"]:
                        buildings[building_code]["rooms"][room_number] = []

                    # Build section info
                    # Course number already includes subject code (e.g., "ACG 2021")
                    section_info = {
                        "course": course_number,
                        "title": course_title,
                        "time": section.get("time"),
                        "days": section.get("days", []),
                        "start_date": section.get("start_date", ""),
                        "end_date": section.get("end_date", "")
                    }
                    
                    buildings[building_code]["rooms"][room_number].append(section_info)
                    buildings[building_code]["total_sections"] += 1

        return {
            "last_updated": datetime.now().isoformat(),
            "term": subject_data.get("term", f"Spring {self.term_code[2:]}"),
            "buildings": buildings
        }

    def save_building_data(self, building_data: Dict):
        """Save the building-sorted data to JSON file."""
        with open(self.output_file, "w") as f:
            json.dump(building_data, f, indent=2)

    def get_stats(self, building_data: Dict) -> Dict:
        """Get statistics about the processed data."""
        buildings = building_data.get("buildings", {})
        
        total_buildings = len(buildings)
        total_rooms = sum(len(b["rooms"]) for b in buildings.values())
        total_sections = sum(b["total_sections"] for b in buildings.values())
        
        # Find buildings with most rooms
        sorted_buildings = sorted(
            buildings.items(),
            key=lambda x: len(x[1]["rooms"]),
            reverse=True
        )
        
        return {
            "total_buildings": total_buildings,
            "total_rooms": total_rooms,
            "total_sections": total_sections,
            "top_buildings": [(b[0], len(b[1]["rooms"])) for b in sorted_buildings[:10]]
        }

    def process(self) -> Dict:
        """Main processing function."""
        print(f"Loading subject data from {self.input_file}...")
        subject_data = self.load_subject_data()

        print("Transforming subjects into building-sorted data...")
        building_data = self.process_to_buildings(subject_data)

        print(f"Saving building data to {self.output_file}...")
        self.save_building_data(building_data)

        stats = self.get_stats(building_data)
        
        print("\n" + "=" * 50)
        print("Processing complete!")
        print("=" * 50)
        print(f"Total buildings: {stats['total_buildings']}")
        print(f"Total rooms: {stats['total_rooms']}")
        print(f"Total sections: {stats['total_sections']}")
        print("\nTop 10 buildings by room count:")
        for building, room_count in stats["top_buildings"]:
            print(f"  {building}: {room_count} rooms")
        
        return building_data


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Transform course data from subject-sorted to building-sorted')
    parser.add_argument('--term', default='SP26', help='Term code (e.g., SP26, FA25)')
    
    args = parser.parse_args()
    
    processor = SubjectToBuildingsProcessor(term_code=args.term)
    processor.process()


if __name__ == "__main__":
    main()
