# TASK 4: RECRUITMENT / HIRING SYSTEM — COMPLETE MODULE
# Build the ENTIRE thing in one session non-stop.
# After ALL sections done: "All done — ready to test" → STOP.
#
# SAME RULES AS ALWAYS apply.

====================================================================
# OVERVIEW: What This System Does
====================================================================

A complete hiring pipeline inside the Telegram bot:
1. Department manager requests a new hire
2. Director approves the position
3. HR creates job posting
4. Candidates apply (HR enters them manually or via form)
5. Screening → Shortlisting → Interview scheduling
6. Interview feedback from panel
7. Selection → Offer → Director approval
8. Onboarding into the main Employee_DB system

Everything tracked, logged, and reportable.

====================================================================
# SECTION A: NEW ROLE + MENU
====================================================================

No new role needed. Recruitment is handled by:
- HR_Staff: creates postings, manages candidates, schedules interviews
- HR_Manager: approves postings, reviews candidates, makes recommendations
- Direct_Manager: requests new hire, participates in interviews, gives feedback
- Director: approves position, approves final hire
- Bot_Manager: full access to everything

Add to these roles' menus:
👔 Recruitment (sub-menu with all recruitment features)

Sub-menu:
├── 📋 Hiring Requests (request a new position)
├── 📢 Job Postings (create/manage postings)
├── 👤 Candidates (view/add/manage)
├── 📅 Interviews (schedule/view)
├── ✅ Selections (approve/offer)
├── 📊 Recruitment Dashboard
└── ↩️ Back

Who sees what:
| Feature | Director | HR_Manager | HR_Staff | Direct_Manager |
|---------|----------|------------|----------|----------------|
| Hiring Requests | Approve | View all | View all | Create + View own |
| Job Postings | View | Create + Manage | Create + Manage | View own dept |
| Candidates | View shortlisted | Full access | Full access | View for own requests |
| Interviews | View | Schedule + Manage | Schedule + Manage | Give feedback |
| Selections | Final approve | Recommend | Process | Recommend |
| Dashboard | Full | Full | Full | Own department |

====================================================================
# SECTION B: HIRING REQUEST FLOW
====================================================================

## B1. Department Manager Requests New Hire
1. Manager taps 👔 Recruitment → 📋 New Hiring Request
2. Fill in:
   - Position title (text)
   - Department (auto from their department)
   - Number of positions (1-10)
   - Priority: Normal / Urgent / Critical
   - Justification/reason (text — AI can improve this)
   - Required start date
   - Contract type: Fixed-term / Permanent / Temporary
   - Shift: Day / Night / Rotating
   - Work location (from 5 locations)
   - Salary range (optional)
   - Special requirements (text, optional)
3. Summary → Submit
4. Goes to HR_Manager for review
5. HR_Manager forwards to Director with recommendation
6. Director approves or rejects

## B2. Hiring Request Log
New tab: Hiring_Requests
Columns:
HR_ID, Date, Requesting_Manager_Code, Requesting_Manager_Name(VLOOKUP),
Department, Position_Title, Num_Positions, Priority, Justification,
Required_Start_Date, Contract_Type, Shift, Work_Location, Salary_Range,
Special_Requirements, HR_Status, HR_Date, HR_Notes,
Director_Status, Director_Date, Director_Notes,
Final_Status (Requested/HR_Reviewed/Approved/Rejected/Filled/Cancelled),
Job_Posting_ID, Created_At

## B3. Status Flow
Requested → HR_Reviewed → Director_Approved → Posting_Created →
Candidates_Screening → Interviews → Selected → Offer_Made →
Offer_Accepted → Onboarding → Filled

OR: Requested → Rejected (at any stage)

====================================================================
# SECTION C: JOB POSTINGS
====================================================================

## C1. Create Job Posting
After hiring request is approved:
1. HR taps 📢 Job Postings → ➕ Create Posting
2. Select approved hiring request (shows list of approved, unfilled requests)
3. Auto-fills: title, department, location, requirements from the request
4. HR adds:
   - Full job description (AI can improve)
   - Requirements: education, experience, skills, languages
   - Benefits summary
   - Application deadline
   - Contact info
5. Select languages: Arabic / English / Russian / Arabic+English
6. AI can translate/improve in selected languages
7. Preview → Publish

## C2. Job Posting Output
Bot generates a formatted job posting text that HR can:
- Copy and paste to Facebook / job sites manually
- Send via the bot's announcement system to all employees (for referrals)
- Generate as a PDF flyer

## C3. Job_Postings tab
Columns:
Posting_ID (JP-YYYY-NNNN), HR_Request_ID, Date, Position_Title,
Department, Location, Description_AR, Description_EN, Description_RU,
Requirements, Benefits, Deadline, Status (Draft/Active/Closed/Filled),
Candidates_Count, Created_By, Created_At

====================================================================
# SECTION D: CANDIDATE MANAGEMENT
====================================================================

## D1. Adding Candidates
HR adds candidates manually (since applications come via phone, WhatsApp, walk-in):
1. HR taps 👤 Candidates → ➕ Add Candidate
2. Select which job posting this candidate is for
3. Fill in:
   - Full name
   - Phone number
   - National ID (optional at this stage)
   - Source: Facebook / Referral / Walk-in / Job Site / Other
   - Education level: Primary / Secondary / Diploma / Bachelor / Master
   - Years of experience (number)
   - Current/previous employer (optional)
   - Skills/notes (text)
   - Resume/CV file (optional — upload photo or PDF)
4. Status = New

## D2. Candidate Pipeline
Each candidate moves through stages:
New → Screened → Shortlisted → Interview_Scheduled →
Interviewed → Selected → Offer_Sent → Offer_Accepted → Hired

OR: Rejected (at any stage, with reason)

## D3. Screening
HR reviews each new candidate:
- View details
- Rate: ⭐ 1-5 stars
- Decision: [✅ Shortlist] [❌ Reject] [⏸ Hold]
- If shortlisted → moves to interview stage

## D4. Candidates tab
Columns:
Candidate_ID (CND-YYYY-NNNN), Posting_ID, Name, Phone, National_ID,
Source, Education, Experience_Years, Previous_Employer, Skills_Notes,
Resume_Link, Screening_Rating, Screening_Notes, Screening_By,
Interview_Date, Interview_Time, Interview_Panel_JSON,
Interview_Feedback_JSON, Final_Rating,
Status (New/Screened/Shortlisted/Interview_Scheduled/Interviewed/Selected/
        Offer_Sent/Offer_Accepted/Hired/Rejected/Withdrawn),
Rejection_Reason, Offer_Salary, Offer_Date, Start_Date,
Emp_Code_Assigned, Created_At

====================================================================
# SECTION E: INTERVIEW MANAGEMENT
====================================================================

## E1. Schedule Interview
HR selects shortlisted candidate → Schedule Interview:
1. Select date + time
2. Select interview panel (choose from employee list — managers who will interview)
3. Add interview notes/questions to prepare
4. Confirm → candidate status = Interview_Scheduled

## E2. Interview Feedback
After interview, each panel member gives feedback via bot:
1. Bot shows: "Interview feedback for [Candidate Name]"
2. Rate (1-5): Technical Skills, Communication, Experience, Culture Fit
3. Overall recommendation: [✅ Hire] [⚠️ Maybe] [❌ Don't Hire]
4. Comments (text)
5. Submit → saved to Interview_Feedback_JSON

## E3. View Interview Results
HR/Manager sees all panel feedback in one view:
- Per panel member: ratings + recommendation
- Average scores
- Consensus: if majority says Hire → highlight green

====================================================================
# SECTION F: SELECTION & OFFER
====================================================================

## F1. Selection
HR reviews all interviewed candidates for a posting:
- Shows candidates ranked by interview scores
- HR recommends top candidate(s) to HR_Manager
- HR_Manager reviews → recommends to Director
- Director approves: [✅ Approve Hire] [❌ Reject]

## F2. Job Offer
After Director approves:
1. HR enters offer details:
   - Salary
   - Start date
   - Contract type + duration
   - Benefits
   - Special conditions
2. Generate offer letter PDF (bilingual RU + EN) — same company template
3. Send to candidate (via HR manually — they print or email it)
4. Track response: Offer_Sent → Offer_Accepted / Offer_Rejected

## F3. If Offer Rejected
Candidate status = Withdrawn
HR can select next candidate from the shortlist without restarting.

====================================================================
# SECTION G: ONBOARDING — CONNECT TO MAIN SYSTEM
====================================================================

## G1. When Candidate Accepts Offer
HR taps "✅ Onboard" on the candidate:
1. Bot auto-creates employee record in Employee_DB:
   - Assigns next available Emp_Code
   - Fills: name, phone, national ID, department, job title, hire date, contract dates
   - Sets Bot_Role based on position
   - Sets Manager_Code, Approval_Chain, Shift_Hours, Off_Type, Work_Location
2. Creates row in User_Registry (password = Emp_Code)
3. Creates row in Leave_Balance (initial entitlements)
4. Creates Google Drive folder for the employee
5. Generates employment contract PDF (if template available)
6. Candidate status = Hired, Emp_Code_Assigned = new code

## G2. Onboarding Checklist
Track per new hire:
- [ ] Employee_DB record created
- [ ] User_Registry created
- [ ] Leave_Balance initialized
- [ ] Drive folder created
- [ ] Contract signed
- [ ] Documents collected (ID, photos, certificates)
- [ ] JD assigned
- [ ] Safety training scheduled
- [ ] Manager introduced
- [ ] Equipment/uniform issued

Tab: Onboarding_Checklist
Columns: Emp_Code, Candidate_ID, Item, Status (Done/Pending), Date_Completed, Notes

====================================================================
# SECTION H: RECRUITMENT DASHBOARD
====================================================================

Bot_Manager / HR_Manager / Director sees:

📊 Recruitment Dashboard
- Open positions: X (approved but not filled)
- Active postings: X
- Total candidates this month: X
- Pipeline: New X → Screened X → Shortlisted X → Interview X → Selected X
- Avg time to fill: X days
- By department: positions open per dept
- By source: where candidates come from (Facebook X%, Referral X%, etc.)

====================================================================
# SECTION I: GOOGLE SHEET TABS
====================================================================

Create these new tabs (headers + VLOOKUP where applicable):

### Hiring_Requests
(columns from B2 above)

### Job_Postings
(columns from C3 above)

### Candidates
(columns from D4 above)

### Onboarding_Checklist
(columns from G2 above)

All tabs: auto-create if missing, VLOOKUP for names where Emp_Code exists.

====================================================================
# SECTION J: DRIVE FOLDERS
====================================================================

/Recruitment/
├── /Postings/[YEAR]/ — job posting PDFs/flyers
├── /Candidates/[CND-ID]_[Name]/ — resumes, documents
├── /Offers/[YEAR]/[MONTH]/ — offer letters
└── /Reports/ — recruitment reports

====================================================================
# SECTION K: AI FEATURES IN RECRUITMENT
====================================================================

## K1. Job Description Improvement
When HR writes job posting, AI can:
- Improve language
- Make it more attractive
- Add relevant keywords
- Translate between AR/EN/RU

Use same AI writing assistant flow (iterate, custom instructions, manual edit).

## K2. Screening Assistant
HR can tap "🤖 AI Screen" on a candidate:
- AI compares candidate's skills/experience with job requirements
- Returns: Match score (%), strengths, gaps, recommendation
- HR makes final decision (AI is advisory only)

## K3. Interview Questions Generator
HR can tap "🤖 Suggest Questions" for a posting:
- AI generates 10 interview questions tailored to the role
- Mix of technical, behavioral, and situational questions
- HR can use, modify, or ignore them

====================================================================
# SECTION L: REFERRAL SYSTEM
====================================================================

## L1. Employee Referrals
Any employee can refer a candidate:
1. Employee taps 👔 Recruitment → 🤝 Refer Someone
2. Enter: candidate name, phone, position they're good for, relationship
3. Saved to Candidates tab with Source = "Referral" + referring employee code
4. If referral gets hired: tracked for referral bonus (if company has one)

## L2. Referral Tracking
Candidates tab has: Referred_By column
When candidate is hired: referral credit logged

====================================================================
# BUILD ORDER (all in one session)
====================================================================

A (menus) → B (hiring requests) → C (job postings) → D (candidates) →
E (interviews) → F (selection & offer) → G (onboarding) →
H (dashboard) → I (sheet tabs) → J (drive) → K (AI) → L (referrals)

Build everything. Register all handlers in bot.py.
After ALL sections: "All done — ready to test" → STOP.

START NOW.
====================================================================
