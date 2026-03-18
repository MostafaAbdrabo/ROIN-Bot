"""
ROIN WORLD FZE — One-Time Password Hash Generator
===================================================
Run this ONCE to generate real bcrypt hashes for all employees
in the User_Registry tab.

After running, each employee can log in with their temporary password.

Usage: python3 generate_hashes.py
"""

import bcrypt
from config import get_sheet, TAB_USER_REGISTRY, BCRYPT_SALT_ROUNDS

print("=" * 50)
print("Generating bcrypt hashes for User_Registry...")
print("=" * 50)

# Temporary passwords: Pass@ + employee code
# Example: employee 1007 → Pass@1007
passwords = {
    "1007": "Pass@1007",
    "1008": "Pass@1008",
    "1009": "Pass@1009",
    "1011": "Pass@1011",
    "1015": "Pass@1015",
    "1022": "Pass@1022",
    "1025": "Pass@1025",
    "1027": "Pass@1027",
    "1032": "Pass@1032",
    "1034": "Pass@1034",
}

ws = get_sheet(TAB_USER_REGISTRY)
all_rows = ws.get_all_values()

updated = 0
for row_idx, row in enumerate(all_rows):
    if row_idx == 0:
        continue

    emp_code = row[0].strip()
    if emp_code in passwords:
        plain = passwords[emp_code]
        hashed = bcrypt.hashpw(
            plain.encode("utf-8"),
            bcrypt.gensalt(rounds=BCRYPT_SALT_ROUNDS)
        )
        hash_str = hashed.decode("utf-8")

        cell_row = row_idx + 1
        ws.update_cell(cell_row, 3, hash_str)

        print(f"  {emp_code}: {plain} -> {hash_str[:30]}...")
        updated += 1

print(f"\nDone! {updated} hashes written to User_Registry.")
print("=" * 50)
print("\nTemporary passwords for testing:")
for code, pwd in passwords.items():
    print(f"  {code} → {pwd}")
