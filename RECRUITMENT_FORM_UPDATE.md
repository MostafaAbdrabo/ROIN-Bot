# RECRUITMENT FORM UPDATE — Add to RECRUITMENT_SYSTEM_PROMPT.md
# This ADDS the exact PDF format for the Personnel Requisition Form (Заявка на подбор персонала)
# Send BOTH files to Claude Code together.

====================================================================
# REPLACE SECTION B (Hiring Request) PDF FORMAT
====================================================================

## Personnel Requisition Form — Exact Layout
The company already uses this form. The bot must generate it EXACTLY like this.
Bilingual: Russian (left) + English (right) throughout.
Font: DejaVu (for Cyrillic support) — same as memo system.
Page: A4 Portrait.

```
[TOP LEFT]                                    [TOP RIGHT]
Директору филиала                             To the Director of the Branch
ROIN WORLD FZE в АРЕ                          ROIN WORLD FZE in ARE
[DIRECTOR_LAST_NAME] [DIRECTOR_INITIALS]      [DIRECTOR_NAME_EN]


            Заявка на подбор персонала
            Personnel Requisition Form

    Прошу принять на работу в ROIN WORLD FZE в АРЕ
    I request to hire at ROIN WORLD FZE in ARE

Количество вакансий / Number of staff required: [NUM_POSITIONS]
Вакансия (Должность / Job Title): [POSITION_TITLE]
В отдел / department: [DEPARTMENT]
Текущее количество сотрудников / Current headcount in department: [CURRENT_HEADCOUNT]
Количество сотрудников согласно ШР / Headcount as per staff schedule: (HR) [SCHEDULED_HEADCOUNT]

Причина запроса / Request Reason:
[REASON_TEXT — can be multiple lines]
_____________________________________________________________________________


Руководитель отдела / Department Head    _________________________
                                         (Подпись и дата / signature and date)
                                         [DEPT_HEAD_SIGNATURE]
                                         [DEPT_HEAD_NAME]
                                         [DATE]

Согласовано / موافق عليه:

Начальник ОРП
Head of HRD              __________      [HR_HEAD_NAME_RU] / [HR_HEAD_NAME_EN]
                      (подпись/signature)  (ФИО / full name)
                      [HR_HEAD_SIGNATURE]

HR Manager
HR Менеджер              __________      [HR_MANAGER_NAME_RU] / [HR_MANAGER_NAME_EN]
                      (подпись/signature)  (ФИО / full name)
                      [HR_MANAGER_SIGNATURE]

Директор по развитию
общественного питания
Director of Catering     __________      [CATERING_DIR_NAME_RU] / [CATERING_DIR_NAME_EN]
Development           (подпись/signature)  (ФИО / full name)
                      [CATERING_DIR_SIGNATURE]

Директор филиала
Branch director          __________      [DIRECTOR_NAME_RU] / [DIRECTOR_NAME_EN]
                      (подпись/signature)  (ФИО / full name)
                      [DIRECTOR_SIGNATURE]
                      [COMPANY_LOGO_STAMP]


[BOTTOM LEFT]
Принял заявку:
Рекрутер
[RECRUITER_NAME]
Дата: [REGISTRATION_DATE]
[RECRUITER_SIGNATURE]
```

## Approval Chain for Personnel Requisition
This form has a SPECIFIC approval chain (different from leave):

1. Department Head (the one requesting) → signs on submission
2. Head of HRD (HR Department Head) → first approval
3. HR Manager → second approval
4. Director of Catering Development → third approval (for kitchen/food positions)
   NOTE: This approver may vary depending on the department.
   - Kitchen positions → Catering Director approves
   - Other positions → skip this step OR replace with relevant director
5. Branch Director → final approval

In the bot:
- Step 1: Department Manager submits → their signature applied
- Step 2: HR_Staff or HR_Manager reviews → HR signature applied
- Step 3: HR_Manager approves → HR Manager signature applied
- Step 4: Relevant senior manager approves (if applicable)
- Step 5: Director final approval → Director signature + company stamp

## Additional Fields from the Real Form

Add these fields to the Hiring Request flow in the bot:

### Current Headcount
When manager submits hiring request, bot auto-calculates:
- Count employees in Employee_DB where Department = manager's department AND Status = Active
- Display as "Current headcount in department: X"

### Scheduled Headcount (HR fills)
HR has a staffing plan. When HR reviews the request:
- HR enters: "Headcount as per staff schedule: Y"
- This helps Director see: current X vs planned Y vs requesting +Z

### Recruiter Field
Bottom of form shows: "Принял заявку: Рекрутер [Name]"
This is the HR_Staff member who processes/registers the request.
Auto-filled with the HR staff who clicks "Register" on the request.

## Registration Number for Hiring Requests
Format: ЗП-YYYY-NNNN (ЗП = Заявка на Подбор)
Or simpler: HR_REQ-YYYY-NNNN
Track in Hiring_Requests tab.

====================================================================
# ADDITIONAL: FACEBOOK AUTO-POSTING HELPER
====================================================================

Since auto-posting to 300 Facebook groups violates Facebook ToS and risks
banning the company page, add this ALTERNATIVE feature to the bot:

## Job Post Generator
When HR creates a job posting in the recruitment system:
1. Bot generates FORMATTED job post text optimized for Facebook/social media
2. Creates 3 VARIATIONS of the same post (different hooks/styles) using Gemini AI
3. Each variation:
   - Catchy opening line
   - Job title + location (El Dabaa)
   - Key requirements (bullet points)
   - Benefits/salary range
   - How to apply (phone number / WhatsApp)
   - Company name + logo description
4. HR copies and pastes manually — but the WRITING is done by AI in seconds
5. Bot can generate in: Arabic, English, or both

This saves HR 80% of the time — instead of writing 300 posts,
HR copies ONE AI-generated post and pastes it.

Add to Job Postings flow:
After creating a posting → [📱 Generate Social Media Post]
→ Shows 3 variations → HR picks one → copies text → done

====================================================================
# ALSO UPDATE THE RECRUITMENT DASHBOARD
====================================================================

Add to the dashboard:
- Requisitions this month: X submitted / X approved / X rejected
- Open positions by department (visual count)
- Candidates pipeline funnel: New → Screened → Interview → Offered → Hired
- Average days to fill (from approval to hire)
- Source effectiveness: which source brings best candidates

====================================================================
