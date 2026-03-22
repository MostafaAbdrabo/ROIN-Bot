# MOSTAFA'S PROJECT RULES — Universal Standards
# ═══════════════════════════════════════════════
# Drop this file into ANY project folder.
# Tell Claude Code: "Read PROJECT_RULES.md and follow all rules in every file you create."
# These rules apply to ALL projects: Telegram bots, web apps, courses, tools.
#
# Last updated: 21/03/2026
# To add a new rule: append it under the correct section with the next number.

====================================================================
# 1. NAVIGATION & MENU RULES
====================================================================

1.1 NESTED MENUS — NEVER flat lists.
    Every main menu item opens a sub-menu. Sub-menus can contain sub-sub-menus.
    Users drill down: Main Menu → Category → Sub-category → Action.
    Never dump 20+ buttons on one screen.

1.2 BACK BUTTON — MANDATORY on every screen.
    Every screen with buttons MUST have:
    - ↩️ Back (goes to previous screen — in multi-step flows)
    - ↩️ Main Menu (goes to the role-based home screen)
    No exceptions. Error screens, success screens, empty states — all get back buttons.

1.3 NEVER tell users to type a command to go back.
    Wrong: "Send /start to return to menu"
    Right: Show a ↩️ Main Menu button.

1.4 MENU ITEMS open sub-menus, not direct actions.
    Wrong: User taps "Leave" → immediately starts leave request flow
    Right: User taps "Leave" → sees sub-menu: Balance / Request / My Requests / etc.

1.5 LISTS are interactive — each item is a tappable button.
    When showing a list of requests/items/employees, each one is a button.
    User taps → sees detail. Never dump all details in one giant message.

1.6 ROLE-BASED MENUS — each role sees ONLY their permitted options.
    Never show a button that the user can't use. Hide it entirely.

1.7 CATEGORIZED VIEWS — group items, don't dump them.
    If there are 50 items, group them: by type, by date, by department, by status.
    User picks a category first, then sees the filtered list.

1.8 BACK BUTTON goes to PREVIOUS MENU — not Main Menu.
    When a screen shows an error, empty state, or unavailable feature:
    ↩️ Back → goes to the menu the user was in BEFORE this screen
    ↩️ Main Menu → goes to the role-based home screen
    BOTH buttons must always be present.
    The Back button callback_data must point to the PARENT menu callback,
    NOT "back_to_menu". User should never be kicked to Main Menu unexpectedly.
    This applies to every nested menu, every error screen, every empty state.

1.9 UNIVERSAL DOCUMENT SEARCH — search by ID across all tabs.
    Authorized users can type any document ID (LVE-, MEMO-, JD-, etc.)
    and the bot finds it in the correct tab automatically.
    Access control: users only see documents they have permission for.

1.10 UNIFIED REQUESTS MENU — one place for ALL request types.
     All requests (leave, memo, OT, missing punch, etc.) are accessed
     from ONE "📋 Requests" menu. Inside: Upcoming / Past / Archive / New Request.
     Each view is organized by Month → Type → List → Detail.
     Never scatter request types across separate menu items.

====================================================================
# 2. NOTIFICATION RULES
====================================================================

2.1 NO auto-popup notifications to approvers/managers.
    Managers check their Pending items from the menu when THEY are ready.
    Never interrupt them with unsolicited messages.

2.2 Notification Center — all notifications stored in a menu item.
    Users tap 🔔 Notifications to see what's new.
    Unread count shown in the menu: "🔔 Notifications (3)"

2.3 Employees ARE notified when:
    - Their request is approved or rejected
    - Someone submits something on their behalf
    - A task is assigned to them
    These are stored in Notifications AND sent as a Telegram message.

2.4 Notifications are logged — never lost.
    Every notification is saved to a log (Google Sheet / database).
    User can review past notifications anytime.

====================================================================
# 3. DATA & FORMS RULES
====================================================================

3.1 SINGLE SOURCE OF TRUTH — never duplicate data.
    One master record per entity. All other references use lookups/links.
    Example: Employee name lives in Employee_DB only. Every other tab
    uses VLOOKUP or code lookup — never copy-paste the name.

3.2 VLOOKUP columns — NEVER overwrite with bot code.
    If a Google Sheet column has a formula (VLOOKUP, SUM, IF, etc.),
    the bot writes "" (empty string) to that cell. The formula handles the rest.

3.3 DROPDOWN VALIDATION on all categorical fields.
    Status, Type, Priority, Role — all must have dropdown validation.
    Prevents typos and ensures data consistency.

3.4 DATES always DD/MM/YYYY — never MM/DD, never YYYY-MM-DD in user-facing content.

3.5 AUTO-GENERATE IDs — users never type IDs.
    Every record gets an auto-generated ID: PREFIX-YYYY-NNNN
    Bot scans existing records and increments. Users see the ID, never create it.

3.6 EMPLOYEE CODES are the universal key.
    Type the code → everything else (name, department, title) auto-fills.
    This applies everywhere: forms, logs, lookups, PDFs.

====================================================================
# 4. APPROVAL FLOW RULES
====================================================================

4.1 PULL-BASED approvals — approvers check when ready.
    The approval queue is in their menu. They open it, review, decide.
    No auto-notifications to approvers (see rule 2.1).

4.2 APPROVAL CHAIN is configurable per employee.
    Stored in a field (e.g., Approval_Chain = "MGR_HR" or "MGR_HR_DIR").
    Bot reads the chain and routes automatically.

4.3 EACH APPROVAL captures:
    - Who approved (employee code)
    - When (exact timestamp DD/MM/YYYY HH:MM)
    - Electronic signature (if enabled)
    - Status (Approved / Rejected)
    - Rejection reason (if rejected — mandatory)

4.4 EMPLOYEE NOTIFIED at each stage — approval or rejection.

4.5 PDF GENERATED on final approval — with all signatures and timestamps.

4.6 REJECTION always requires a reason — never allow blank rejection.

====================================================================
# 5. PDF & DOCUMENT RULES
====================================================================

5.1 COMPANY HEADER on every PDF.
    Logo centered + company name + address + email + website.
    Consistent across ALL document types.

5.2 ELECTRONIC SIGNATURES in all approved documents.
    Each approver's signature (image or text) embedded at their approval line.
    Timestamp below each signature.
    Verification code at the bottom: SIG-XXXXXXXX.

5.3 AUTO-SAVE to Google Drive — every generated PDF.
    Organized in folders by year/month/type.
    Link saved back to the log record.

5.4 BILINGUAL where required — Russian + English, or Arabic + English.
    Text content changes per language, but layout stays identical.
    Section headings in both languages on the same document.

5.5 USE UNICODE FONTS for non-Latin text.
    For Russian/Arabic: use DejaVu or similar Unicode TTF font in fpdf2.
    Never transliterate Cyrillic — render actual characters.

5.6 PDF DELIVERED via Telegram send_document — not send_photo.
    User receives a proper .pdf file they can save/print.

5.7 PDF PREVIEW via Google Drive link — not download.
    When showing a PDF to any user, upload to Drive first, then show a
    clickable URL button [📄 View PDF] that opens in the browser.
    InlineKeyboardButton("📄 View PDF", url=drive_url)
    This is faster and doesn't require downloading.
    Apply to ALL document types across the entire system.

5.8 EVERY approved PDF auto-uploads to organized Drive folders.
    Structure: /[Category]/[YEAR]/[MONTH]/filename.pdf
    Drive link saved back to the relevant log tab.
    Draft/preview PDFs go to /Drafts/ folder (temporary).

5.9 ZERO FILES IN CHAT — all PDFs via Google Drive link.
    NEVER use send_document() to send PDFs in Telegram chat.
    ALWAYS: generate PDF → upload to Drive → send URL button.
    [📄 View PDF] opens in browser via InlineKeyboardButton(url=...).
    This applies to ALL document types, ALL stages, ALL roles, ALL archives.
    Fallback to send_document ONLY if Drive upload completely fails.

5.10 PROGRESSIVE PDF DRIVE LINKS — universal rule for ALL multi-stage approval flows.
    At EVERY stage of any approval chain, generate a PDF and upload to Drive:
    - Submission:      PDF with submitter signature → upload → save link → submitter sees [📄 View Submitted PDF]
    - Each approval:   PDF with ALL signatures collected so far → upload → overwrite saved link → next approver sees [📄 View Current PDF]
    - Final approval:  Fully-signed PDF → upload → save link → sent to submitter + all approvers
    The Drive link stored in the sheet is ALWAYS the CURRENT (latest) version — overwritten at each stage.
    EVERY person who receives a request must see a [📄 View ...] URL button BEFORE they approve/reject.
    This applies to: Leave, Overtime, Early Departure, Missing Punch, Memos, Deductions, Bonuses,
                     and ALL future request types across ALL departments (Transport, Kitchen, Warehouse, Operations…).
    NEVER make any person approve or decide without first seeing the current PDF via a Drive URL button.

====================================================================
# 6. AI RULES
====================================================================

6.1 ALL AI features use Google Gemini — never Claude/Anthropic API.
    Claude is for development. Gemini is for production features.
    API key stored in gemini_key.txt (local) or GEMINI_KEY env var (production).

6.2 AI IMPROVEMENT is always optional — user chooses.
    Show: [✨ Improve with AI] [✍️ Edit manually] [✅ Keep as is]
    Never force AI on the user.

6.3 AI ITERATIONS are unlimited.
    User can keep asking AI to revise. Buttons:
    [✅ Use this] [🔄 Try again] [💬 Give instructions] [✍️ Edit manually] [↩️ Keep original]

6.4 USER CAN GIVE CUSTOM INSTRUCTIONS to AI.
    "Make it shorter" / "More formal" / "Add numbers" — user types what they want.
    AI applies the instruction and shows the result.

6.5 MANUAL EDIT always available after AI.
    After AI suggests, user can get the full text, edit one word, send back.
    Bot accepts the manually edited version.

6.6 AI OUTPUT is text only — no explanations, no preamble, no markdown.
    System prompt always ends with: "Output ONLY the improved text."

6.7 RETRY if AI returns identical text.
    If output == input, retry with stronger prompt:
    "Rewrite and significantly improve this text. Do NOT return the same text."

====================================================================
# 7. SECURITY RULES
====================================================================

7.1 PASSWORDS stored as bcrypt hashes — NEVER plain text.
    Salt rounds ≥ 12.

7.2 BOT TOKEN, API KEYS, CREDENTIALS — never in code files.
    Store in: environment variables (production) or .txt files (local).
    .gitignore must exclude all secrets.

7.3 ROLE-BASED ACCESS — users see only what their role permits.
    Every data query filtered by the user's role + department + manager chain.
    No cross-boundary access.

7.4 ACCOUNT LOCKING — 3 wrong password attempts = locked.
    HR must unlock manually. Logged in access log.

7.5 TERMINATED EMPLOYEES — access revoked immediately.
    Set Status=Terminated → next bot message = access denied.

7.6 ACCESS LOG — every login attempt (success or failure) recorded.
    Timestamp, Telegram ID, employee code, result.

7.7 UNREGISTERED TELEGRAM IDs — silently rejected and logged.
    No error message shown — just ignored.

====================================================================
# 8. TECHNICAL RULES
====================================================================

8.1 PYTHON 3.14 — use asyncio.run(main()) pattern.
    Standard app.run_polling() does NOT work on Python 3.14.

8.2 GOOGLE SHEETS rate limit: 60 reads/min.
    Batch reads where possible. Use caching for frequently accessed data.

8.3 GOOGLE DRIVE uploads via Apps Script middleman.
    Service accounts cannot upload to free Gmail Drive.
    Bot sends base64 PDF to Apps Script web app → Apps Script uploads.

8.4 COMPLETE FILES ONLY — never partial code.
    Every file must be complete and runnable. No "add your logic here" placeholders.

8.5 REQUIREMENTS.TXT always up to date.
    Every new library → added to requirements.txt immediately.

8.6 ERROR HANDLING — friendly messages + back button.
    User sees: "Something went wrong. Please try again or contact HR."
    Plus ↩️ Main Menu button. Never a raw Python error.

8.7 TYPING INDICATOR before slow operations.
    If response takes >2 seconds, show send_chat_action(TYPING) first.

====================================================================
# 9. UX WRITING RULES
====================================================================

9.1 MESSAGES are clear, short, professional.
    No emojis overload. Use 1-2 relevant emojis per message, not 10.

9.2 CONFIRMATIONS always include the record ID.
    "✅ Leave request submitted! ID: LVE-2026-0042"

9.3 DATE FORMAT consistent: DD/MM/YYYY everywhere.

9.4 SUMMARY before submission — always.
    Before user confirms any action, show a full summary of what they're submitting.
    [✅ Submit] [✍️ Edit] [❌ Cancel]

9.5 EMPTY STATES handled gracefully.
    "No pending requests. All clear! ✅" + ↩️ Main Menu
    Never show a blank screen or error.

9.6 LISTS show count in header.
    "📋 Pending Approvals (3)" — not just "Pending Approvals"

====================================================================
# 10. FILE & FOLDER ORGANIZATION
====================================================================

10.1 SEPARATE FILES per feature — never one giant file.
     Each module/feature gets its own .py file.
     Main bot file only imports and registers handlers.

10.2 CONFIG in one file — all settings, constants, connections.
     Other files import from config. Never hardcode settings.

10.3 DRIVE FOLDERS organized by: /[Category]/[YEAR]/[MONTH]/[filename]
     Every document type has its own folder structure.

10.4 PDF FILENAMES are descriptive.
     EmpCode-Type-RequestID-Date.pdf
     Example: 1011-leave_approval-LVE-2026-0042-21-03-2026.pdf

====================================================================
# 11. TESTING RULES
====================================================================

11.1 BUILD ONE feature → TEST → next feature.
     Never batch multiple features without testing in between.

11.2 AFTER EVERY CHANGE: tell user the exact command to run.
     "python3 bot.py" or whatever the run command is.

11.3 IF ERROR PASTED — fix immediately, no questions.

11.4 SOUND ALERT when task is done.
     After completing all changes, run as final terminal command:
     afplay /System/Library/Sounds/Hero.aiff
     This plays a sound so Mostafa knows the task is finished.

====================================================================
# 12. WORKING WITH MOSTAFA
====================================================================

12.1 COMPLETE BEGINNER — explain every non-obvious step.
12.2 Uses Mac with python3, pip3.
12.3 Uses VS Code with Claude Code.
12.4 ONE terminal command at a time.
12.5 COMPLETE files — never ask to manually edit code.
12.6 DEFAULT language: English.
12.7 When next step is running: write the exact command.

====================================================================
# HOW TO ADD NEW RULES
====================================================================
# Tell Claude (this chat): "New basic rule: [describe the rule]"
# It will be added here with the next number in the correct section.
# Example: "New basic rule: all tables in PDFs must have alternating row colors"
# → Added as 5.7 under PDF & Document Rules.
====================================================================
