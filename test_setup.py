"""
ROIN WORLD FZE — Setup Test
Run this to verify everything is installed and connected.
"""

print("=" * 50)
print("ROIN HR BOT — SETUP TEST")
print("=" * 50)

# Test 1: Check all libraries
print("\n[1/5] Checking Python libraries...")
errors = []
for lib in ["telegram", "gspread", "google.oauth2", "bcrypt", "fpdf", "google.generativeai"]:
    try:
        __import__(lib)
        print(f"  OK  {lib}")
    except ImportError:
        print(f"  FAIL  {lib} — not installed")
        errors.append(lib)

if errors:
    print(f"\nMISSING LIBRARIES: {errors}")
    print("Run: pip3 install -r requirements.txt")
    exit(1)

# Test 2: Check files exist
print("\n[2/5] Checking project files...")
import os
base = os.path.dirname(os.path.abspath(__file__))
files = ["bot_token.txt", "sheet_id.txt", "credentials.json", "config.py", "requirements.txt"]
for f in files:
    path = os.path.join(base, f)
    if os.path.exists(path):
        print(f"  OK  {f}")
    else:
        print(f"  FAIL  {f} — file not found")
        errors.append(f)

# Test 3: Read config
print("\n[3/5] Loading config.py...")
try:
    from config import BOT_TOKEN, SHEET_ID, WORKBOOK
    print(f"  OK  Bot token loaded ({len(BOT_TOKEN)} chars)")
    print(f"  OK  Sheet ID: {SHEET_ID[:20]}...")
except Exception as e:
    print(f"  FAIL  {e}")
    errors.append("config")

# Test 4: Read Google Sheet
print("\n[4/5] Reading Employee_DB from Google Sheet...")
try:
    from config import get_sheet, TAB_EMPLOYEE_DB
    ws = get_sheet(TAB_EMPLOYEE_DB)
    row2 = ws.row_values(2)
    print(f"  OK  First employee: {row2[0]} - {row2[1]}")
    tabs = [s.title for s in WORKBOOK.worksheets()]
    print(f"  OK  Tabs found: {tabs}")
except Exception as e:
    print(f"  FAIL  {e}")
    errors.append("sheets")

# Test 5: Check bcrypt
print("\n[5/5] Testing bcrypt password hashing...")
try:
    import bcrypt
    test_password = "Pass@001"
    hashed = bcrypt.hashpw(test_password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    check = bcrypt.checkpw(test_password.encode("utf-8"), hashed)
    print(f"  OK  Hash generated: {hashed[:30].decode()}...")
    print(f"  OK  Password verify: {check}")
except Exception as e:
    print(f"  FAIL  {e}")
    errors.append("bcrypt")

# Final result
print("\n" + "=" * 50)
if errors:
    print(f"SETUP INCOMPLETE — {len(errors)} issue(s) found")
    print(f"Problems: {errors}")
else:
    print("ALL TESTS PASSED — READY TO BUILD THE BOT!")
print("=" * 50)
