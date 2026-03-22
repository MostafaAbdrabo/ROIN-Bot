"""
ROIN WORLD FZE -- Add 40 Test Employees for All Departments
=============================================================
Run once: python3 setup_test_employees.py
Adds test employees to Employee_DB and User_Registry.
Password for ALL = Pass@[Emp_Code]
"""
import bcrypt
from config import get_sheet

# (Emp_Code, Full_Name, Department, Job_Title, Bot_Role, Manager_Code)
TEST_EMPLOYEES = [
    # Director
    ("2001", "Viktor Petrov",              "Management",          "Company Director",        "Director",              ""),
    # HR
    ("2010", "Layla HR Manager",           "HR",                  "HR Manager",              "HR_Manager",            "2001"),
    ("2011", "Dina HR Staff 1",            "HR",                  "HR Specialist",           "HR_Staff",              "2010"),
    ("2012", "Nada HR Staff 2",            "HR",                  "HR Specialist",           "HR_Staff",              "2010"),
    # Egyptian Kitchen
    ("2020", "Youssef Kitchen Mgr",        "Egyptian Kitchen",    "Head Chef",               "Direct_Manager",        "2001"),
    ("2021", "Amr Kitchen Supervisor",     "Egyptian Kitchen",    "Shift Supervisor",        "Supervisor",            "2020"),
    ("2022", "Tamer Kitchen Worker 1",     "Egyptian Kitchen",    "Cook",                    "Employee",              "2020"),
    ("2023", "Hossam Kitchen Worker 2",    "Egyptian Kitchen",    "Cook",                    "Employee",              "2020"),
    # Russian Kitchen
    ("2030", "Alexei Russian Kitchen Mgr", "Russian Kitchen",     "Head Chef",               "Direct_Manager",        "2001"),
    ("2031", "Igor Russian Cook",          "Russian Kitchen",     "Cook",                    "Employee",              "2030"),
    # Warehouse
    ("3001", "Khaled Warehouse Mgr",       "Warehouse",           "Warehouse Manager",       "Warehouse_Manager",     "2001"),
    ("3002", "Hassan WH Assistant",        "Warehouse",           "Warehouse Supervisor",    "Warehouse_Specialist",  "3001"),
    ("3003", "Ali Store Keeper 1",         "Warehouse",           "Store Keeper WH-1",       "Store_Keeper",          "3001"),
    ("3004", "Omar Store Keeper 2",        "Warehouse",           "Store Keeper WH-2",       "Store_Keeper",          "3001"),
    ("3005", "Mahmoud Store Keeper 3",     "Warehouse",           "Store Keeper WH-3",       "Store_Keeper",          "3001"),
    # Translation
    ("3010", "Natalia Translation Mgr",    "Translation",         "Translation Manager",     "Translation_Manager",   "2001"),
    ("3011", "Dmitry Translator RU",       "Translation",         "Translator RU-AR",        "Translator",            "3010"),
    ("3012", "Fatma Translator AR",        "Translation",         "Translator AR-EN",        "Translator",            "3010"),
    ("3013", "Sergei Translator RU2",      "Translation",         "Translator RU-EN",        "Translator",            "3010"),
    ("3014", "Maha Translator AR2",        "Translation",         "Translator AR-RU",        "Translator",            "3010"),
    ("3015", "Pavel Translator RU3",       "Translation",         "Translator EN-RU",        "Translator",            "3010"),
    # Operations
    ("3020", "Ahmed Operations Mgr",       "Operations",          "Operations Manager",      "Operations_Manager",    "2001"),
    ("3021", "Yasser Operations Spec",     "Operations",          "Operations Specialist",   "Operations_Specialist", "3020"),
    ("3022", "Tarek Operations Coord",     "Operations",          "Operations Coordinator",  "Operations_Coordinator","3020"),
    # Packaging & Delivery
    ("3030", "Samir Packaging Mgr",        "Packaging & Delivery","Packaging Manager",       "Packaging_Manager",     "3020"),
    ("3031", "Hany Packaging Spec",        "Packaging & Delivery","Packaging Specialist",    "Packaging_Specialist",  "3030"),
    ("3032", "Wael Delivery Coord",        "Packaging & Delivery","Delivery Coordinator",    "Packaging_Specialist",  "3030"),
    # Purchasing
    ("3040", "Ibrahim Supply Mgr",         "Purchasing",          "Supply Manager",          "Supply_Manager",        "2001"),
    ("3041", "Ayman Supply Spec",          "Purchasing",          "Supply Specialist",       "Supply_Specialist",     "3040"),
    # Quality Control
    ("3050", "Rami Quality Mgr",           "Quality Control",     "Quality Manager",         "Quality_Manager",       "2001"),
    ("3051", "Nour Quality Spec",          "Quality Control",     "Quality Specialist",      "Quality_Specialist",    "3050"),
    # Housing
    ("3060", "Fathi Housing Mgr",          "Housing",             "Housing Manager",         "Housing_Manager",       "2001"),
    ("3061", "Samy Housing Spec",          "Housing",             "Housing Specialist",      "Housing_Specialist",    "3060"),
    # Transport
    ("3070", "Magdy Transport Mgr",        "Transportation",      "Transport Manager",       "Transport_Manager",     "2001"),
    ("3071", "Walid Driver 1",             "Transportation",      "Driver",                  "Driver",                "3070"),
    ("3072", "Tarek Driver 2",             "Transportation",      "Driver",                  "Driver",                "3070"),
    # Safety
    ("3080", "Sherif Safety Mgr",          "Safety",              "Safety Manager",          "Safety_Manager",        "2001"),
]


def main():
    edb = get_sheet("Employee_DB")
    existing_codes = {r[0].strip() for r in edb.get_all_values()[1:] if r}
    ureg = get_sheet("User_Registry")
    existing_ureg = {r[0].strip() for r in ureg.get_all_values()[1:] if r}

    added_edb = 0
    added_ureg = 0

    for ec, name, dept, title, role, mgr in TEST_EMPLOYEES:
        if ec not in existing_codes:
            row = [""] * 34
            row[0]  = ec             # Emp_Code
            row[1]  = name           # Full_Name
            row[6]  = dept           # Department
            row[7]  = title          # Job_Title
            row[8]  = "8"            # Shift_Hours
            row[17] = mgr            # Manager_Code
            row[18] = "MGR_HR_DIR"   # Approval_Chain
            row[19] = mgr            # Supervisor_Code
            row[22] = role           # Bot_Role
            row[23] = "EN"           # Preferred_Language
            row[24] = "21"           # Annual_Leave_Balance
            row[25] = "Active"       # Status
            row[29] = "Friday"       # Off_Type
            row[32] = dept           # Work_Location
            edb.append_row(row, value_input_option="USER_ENTERED")
            print(f"  EDB: ADDED {ec} - {name} ({role})")
            added_edb += 1
        else:
            print(f"  EDB: SKIP {ec}")

        if ec not in existing_ureg:
            pw = f"Pass@{ec}"
            pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()
            ureg.append_row([ec, "", pw_hash, role, "", "Active", "0", ""],
                           value_input_option="USER_ENTERED")
            print(f"  REG: ADDED {ec} role={role} pw={pw}")
            added_ureg += 1
        else:
            print(f"  REG: SKIP {ec}")

    print(f"\nDone. {added_edb} to Employee_DB, {added_ureg} to User_Registry.")


if __name__ == "__main__":
    main()
