"""
ROIN WORLD FZE — Vehicle Setup Script
======================================
Adds 10 test vehicles to the Vehicles tab in Google Sheets.
Run once: python3 setup_vehicles.py
"""

from config import get_sheet

VEHICLES = [
    # Vehicle_ID | Plate | Type | Capacity | Driver_Code | Driver_Name | Driver_Phone | Status | Notes
    ["VEH-001", "ABD 1001", "Mercedes Sprinter",    "14", "2001", "Ahmed Khaled",       "01001112201", "Available", "14-seat executive shuttle"],
    ["VEH-002", "ABD 1002", "Toyota Coaster",       "30", "2002", "Mohamed Saad",       "01001112202", "Available", "30-seat large coach"],
    ["VEH-003", "ABD 1003", "Toyota Hiace Bus",     "15", "2003", "Mahmoud Hassan",     "01001112203", "Available", "15-seat minibus"],
    ["VEH-004", "ABD 1004", "Mercedes Vito",        "8",  "2004", "Omar Fathy",         "01001112204", "Available", "8-seat VIP van"],
    ["VEH-005", "ABD 1005", "Toyota Land Cruiser",  "6",  "2005", "Youssef Ibrahim",    "01001112205", "Available", "6-seat 4x4 SUV"],
    ["VEH-006", "ABD 1006", "Mitsubishi Rosa",      "25", "2006", "Karim Mostafa",      "01001112206", "Available", "25-seat medium coach"],
    ["VEH-007", "ABD 1007", "BMW X5",               "5",  "2007", "Tarek Nasser",       "01001112207", "Available", "5-seat luxury SUV"],
    ["VEH-008", "ABD 1008", "Mercedes S-Class",     "4",  "2008", "Hossam Ramadan",     "01001112208", "Available", "4-seat VIP sedan"],
    ["VEH-009", "ABD 1009", "Range Rover Sport",    "5",  "2009", "Amr El-Sayed",       "01001112209", "Available", "5-seat executive 4x4"],
    ["VEH-010", "ABD 1010", "Hyundai H350 Van",     "12", "2010", "Walid Abdallah",     "01001112210", "Available", "12-seat cargo van"],
]

HEADER = [
    "Vehicle_ID", "Plate", "Type", "Capacity",
    "Driver_Code", "Driver_Name", "Driver_Phone", "Status", "Notes"
]


def main():
    ws = get_sheet("Vehicles")
    existing = ws.get_all_values()

    if not existing or existing[0][0] != "Vehicle_ID":
        print("Writing header row...")
        ws.update("A1", [HEADER])
        existing = [HEADER]

    existing_ids = {r[0].strip() for r in existing[1:] if r}

    added = 0
    for v in VEHICLES:
        if v[0] in existing_ids:
            print(f"  SKIP {v[0]} (already exists)")
            continue
        ws.append_row(v)
        print(f"  ADDED {v[0]} — {v[2]} ({v[5]})")
        added += 1

    print(f"\nDone. {added} vehicle(s) added.")


if __name__ == "__main__":
    main()
