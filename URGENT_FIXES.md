# URGENT FIXES — Do all now, non-stop

====================================================================
# FIX 1: Memo PDF Error
====================================================================

Error: "Not enough horizontal space to render a single character"

This is an fpdf2 error when a cell or multi_cell is too narrow for the font size.
The memo PDF generator (memo_handler.py or wherever the memo PDF is built) 
likely has a column/cell width that's 0 or too small.

Common causes:
- Using pdf.cell(0, ...) inside a table where margin leaves no space
- Font size too large for the available width
- DejaVu font characters wider than expected
- Page margins too large leaving no print area

FIX:
1. Find the memo PDF generation function
2. Check all cell() and multi_cell() calls — ensure width > 0
3. For multi_cell with long text, use: pdf.multi_cell(pdf.epw, 7, text)
   where pdf.epw = effective page width (accounts for margins)
4. Ensure margins are reasonable: pdf.set_margins(15, 15, 15)
5. For the bilingual layout, don't use side-by-side columns — use
   SEQUENTIAL layout: full Russian section, then separator, then full English
6. Test with the actual memo text "test" (short) to make sure it works

The existing leave PDF (pdf_generator.py) works fine — use the same 
pattern for margins and cell widths.

====================================================================
# FIX 2: PDF Preview at Every Stage
====================================================================

Add "👁 Preview PDF" button at EVERY stage of the memo flow:

## For Submitter (before sending to HR):
After writing text and before final submit, show:
[👁 Preview PDF] [✅ Submit to HR] [✍️ Edit] [❌ Cancel]

When "Preview PDF" tapped:
- Generate the PDF in memory (same as final, but without signatures/registration)
- Send as Telegram document (send_document)
- Show same buttons again (user can preview multiple times)
- DO NOT save to Drive at this stage

## For HR Staff (reviewing):
When viewing a memo to review:
[👁 View PDF] [✅ Register & Forward] [📝 Request Changes] [❌ Reject]

PDF shows: submitter's text + submitter's signature (if they signed)

## For HR Manager:
[👁 View PDF] [✅ Approve & Forward] [📝 Send Back] [❌ Reject]

PDF shows: text + submitter signature + HR registration number + HR signature

## For Director:
[👁 View PDF] [✅ Approve & Sign] [❌ Reject]

PDF shows: text + all previous signatures + "PENDING DIRECTOR DECISION"

## After Director Approves:
- Final PDF generated with ALL signatures
- Auto-uploaded to Drive
- Drive link saved to Memo_Log column "Drive_Link" (col 24)
- PDF sent to: submitter + HR_Manager + Director
- Everyone can download from their archive view

====================================================================
# FIX 3: Back Button Goes to PREVIOUS Menu, Not Main Menu
====================================================================

CRITICAL RULE (add to all handlers):

When a user taps an option and it doesn't work (error, empty, not available):
→ The ↩️ Back button must go to the MENU THEY WERE IN BEFORE
→ NOT to Main Menu

Example:
User is in: Memo Archive → March 2026 → By Submitter → taps a submitter
If that submitter has no memos: "No memos found"
↩️ Back → goes to "By Submitter" list (NOT main menu)
↩️ Main Menu → goes to main menu (always available as second option)

This means EVERY error screen, empty state, and "not available" message must have:
[↩️ Back (to previous screen)] + [↩️ Main Menu]

The "Back" callback_data must point to the PARENT menu's callback, not "back_to_menu".

CHECK ALL HANDLERS:
Go through every handler file and verify that error/empty screens have 
a ↩️ Back button pointing to the correct parent menu. Fix any that 
go directly to main menu when they should go to the parent.

This is especially important in nested menus:
- Memo Archive → Month → View Type → List → Detail
- Recruitment → Candidates → Candidate Detail
- Leave → My Requests → Request Detail
- Attendance → Department → Employee → Month
- Any nested flow

====================================================================
# After all 3 fixes: "All fixed — ready to test" → STOP
====================================================================
