# Hostel Complaint Management System

## Run (Visual Studio / VS Code Terminal)
1. Open this folder in Visual Studio or VS Code.
2. In terminal:
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
   - `pip install -r requirements.txt`
   - `python app.py`
3. Open: http://127.0.0.1:5000

## Features
- Branded with `Tagore Engineering College` name and logo in all portals
- Student login using roll number starting with `4127`
- File complaints in categories: Electrical Fault, Room Related, Food, Water, Bathroom
- Additional complaint requirements: Hostel Block, Room Number, Priority (Low/Medium/High), detailed description
- Validation rules: max 5 active complaints per student, description length checks
- Student complaint status + history
- Admin account creation + login
- Admin password policy: minimum 8 characters with letters and numbers
- Admin can view complaints, filter by status/category/priority, update status, set priority, assign staff, add remarks
- Admin view hides student identity
