"""
ROIN WORLD FZE — Leave System v9
==================================
My Requests: Previous / Upcoming → list → open detail → PDF / close
Team Requests: same structure
"""

from datetime import datetime, timedelta
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from config import get_sheet
from pdf_generator import generate_leave_pdf

LEAVE_TYPE=100; LEAVE_START=101; LEAVE_END=102; LEAVE_REASON=103
LEAVE_SICK_PHOTO=104; LEAVE_CONFIRM=105
TEAM_SELECT_EMP=110; TEAM_LEAVE_TYPE=111; TEAM_START=112
TEAM_END=113; TEAM_REASON=114; TEAM_SICK_PHOTO=115; TEAM_CONFIRM=116
# Early Departure states
ED_DATE=120; ED_TIME=121; ED_REASON_ST=122; ED_CONFIRM_ST=123
# Overtime states
OT_DATE=130; OT_HOURS_ST=131; OT_REASON_ST=132; OT_CONFIRM_ST=133

DEDUCTED_TYPES = {"Paid", "Emergency"}
ROLE_LABELS_MAP = {"manager": "Direct Manager", "hr": "HR Manager", "director": "Director"}
TYPE_EMOJI = {
    "Paid": "🏖", "Sick": "🤒", "Emergency": "🚨", "Unpaid": "📋",
    "Business_Trip": "🚗", "Early_Departure": "🚪",
    "Overtime_Planned": "⏰", "Overtime_Emergency": "🚨",
    "Missing_Punch": "🖐",
}
STAGE_COLUMNS = {0: (10, 11), 1: (12, 13), 2: (14, 15)}

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def blt(): return InlineKeyboardButton("↩️ Back", callback_data="back_to_leave_type")

# ── Helpers ──
def get_official_holidays():
    try:
        h = set()
        for r in get_sheet("Holidays").get_all_records():
            ds = str(r.get("Date", "")).strip()
            if ds:
                try: h.add(datetime.strptime(ds, "%d/%m/%Y").date())
                except: pass
        return h
    except: return set()

def is_second_saturday(d):
    if d.weekday() != 5: return False
    f = d.replace(day=1); fs = f + timedelta(days=(5 - f.weekday()) % 7)
    return d == fs + timedelta(days=7)

def calculate_leave_days(sd, ed, h2, hol):
    if sd > ed: return 0, []
    wd=0; sk=[]; c=sd
    while c <= ed:
        sr=None
        if c.weekday()==4: sr="Friday"
        elif h2 and is_second_saturday(c): sr="2nd Saturday"
        elif c in hol: sr="Official Holiday"
        if sr: sk.append((c,sr))
        else: wd+=1
        c+=timedelta(days=1)
    return wd, sk

def get_total_balance(ec):
    for r in get_sheet("Leave_Balance").get_all_records():
        if str(r.get("Emp_Code",""))==str(ec):
            try: return int(r.get("Total_Balance_Remaining",0))
            except: return 0
    return None

def employee_has_second_saturday(ec):
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code",""))==str(ec):
            return str(r.get("Saturday_Type","")).strip()!="No_2nd_Saturday"
    return True

def find_emp_code_by_tid(tid):
    for i,r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i==0: continue
        if r[1].strip()==str(tid): return r[0].strip()
    return None

def get_user_role(tid):
    for i,r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i==0: continue
        if r[1].strip()==str(tid): return r[3].strip() if len(r)>3 else "Employee"
    return "Employee"

def get_employee_name(ec):
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code",""))==str(ec):
            return r.get("Full_Name",ec), r.get("Department","?")
    return ec, "?"

def gen_rid():
    ids=get_sheet("Leave_Log").col_values(1); yr=datetime.now().strftime("%Y")
    px=f"LVE-{yr}-"; mx=0
    for r in ids:
        if str(r).startswith(px):
            try: n=int(str(r).split("-")[-1]); mx=max(mx,n)
            except: pass
    return f"{px}{mx+1:04d}"

def get_chain(ec,lt):
    from approval_handler import get_approval_chain
    return get_approval_chain(ec,lt)

def gen_prefixed_id(prefix):
    """Generate MP-YYYY-NNNN, ED-YYYY-NNNN, OT-YYYY-NNNN style IDs."""
    ids = get_sheet("Leave_Log").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"{prefix}-{yr}-"
    mx  = 0
    for r in ids:
        if str(r).startswith(px):
            try: n = int(str(r).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"

def count_ed_this_month(ec):
    """Count approved Early_Departure requests for ec in current month."""
    rows = get_sheet("Leave_Log").get_all_values()
    now  = datetime.now()
    count = 0
    for i, r in enumerate(rows):
        if i == 0: continue
        if r[1].strip() != str(ec): continue
        if r[2].strip() != "Early_Departure": continue
        if len(r) > 15 and r[15].strip() != "Approved": continue
        try:
            rd = datetime.strptime(r[3].strip(), "%d/%m/%Y").date()
            if rd.year == now.year and rd.month == now.month: count += 1
        except: pass
    return count

def get_shift_end(ec):
    """Return shift end time (HH:MM) based on Shift_Hours in Employee_DB."""
    from config import OFFICIAL_START_TIME, OFFICIAL_END_TIME
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code","")) == str(ec):
            try:
                sh    = float(r.get("Shift_Hours", 9))
                start = datetime.strptime(OFFICIAL_START_TIME, "%H:%M")
                end   = start + timedelta(hours=sh)
                return end.strftime("%H:%M")
            except: pass
    from config import OFFICIAL_END_TIME
    return OFFICIAL_END_TIME

def get_ot_hours_this_month(ec):
    """Total pending/approved OT hours for ec in the current month."""
    rows  = get_sheet("Leave_Log").get_all_values()
    now   = datetime.now()
    total = 0.0
    for i, r in enumerate(rows):
        if i == 0: continue
        if r[1].strip() != str(ec): continue
        if r[2].strip() not in ("Overtime_Planned","Overtime_Emergency"): continue
        if len(r) > 15 and r[15].strip() == "Rejected": continue
        try:
            rd = datetime.strptime(r[3].strip(), "%d/%m/%Y").date()
            if rd.year == now.year and rd.month == now.month:
                h = float(r[6]) if len(r) > 6 and r[6] else 0
                total += h
        except: pass
    return total

def write_req(data):
    ws=get_sheet("Leave_Log"); rid=gen_rid(); now=datetime.now().strftime("%d/%m/%Y %H:%M")
    chain=get_chain(data["emp_code"],data["leave_type"])
    ss=["NA","NA","NA"]
    for i in range(len(chain)): ss[i]="Pending"
    row=[rid,str(data["emp_code"]),data["leave_type"],data["start_date"],data["end_date"],
         data["working_days"],"","",data["reason"],ss[0],"",ss[1],"",ss[2],"",
         "Pending","","","","No","",now]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return rid, now

def write_ed_req(data):
    """Write Early Departure request. Chain is always Manager → HR only."""
    ws  = get_sheet("Leave_Log")
    rid = gen_prefixed_id("ED")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    # ED: always MGR_HR regardless of employee's chain
    ss  = ["Pending", "Pending", "NA"]
    row = [rid, str(data["emp_code"]), "Early_Departure",
           data["date"], data["date"], "1",
           str(data["hours_early"]), data["leave_time"], data["reason"],
           ss[0], "", ss[1], "", ss[2], "",
           "Pending", "", "", "", "No", "", now]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return rid, now

def write_ot_req(data):
    """Write Overtime request. Chain: Manager → HR; add Director if monthly > 40hrs."""
    from config import OT_RATE_DEFAULT
    ws    = get_sheet("Leave_Log")
    rid   = gen_prefixed_id("OT")
    now   = datetime.now().strftime("%d/%m/%Y %H:%M")
    chain = data.get("chain", ["manager","hr"])
    ss    = ["NA","NA","NA"]
    for i in range(len(chain)): ss[i] = "Pending"
    hours = data["hours"]
    rate  = OT_RATE_DEFAULT
    equiv = round(hours * rate, 2)
    row = [rid, str(data["emp_code"]), data["ot_type"],
           data["date"], data["date"], "1",
           str(hours), "", data["reason"],
           ss[0], "", ss[1], "", ss[2], "",
           "Pending", "", str(rate), str(equiv), "No", "", now]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return rid, now

def _menu(role):
    from bot import build_inline_menu
    return build_inline_menu(role)

def get_my_team(my_code, my_role):
    codes=[]
    for r in get_sheet("Employee_DB").get_all_records():
        if my_role=="Supervisor" and str(r.get("Supervisor_Code","")).strip()==str(my_code):
            codes.append(str(r.get("Emp_Code","")))
        elif my_role in ("Direct_Manager","HR_Manager") and str(r.get("Manager_Code","")).strip()==str(my_code):
            codes.append(str(r.get("Emp_Code","")))
    return codes

def _parse_date(ds):
    """Try to parse DD/MM/YYYY date string."""
    try: return datetime.strptime(ds.strip(), "%d/%m/%Y").date()
    except: return None

def build_status(rd, chain):
    lines=[]
    for i,role in enumerate(chain):
        sc=STAGE_COLUMNS[i][0]-1; dc=STAGE_COLUMNS[i][1]-1
        lb=ROLE_LABELS_MAP.get(role,role)
        if sc<len(rd):
            s=rd[sc].strip(); d=rd[dc].strip() if dc<len(rd) else ""
            if s=="Approved": lines.append(f"  ✅ {lb} ({d})")
            elif s=="Rejected": lines.append(f"  ❌ {lb} ({d})")
            elif s=="Pending": lines.append(f"  ⏳ {lb}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
#  REQUEST LEAVE — SELF (unchanged logic, back buttons)
# ══════════════════════════════════════════════════════════════════
def _leave_type_kb(prefix="ltype"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏖 Paid",       callback_data=f"{prefix}_Paid"),
         InlineKeyboardButton("🤒 Sick",       callback_data=f"{prefix}_Sick")],
        [InlineKeyboardButton("🚨 Emergency",  callback_data=f"{prefix}_Emergency"),
         InlineKeyboardButton("📋 Unpaid",     callback_data=f"{prefix}_Unpaid")],
        [InlineKeyboardButton("🚗 Business Trip", callback_data=f"{prefix}_Business_Trip")],
        [InlineKeyboardButton("🚪 Early Departure", callback_data=f"{prefix}_Early_Departure")],
        [InlineKeyboardButton("⏰ Planned OT",  callback_data=f"{prefix}_Overtime_Planned"),
         InlineKeyboardButton("🚨 Emergency OT",callback_data=f"{prefix}_Overtime_Emergency")],
        [bm()],
    ])

async def leave_start(u,c):
    q=u.callback_query; await q.answer(); c.user_data["requesting_for"]="self"
    await q.edit_message_text("📝 *Request Leave*\n\nSelect type:", parse_mode="Markdown",
        reply_markup=_leave_type_kb("ltype")); return LEAVE_TYPE

async def leave_type_sel(u,c):
    q=u.callback_query; await q.answer()
    if q.data=="back_to_menu":
        await q.edit_message_text("Choose:",reply_markup=_menu(get_user_role(str(q.from_user.id))))
        return ConversationHandler.END
    lt=q.data.replace("ltype_",""); c.user_data["leave_type"]=lt; c.user_data["sick_photos"]=[]
    bk=InlineKeyboardMarkup([[blt(),bm()]])
    if lt=="Early_Departure":
        ec=find_emp_code_by_tid(str(q.from_user.id))
        if ec:
            ed_cnt=count_ed_this_month(ec)
            if ed_cnt>=2:
                await q.edit_message_text(
                    "🚪 Early Departure\n\n❌ Maximum 2 early departures per month reached.\n"
                    f"You have already used {ed_cnt} this month.",
                    reply_markup=InlineKeyboardMarkup([[blt(),bm()]])); return LEAVE_TYPE
            c.user_data["ed_count_used"]=ed_cnt
        await q.edit_message_text(
            "🚪 *Early Departure*\n\nEnter the departure date (`DD/MM/YYYY`):\n"
            "(Today or future dates only)",
            parse_mode="Markdown",reply_markup=bk); return ED_DATE
    elif lt in ("Overtime_Planned","Overtime_Emergency"):
        label="tomorrow or later (24-hr advance)" if lt=="Overtime_Planned" else "today or yesterday"
        await q.edit_message_text(
            f"{'⏰' if lt=='Overtime_Planned' else '🚨'} *{'Planned' if 'Planned' in lt else 'Emergency'} Overtime*\n\n"
            f"Enter date (`DD/MM/YYYY`) — {label}:",
            parse_mode="Markdown",reply_markup=bk); return OT_DATE
    await q.edit_message_text(f"{TYPE_EMOJI.get(lt,'📋')} *{lt} Leave*\n\nStart date: `DD/MM/YYYY`",
        parse_mode="Markdown",reply_markup=bk); return LEAVE_START

async def back_lt(u,c):
    q=u.callback_query; await q.answer()
    await q.edit_message_text("📝 *Request Leave*\n\nSelect type:", parse_mode="Markdown",
        reply_markup=_leave_type_kb("ltype")); return LEAVE_TYPE

async def back_menu_conv(u,c):
    q=u.callback_query; await q.answer()
    await q.edit_message_text("Choose:",reply_markup=_menu(get_user_role(str(q.from_user.id))))
    return ConversationHandler.END

async def l_start(u,c):
    t=u.message.text.strip(); bk=InlineKeyboardMarkup([[blt(),bm()]])
    try: sd=datetime.strptime(t,"%d/%m/%Y").date()
    except: await u.message.reply_text("⚠️ `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk); return LEAVE_START
    lt=c.user_data.get("leave_type","")
    min_date=datetime.now().date()-timedelta(days=2) if lt=="Business_Trip" else datetime.now().date()
    if sd<min_date:
        msg="⚠️ Past. Business trips can be submitted up to 2 days after." if lt=="Business_Trip" else "⚠️ Past."
        await u.message.reply_text(msg,reply_markup=bk); return LEAVE_START
    c.user_data["start_date"]=sd; c.user_data["start_date_str"]=t
    await u.message.reply_text(f"✅ {t}\n\nEnd date: `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk); return LEAVE_END

async def l_end(u,c):
    t=u.message.text.strip(); bk=InlineKeyboardMarkup([[blt(),bm()]])
    try: ed=datetime.strptime(t,"%d/%m/%Y").date()
    except: await u.message.reply_text("⚠️ `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk); return LEAVE_END
    sd=c.user_data["start_date"]
    if ed<sd: await u.message.reply_text(f"⚠️ Before {sd.strftime('%d/%m/%Y')}.",reply_markup=bk); return LEAVE_END
    if (ed-sd).days+1>60: await u.message.reply_text("⚠️ Max 60.",reply_markup=bk); return LEAVE_END
    c.user_data["end_date"]=ed; c.user_data["end_date_str"]=t
    await u.message.reply_text(f"✅ {t}\n\nReason:",reply_markup=bk); return LEAVE_REASON

async def l_reason(u,c):
    r=u.message.text.strip(); bk=InlineKeyboardMarkup([[blt(),bm()]])
    if len(r)<3: await u.message.reply_text("⚠️ Short.",reply_markup=bk); return LEAVE_REASON
    c.user_data["reason"]=r
    if c.user_data["leave_type"]=="Sick":
        await u.message.reply_text("🏥 Send sick note photo(s).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done",callback_data="sick_done")],[blt(),bm()]]))
        return LEAVE_SICK_PHOTO
    return await _summary(u,c)

async def l_photo(u,c):
    if u.message.photo:
        if "sick_photos" not in c.user_data: c.user_data["sick_photos"]=[]
        c.user_data["sick_photos"].append(u.message.photo[-1].file_id)
        await u.message.reply_text(f"📷 {len(c.user_data['sick_photos'])} received.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done",callback_data="sick_done")],[blt(),bm()]]))
    return LEAVE_SICK_PHOTO

async def l_sick_done(u,c):
    q=u.callback_query; await q.answer()
    if not c.user_data.get("sick_photos"):
        await q.edit_message_text("⚠️ Upload at least one.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done",callback_data="sick_done")],[blt(),bm()]]))
        return LEAVE_SICK_PHOTO
    await q.edit_message_text(f"✅ {len(c.user_data['sick_photos'])} photo(s)."); return await _summary(u,c,True)

async def _summary(u,c,cb=False):
    cid=u.effective_chat.id; tm=await c.bot.send_message(chat_id=cid,text="⏳")
    try:
        ec=c.user_data.get("target_emp_code") if c.user_data.get("requesting_for")=="employee" else find_emp_code_by_tid(str(u.effective_user.id))
        if not ec: await tm.edit_text("❌",reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
        c.user_data["emp_code"]=ec; sd=c.user_data["start_date"]; ed=c.user_data["end_date"]; lt=c.user_data["leave_type"]
        wd,sk=calculate_leave_days(sd,ed,employee_has_second_saturday(ec),get_official_holidays())
        if wd==0: await tm.edit_text("ℹ️ All off days.",reply_markup=InlineKeyboardMarkup([[blt(),bm()]])); return LEAVE_TYPE
        c.user_data["working_days"]=wd; bt=""
        if lt in DEDUCTED_TYPES:
            bal=get_total_balance(ec)
            if bal is None: await tm.edit_text("❌ Balance?",reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
            if wd>bal: await tm.edit_text(f"❌ {wd} vs {bal}.",reply_markup=InlineKeyboardMarkup([[blt(),bm()]])); return LEAVE_TYPE
            bt=f"Balance after: {bal-wd}\n"
        elif lt=="Sick": bt="ℹ️ Not deducted\n"
        elif lt=="Unpaid": bt="ℹ️ Salary deducted\n"
        elif lt=="Business_Trip": bt="ℹ️ Business trip — not deducted\n"
        await tm.delete(); tc=(ed-sd).days+1; reason=c.user_data["reason"]
        skt=""
        if sk: skt=f"\nExcluded ({len(sk)}):\n"+"\n".join([f"  - {d.strftime('%d/%m/%Y')} ({d.strftime('%A')}) = {r}" for d,r in sk])+"\n"
        pt=f"📷 {len(c.user_data.get('sick_photos',[]))} photo(s)\n" if lt=="Sick" else ""
        chain=get_chain(ec,lt); ct=" → ".join([ROLE_LABELS_MAP.get(r,r) for r in chain])
        nm,_=get_employee_name(ec)
        rb=f"By: {get_user_role(str(u.effective_user.id))}\n" if c.user_data.get("requesting_for")=="employee" else ""
        s=(f"📝 Summary\n{'─'*28}\n{nm} ({ec})\n{rb}{lt} Leave\n{c.user_data['start_date_str']} to {c.user_data['end_date_str']}\n"
           f"{tc} cal / {wd} work\n{bt}{pt}{skt}Reason: {reason}\nChain: {ct}\n{'─'*28}\n\nConfirm?")
        kb=[[InlineKeyboardButton("✅ Submit",callback_data="leave_confirm_yes"),
             InlineKeyboardButton("❌ Cancel",callback_data="leave_confirm_no")],[blt(),bm()]]
        await c.bot.send_message(chat_id=cid,text=s,reply_markup=InlineKeyboardMarkup(kb)); return LEAVE_CONFIRM
    except Exception as e:
        await tm.edit_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END

async def l_confirmed(u,c):
    q=u.callback_query; await q.answer()
    if q.data=="leave_confirm_no":
        await q.edit_message_text("Choose:",reply_markup=_menu(get_user_role(str(q.from_user.id)))); return ConversationHandler.END
    try:
        d={"emp_code":c.user_data["emp_code"],"leave_type":c.user_data["leave_type"],
           "start_date":c.user_data["start_date_str"],"end_date":c.user_data["end_date_str"],
           "working_days":c.user_data["working_days"],"reason":c.user_data["reason"]}
        rid,sub=write_req(d); sp=c.user_data.get("sick_photos",[])
        if sp: c.bot_data[f"sick_photos_{rid}"]=sp
        if c.user_data.get("requesting_for")=="employee":
            try:
                for i,r in enumerate(get_sheet("User_Registry").get_all_values()):
                    if i==0: continue
                    if r[0].strip()==str(d["emp_code"]) and r[1].strip():
                        await c.bot.send_message(chat_id=r[1].strip(),
                            text=f"ℹ️ Leave request submitted for you.\nID: {rid}\n{d['leave_type']} {d['start_date']} to {d['end_date']}"); break
            except: pass
        # Rule 5.10 — generate submitted PDF, upload, save to col 21
        sub_url = None
        try:
            from approval_handler import _generate_and_save_stage_pdf, find_leave_request, get_approval_chain
            rn2, rd2 = find_leave_request(rid)
            if rn2 and rd2:
                chain2 = get_approval_chain(d["emp_code"], d["leave_type"])
                sub_url = await _generate_and_save_stage_pdf(c, rn2, rd2, rid, d["emp_code"], d["leave_type"], chain2, sub)
        except Exception: pass
        conf_kb = [[InlineKeyboardButton("↩️ Leave Menu",callback_data="menu_leave"),bm()]]
        if sub_url:
            conf_kb.insert(0, [InlineKeyboardButton("📄 View Submitted PDF", url=sub_url)])
        await q.edit_message_text(f"✅ Submitted!\nID: {rid}\nTime: {sub}",
            reply_markup=InlineKeyboardMarkup(conf_kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="menu_leave"),bm()]]))
    return ConversationHandler.END

async def l_cancel(u,c):
    await u.message.reply_text("❌ Cancelled.\n\nSend /start."); return ConversationHandler.END

# ══════════════════════════════════════════════════════════════════
#  EARLY DEPARTURE FLOW
# ══════════════════════════════════════════════════════════════════

async def ed_date_inp(u,c):
    t=u.message.text.strip(); bk=InlineKeyboardMarkup([[blt(),bm()]])
    try: sd=datetime.strptime(t,"%d/%m/%Y").date()
    except:
        await u.message.reply_text("⚠️ Format: `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk)
        return ED_DATE
    if sd<datetime.now().date():
        await u.message.reply_text("⚠️ Date cannot be in the past.",reply_markup=bk); return ED_DATE
    c.user_data["ed_date"]=t
    ec=c.user_data.get("target_emp_code") if c.user_data.get("requesting_for")=="employee" \
        else find_emp_code_by_tid(str(u.effective_user.id))
    if ec: c.user_data["emp_code"]=ec
    shift_end=get_shift_end(ec) if ec else "17:00"
    await u.message.reply_text(
        f"✅ Date: {t}\n\n🕐 Enter the time you will leave (`HH:MM`):\n"
        f"(Your shift ends at {shift_end})",
        parse_mode="Markdown",reply_markup=bk); return ED_TIME

async def ed_time_inp(u,c):
    t=u.message.text.strip(); bk=InlineKeyboardMarkup([[blt(),bm()]])
    try:
        lt_obj=datetime.strptime(t,"%H:%M")
    except:
        await u.message.reply_text("⚠️ Format: `HH:MM` (e.g. 14:30)",parse_mode="Markdown",reply_markup=bk)
        return ED_TIME
    ec=c.user_data.get("emp_code") or find_emp_code_by_tid(str(u.effective_user.id))
    shift_end_str=get_shift_end(ec) if ec else "17:00"
    try:
        end_obj=datetime.strptime(shift_end_str,"%H:%M")
        diff=(end_obj-lt_obj).total_seconds()/3600
        if diff<=0:
            await u.message.reply_text(
                f"⚠️ Leave time must be before shift end ({shift_end_str}).",reply_markup=bk)
            return ED_TIME
        hours_early=round(diff,2)
    except:
        hours_early=1.0
    c.user_data["ed_leave_time"]=t; c.user_data["ed_hours_early"]=hours_early
    kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎉 Pre-holiday",callback_data="ed_rsn_Pre-holiday"),
         InlineKeyboardButton("👤 Personal",   callback_data="ed_rsn_Personal")],
        [InlineKeyboardButton("🏥 Medical",    callback_data="ed_rsn_Medical"),
         InlineKeyboardButton("📝 Other",      callback_data="ed_rsn_Other")],
        [blt(),bm()],
    ])
    await u.message.reply_text(
        f"✅ Leaving at: {t} ({hours_early:.1f} hrs early)\n\nSelect reason:",
        reply_markup=kb); return ED_REASON_ST

async def ed_reason_pick(u,c):
    q=u.callback_query; await q.answer()
    reason=q.data.replace("ed_rsn_",""); c.user_data["ed_reason"]=reason
    ec=c.user_data.get("emp_code") or find_emp_code_by_tid(str(q.from_user.id))
    nm,_=get_employee_name(ec) if ec else ("?","?")
    ed_date=c.user_data["ed_date"]; leave_time=c.user_data["ed_leave_time"]
    hours_early=c.user_data["ed_hours_early"]
    used=c.user_data.get("ed_count_used",count_ed_this_month(ec) if ec else 0)
    remaining=2-used-1  # -1 for this request
    chain_display=" → ".join(ROLE_LABELS_MAP.get(r,"?") for r in ["manager","hr"])
    msg=(f"🚪 Early Departure — Summary\n{'─'*28}\n"
         f"👤 {nm} ({ec})\n"
         f"Date:       {ed_date}\n"
         f"Leaving at: {leave_time}\n"
         f"Hours early:{hours_early:.1f}\n"
         f"Reason:     {reason}\n"
         f"Monthly ED remaining after this: {remaining}/2\n"
         f"Chain: {chain_display}\n"
         f"{'─'*28}\n\nConfirm submission?")
    kb=[[InlineKeyboardButton("✅ Submit",callback_data="leave_confirm_yes"),
         InlineKeyboardButton("❌ Cancel",callback_data="leave_confirm_no")],
        [blt(),bm()]]
    await q.edit_message_text(msg,reply_markup=InlineKeyboardMarkup(kb)); return ED_CONFIRM_ST

async def ed_confirm(u,c):
    q=u.callback_query; await q.answer()
    if q.data=="leave_confirm_no":
        await q.edit_message_text("Choose:",reply_markup=_menu(get_user_role(str(q.from_user.id))))
        return ConversationHandler.END
    ec=c.user_data.get("emp_code") or find_emp_code_by_tid(str(q.from_user.id))
    try:
        data={"emp_code":ec,"date":c.user_data["ed_date"],
              "leave_time":c.user_data["ed_leave_time"],
              "hours_early":c.user_data["ed_hours_early"],
              "reason":c.user_data["ed_reason"]}
        rid,sub=write_ed_req(data)
        # Rule 5.10 — generate submitted PDF, upload, save to col 21
        sub_url = None
        try:
            from approval_handler import _generate_and_save_stage_pdf, find_leave_request, get_approval_chain
            rn2, rd2 = find_leave_request(rid)
            if rn2 and rd2:
                chain2 = get_approval_chain(ec, "Early_Departure")
                sub_url = await _generate_and_save_stage_pdf(c, rn2, rd2, rid, ec, "Early_Departure", chain2, sub)
        except Exception: pass
        conf_kb = [[InlineKeyboardButton("↩️ Leave Menu",callback_data="menu_leave"),bm()]]
        if sub_url:
            conf_kb.insert(0, [InlineKeyboardButton("📄 View Submitted PDF", url=sub_url)])
        await q.edit_message_text(
            f"✅ Early Departure submitted!\nID: {rid}\nDate: {data['date']}\n"
            f"Leaving at: {data['leave_time']}\nSubmitted: {sub}",
            reply_markup=InlineKeyboardMarkup(conf_kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[blt(),bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════
#  OVERTIME FLOW
# ══════════════════════════════════════════════════════════════════

async def ot_date_inp(u,c):
    t=u.message.text.strip(); bk=InlineKeyboardMarkup([[blt(),bm()]])
    try: sd=datetime.strptime(t,"%d/%m/%Y").date()
    except:
        await u.message.reply_text("⚠️ Format: `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk)
        return OT_DATE
    lt=c.user_data.get("leave_type","")
    today=datetime.now().date()
    if lt=="Overtime_Planned":
        if sd<=today:
            await u.message.reply_text("⚠️ Planned OT must be submitted at least 24 hrs in advance.",reply_markup=bk)
            return OT_DATE
    elif lt=="Overtime_Emergency":
        if sd<today-timedelta(days=1):
            await u.message.reply_text("⚠️ Emergency OT can only be submitted for today or yesterday.",reply_markup=bk)
            return OT_DATE
    c.user_data["ot_date"]=t
    kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("1 hr",callback_data="ot_hrs_1"),
         InlineKeyboardButton("2 hrs",callback_data="ot_hrs_2"),
         InlineKeyboardButton("3 hrs",callback_data="ot_hrs_3"),
         InlineKeyboardButton("4 hrs",callback_data="ot_hrs_4")],
        [blt(),bm()],
    ])
    await u.message.reply_text(f"✅ Date: {t}\n\nSelect OT hours (max 4 per day):",
        reply_markup=kb); return OT_HOURS_ST

async def ot_hours_sel(u,c):
    q=u.callback_query; await q.answer()
    hrs=int(q.data.replace("ot_hrs_",""))
    ec=c.user_data.get("target_emp_code") if c.user_data.get("requesting_for")=="employee" \
        else find_emp_code_by_tid(str(q.from_user.id))
    if ec: c.user_data["emp_code"]=ec
    # Check limits
    month_total=get_ot_hours_this_month(ec) if ec else 0.0
    from config import MAX_OT_HOURS_PER_DAY,MAX_OT_HOURS_PER_MONTH
    bk=InlineKeyboardMarkup([[blt(),bm()]])
    if hrs>MAX_OT_HOURS_PER_DAY:
        await q.edit_message_text(f"❌ Max {MAX_OT_HOURS_PER_DAY} OT hours per day.",reply_markup=bk)
        return OT_HOURS_ST
    if month_total+hrs>MAX_OT_HOURS_PER_MONTH:
        c.user_data["ot_add_director"]=True  # Will add Director to chain
    else:
        c.user_data["ot_add_director"]=False
    c.user_data["ot_hours"]=hrs
    await q.edit_message_text(
        f"✅ OT Hours: {hrs}\n\nMonth total so far: {month_total:.0f} hrs\n\nType reason for overtime:",
        reply_markup=bk); return OT_REASON_ST

async def ot_reason_inp(u,c):
    r=u.message.text.strip(); bk=InlineKeyboardMarkup([[blt(),bm()]])
    if len(r)<3:
        await u.message.reply_text("⚠️ Too short.",reply_markup=bk); return OT_REASON_ST
    c.user_data["ot_reason"]=r
    ec=c.user_data.get("emp_code") or find_emp_code_by_tid(str(u.effective_user.id))
    nm,_=get_employee_name(ec) if ec else ("?","?")
    ot_date=c.user_data["ot_date"]; hrs=c.user_data["ot_hours"]
    lt=c.user_data.get("leave_type",""); add_dir=c.user_data.get("ot_add_director",False)
    from config import OT_RATE_DEFAULT
    equiv=round(hrs*OT_RATE_DEFAULT,2)
    chain=["manager","hr","director"] if add_dir else ["manager","hr"]
    chain_display=" → ".join(ROLE_LABELS_MAP.get(s,"?") for s in chain)
    dir_note="\n⚠️ Director approval required (monthly limit exceeded)." if add_dir else ""
    month_total=get_ot_hours_this_month(ec) if ec else 0.0
    msg=(f"{'⏰' if 'Planned' in lt else '🚨'} {'Planned' if 'Planned' in lt else 'Emergency'} OT — Summary\n"
         f"{'─'*28}\n"
         f"👤 {nm} ({ec})\n"
         f"Date:      {ot_date}\n"
         f"OT Hours:  {hrs}\n"
         f"Rate:      {OT_RATE_DEFAULT}x\n"
         f"Equivalent:{equiv} hrs\n"
         f"Month total (incl. this): {month_total+hrs:.0f}/40 hrs\n"
         f"Reason:    {r}\n"
         f"Chain:     {chain_display}{dir_note}\n"
         f"{'─'*28}\n\nConfirm submission?")
    c.user_data["ot_chain"]=chain
    kb=[[InlineKeyboardButton("✅ Submit",callback_data="leave_confirm_yes"),
         InlineKeyboardButton("❌ Cancel",callback_data="leave_confirm_no")],
        [blt(),bm()]]
    await u.message.reply_text(msg,reply_markup=InlineKeyboardMarkup(kb)); return OT_CONFIRM_ST

async def ot_confirm(u,c):
    q=u.callback_query; await q.answer()
    if q.data=="leave_confirm_no":
        await q.edit_message_text("Choose:",reply_markup=_menu(get_user_role(str(q.from_user.id))))
        return ConversationHandler.END
    ec=c.user_data.get("emp_code") or find_emp_code_by_tid(str(q.from_user.id))
    try:
        data={"emp_code":ec,"ot_type":c.user_data.get("leave_type","Overtime_Planned"),
              "date":c.user_data["ot_date"],"hours":c.user_data["ot_hours"],
              "reason":c.user_data["ot_reason"],"chain":c.user_data.get("ot_chain",["manager","hr"])}
        rid,sub=write_ot_req(data)
        lt=data["ot_type"]; hrs=data["hours"]
        from config import OT_RATE_DEFAULT
        # Rule 5.10 — generate submitted PDF, upload, save to col 21
        sub_url = None
        try:
            from approval_handler import _generate_and_save_stage_pdf, find_leave_request, get_approval_chain
            rn2, rd2 = find_leave_request(rid)
            if rn2 and rd2:
                chain2 = get_approval_chain(ec, lt)
                sub_url = await _generate_and_save_stage_pdf(c, rn2, rd2, rid, ec, lt, chain2, sub)
        except Exception: pass
        conf_kb = [[InlineKeyboardButton("↩️ Leave Menu",callback_data="menu_leave"),bm()]]
        if sub_url:
            conf_kb.insert(0, [InlineKeyboardButton("📄 View Submitted PDF", url=sub_url)])
        await q.edit_message_text(
            f"✅ Overtime submitted!\nID: {rid}\nDate: {data['date']}\n"
            f"Hours: {hrs} × {OT_RATE_DEFAULT} = {round(hrs*OT_RATE_DEFAULT,2)}\nSubmitted: {sub}",
            reply_markup=InlineKeyboardMarkup(conf_kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[blt(),bm()]]))
    return ConversationHandler.END


def _bh():
    return [CallbackQueryHandler(back_lt,pattern="^back_to_leave_type$"),
            CallbackQueryHandler(back_menu_conv,pattern="^back_to_menu$")]

def get_leave_conversation_handler():
    bh=_bh()
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(leave_start,pattern="^menu_request_leave$")],
        states={
            LEAVE_TYPE:[CallbackQueryHandler(leave_type_sel,pattern="^ltype_"),CallbackQueryHandler(back_menu_conv,pattern="^back_to_menu$")],
            LEAVE_START:[MessageHandler(filters.TEXT & ~filters.COMMAND,l_start)]+bh,
            LEAVE_END:[MessageHandler(filters.TEXT & ~filters.COMMAND,l_end)]+bh,
            LEAVE_REASON:[MessageHandler(filters.TEXT & ~filters.COMMAND,l_reason)]+bh,
            LEAVE_SICK_PHOTO:[MessageHandler(filters.PHOTO,l_photo),CallbackQueryHandler(l_sick_done,pattern="^sick_done$")]+bh+[
                MessageHandler(filters.TEXT & ~filters.COMMAND,l_photo)],
            LEAVE_CONFIRM:[CallbackQueryHandler(l_confirmed,pattern="^leave_confirm_")]+bh,
            # Early Departure states
            ED_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND,ed_date_inp)]+bh,
            ED_TIME:[MessageHandler(filters.TEXT & ~filters.COMMAND,ed_time_inp)]+bh,
            ED_REASON_ST:[CallbackQueryHandler(ed_reason_pick,pattern="^ed_rsn_")]+bh,
            ED_CONFIRM_ST:[CallbackQueryHandler(ed_confirm,pattern="^leave_confirm_")]+bh,
            # Overtime states
            OT_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND,ot_date_inp)]+bh,
            OT_HOURS_ST:[CallbackQueryHandler(ot_hours_sel,pattern="^ot_hrs_")]+bh,
            OT_REASON_ST:[MessageHandler(filters.TEXT & ~filters.COMMAND,ot_reason_inp)]+bh,
            OT_CONFIRM_ST:[CallbackQueryHandler(ot_confirm,pattern="^leave_confirm_")]+bh,
        },fallbacks=[MessageHandler(filters.COMMAND,l_cancel)],per_message=False)


# ══════════════════════════════════════════════════════════════════
#  TEAM REQUEST FOR EMPLOYEE
# ══════════════════════════════════════════════════════════════════
async def team_req_start(u,c):
    q=u.callback_query; await q.answer()
    mc=find_emp_code_by_tid(str(q.from_user.id)); mr=get_user_role(str(q.from_user.id))
    if not mc: await q.edit_message_text("❌",reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    team=get_my_team(mc,mr)
    if not team: await q.edit_message_text("ℹ️ No team.",reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    kb=[]
    for ec in team:
        nm,_=get_employee_name(ec); kb.append([InlineKeyboardButton(f"👤 {nm} ({ec})",callback_data=f"te_{ec}")])
    kb.append([bm()])
    await q.edit_message_text("👥 Select employee:",reply_markup=InlineKeyboardMarkup(kb)); return TEAM_SELECT_EMP

async def te_sel(u,c):
    q=u.callback_query; await q.answer(); ec=q.data.replace("te_","")
    nm,_=get_employee_name(ec); c.user_data["target_emp_code"]=ec; c.user_data["target_emp_name"]=nm
    c.user_data["requesting_for"]="employee"; c.user_data["sick_photos"]=[]
    kb=[[InlineKeyboardButton("🏖 Paid",callback_data="tlt_Paid"),InlineKeyboardButton("🤒 Sick",callback_data="tlt_Sick")],
        [InlineKeyboardButton("🚨 Emergency",callback_data="tlt_Emergency"),InlineKeyboardButton("📋 Unpaid",callback_data="tlt_Unpaid")],
        [InlineKeyboardButton("🚗 Business Trip",callback_data="tlt_Business_Trip")],
        [InlineKeyboardButton("🚪 Early Departure",callback_data="tlt_Early_Departure")],
        [InlineKeyboardButton("⏰ Planned OT",callback_data="tlt_Overtime_Planned"),
         InlineKeyboardButton("🚨 Emergency OT",callback_data="tlt_Overtime_Emergency")],
        [InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]]
    await q.edit_message_text(f"📝 Leave for {nm}\n\nType:",reply_markup=InlineKeyboardMarkup(kb)); return TEAM_LEAVE_TYPE

async def t_back(u,c): return await team_req_start(u,c)

async def tlt_sel(u,c):
    q=u.callback_query; await q.answer(); lt=q.data.replace("tlt_",""); c.user_data["leave_type"]=lt
    nm=c.user_data.get("target_emp_name","")
    bk=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]])
    if lt=="Early_Departure":
        ec=c.user_data.get("target_emp_code")
        if ec:
            ed_cnt=count_ed_this_month(ec)
            if ed_cnt>=2:
                await q.edit_message_text(
                    f"❌ {nm} has already used 2 early departures this month (max 2).",
                    reply_markup=bk); return TEAM_LEAVE_TYPE
            c.user_data["ed_count_used"]=ed_cnt
        await q.edit_message_text(
            f"🚪 Early Departure for {nm}\n\nDate (`DD/MM/YYYY`) — today or future:",
            parse_mode="Markdown",reply_markup=bk); return ED_DATE
    elif lt in ("Overtime_Planned","Overtime_Emergency"):
        label="tomorrow or later" if lt=="Overtime_Planned" else "today or yesterday"
        await q.edit_message_text(
            f"{'⏰' if 'Planned' in lt else '🚨'} OT for {nm}\n\nDate (`DD/MM/YYYY`) — {label}:",
            parse_mode="Markdown",reply_markup=bk); return OT_DATE
    await q.edit_message_text(f"{TYPE_EMOJI.get(lt,'📋')} {lt} for {nm}\n\nStart: `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk); return TEAM_START

async def t_start(u,c):
    t=u.message.text.strip(); bk=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]])
    try: sd=datetime.strptime(t,"%d/%m/%Y").date()
    except: await u.message.reply_text("⚠️ `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk); return TEAM_START
    lt=c.user_data.get("leave_type","")
    min_date=datetime.now().date()-timedelta(days=2) if lt=="Business_Trip" else datetime.now().date()
    if sd<min_date:
        msg="⚠️ Past. Business trips can be submitted up to 2 days after." if lt=="Business_Trip" else "⚠️ Past."
        await u.message.reply_text(msg,reply_markup=bk); return TEAM_START
    c.user_data["start_date"]=sd; c.user_data["start_date_str"]=t
    await u.message.reply_text(f"✅ {t}\n\nEnd: `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk); return TEAM_END

async def t_end(u,c):
    t=u.message.text.strip(); bk=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]])
    try: ed=datetime.strptime(t,"%d/%m/%Y").date()
    except: await u.message.reply_text("⚠️ `DD/MM/YYYY`",parse_mode="Markdown",reply_markup=bk); return TEAM_END
    sd=c.user_data["start_date"]
    if ed<sd: await u.message.reply_text("⚠️ Before.",reply_markup=bk); return TEAM_END
    c.user_data["end_date"]=ed; c.user_data["end_date_str"]=t
    await u.message.reply_text(f"✅ {t}\n\nReason:",reply_markup=bk); return TEAM_REASON

async def t_reason(u,c):
    r=u.message.text.strip(); bk=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]])
    if len(r)<3: await u.message.reply_text("⚠️ Short.",reply_markup=bk); return TEAM_REASON
    c.user_data["reason"]=r
    if c.user_data["leave_type"]=="Sick":
        await u.message.reply_text("🏥 Photo(s).",reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Done",callback_data="t_pdone")],[InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]]))
        return TEAM_SICK_PHOTO
    return await _summary(u,c)

async def t_photo(u,c):
    if u.message.photo:
        if "sick_photos" not in c.user_data: c.user_data["sick_photos"]=[]
        c.user_data["sick_photos"].append(u.message.photo[-1].file_id)
        await u.message.reply_text(f"📷 {len(c.user_data['sick_photos'])}.",reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Done",callback_data="t_pdone")],[InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]]))
    return TEAM_SICK_PHOTO

async def t_pdone(u,c):
    q=u.callback_query; await q.answer()
    if not c.user_data.get("sick_photos"):
        await q.edit_message_text("⚠️ Upload.",reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Done",callback_data="t_pdone")],[InlineKeyboardButton("↩️ Back",callback_data="t_back"),bm()]]))
        return TEAM_SICK_PHOTO
    await q.edit_message_text(f"✅ {len(c.user_data['sick_photos'])} photo(s)."); return await _summary(u,c,True)

def get_team_request_handler():
    tbh=[CallbackQueryHandler(t_back,pattern="^t_back$"),CallbackQueryHandler(back_menu_conv,pattern="^back_to_menu$")]
    # back_to_leave_type acts as back within team flow
    tbh_ed=[CallbackQueryHandler(t_back,pattern="^back_to_leave_type$"),
            CallbackQueryHandler(t_back,pattern="^t_back$"),
            CallbackQueryHandler(back_menu_conv,pattern="^back_to_menu$")]
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(team_req_start,pattern="^menu_team_request$")],
        states={
            TEAM_SELECT_EMP:[CallbackQueryHandler(te_sel,pattern="^te_"),CallbackQueryHandler(back_menu_conv,pattern="^back_to_menu$")],
            TEAM_LEAVE_TYPE:[CallbackQueryHandler(tlt_sel,pattern="^tlt_")]+tbh,
            TEAM_START:[MessageHandler(filters.TEXT & ~filters.COMMAND,t_start)]+tbh,
            TEAM_END:[MessageHandler(filters.TEXT & ~filters.COMMAND,t_end)]+tbh,
            TEAM_REASON:[MessageHandler(filters.TEXT & ~filters.COMMAND,t_reason)]+tbh,
            TEAM_SICK_PHOTO:[MessageHandler(filters.PHOTO,t_photo),CallbackQueryHandler(t_pdone,pattern="^t_pdone$")]+tbh,
            TEAM_CONFIRM:[CallbackQueryHandler(l_confirmed,pattern="^leave_confirm_")]+tbh,
            # Early Departure (shared handlers, user_data["requesting_for"]=="employee")
            ED_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND,ed_date_inp)]+tbh_ed,
            ED_TIME:[MessageHandler(filters.TEXT & ~filters.COMMAND,ed_time_inp)]+tbh_ed,
            ED_REASON_ST:[CallbackQueryHandler(ed_reason_pick,pattern="^ed_rsn_")]+tbh_ed,
            ED_CONFIRM_ST:[CallbackQueryHandler(ed_confirm,pattern="^leave_confirm_")]+tbh_ed,
            # Overtime (shared handlers)
            OT_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND,ot_date_inp)]+tbh_ed,
            OT_HOURS_ST:[CallbackQueryHandler(ot_hours_sel,pattern="^ot_hrs_")]+tbh_ed,
            OT_REASON_ST:[MessageHandler(filters.TEXT & ~filters.COMMAND,ot_reason_inp)]+tbh_ed,
            OT_CONFIRM_ST:[CallbackQueryHandler(ot_confirm,pattern="^leave_confirm_")]+tbh_ed,
        },fallbacks=[MessageHandler(filters.COMMAND,l_cancel)],per_message=False)


# ══════════════════════════════════════════════════════════════════
#  MY REQUESTS — Previous / Upcoming → List → Detail
# ══════════════════════════════════════════════════════════════════
async def my_requests_handler(u,c):
    q=u.callback_query; await q.answer()
    # Show Previous / Upcoming choice
    kb=[[InlineKeyboardButton("📁 Previous Requests",callback_data="myreq_prev"),
         InlineKeyboardButton("📅 Upcoming Requests",callback_data="myreq_upcoming")],
        [InlineKeyboardButton("↩️ Back",callback_data="menu_leave"),bm()]]
    await q.edit_message_text("📋 My Requests\n\nSelect:",reply_markup=InlineKeyboardMarkup(kb))

async def myreq_list(u,c):
    """Show list of previous or upcoming requests."""
    q=u.callback_query; await q.answer(); mode=q.data.replace("myreq_","")
    await q.edit_message_text("⏳ Loading...")
    try:
        ec=find_emp_code_by_tid(str(q.from_user.id))
        if not ec: await q.edit_message_text("❌",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ My Requests",callback_data="menu_my_requests"),bm()]])); return
        today=datetime.now().date()
        rows=get_sheet("Leave_Log").get_all_values(); reqs=[]
        for i,r in enumerate(rows):
            if i==0: continue
            if r[1].strip()!=str(ec): continue
            ed=_parse_date(r[4]) if len(r)>4 else None
            if mode=="prev" and ed and ed<today: reqs.append(r)
            elif mode=="upcoming" and ed and ed>=today: reqs.append(r)
        if not reqs:
            label="previous" if mode=="prev" else "upcoming"
            await q.edit_message_text(f"ℹ️ No {label} requests.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="menu_my_requests"),bm()]])); return
        reqs.reverse(); reqs=reqs[:15]
        kb=[]
        for r in reqs:
            rid=r[0]; lt=r[2]; em=TYPE_EMOJI.get(lt,"📋"); final=r[15].strip() if len(r)>15 else "⏳"
            si="✅" if final=="Approved" else "❌" if final=="Rejected" else "⏳"
            label=f"{si} {r[3]}-{r[4]} {lt}"
            kb.append([InlineKeyboardButton(f"{em} {label}",callback_data=f"rview_{rid}")])
        kb.append([InlineKeyboardButton("↩️ Back",callback_data="menu_my_requests"),bm()])
        title="📁 Previous" if mode=="prev" else "📅 Upcoming"
        await q.edit_message_text(f"{title} ({len(reqs)})\n\nTap to view:",reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ My Requests",callback_data="menu_my_requests"),bm()]]))


# ══════════════════════════════════════════════════════════════════
#  TEAM REQUESTS — Previous / Upcoming
# ══════════════════════════════════════════════════════════════════
async def team_requests_handler(u,c):
    q=u.callback_query; await q.answer()
    kb=[[InlineKeyboardButton("📁 Previous",callback_data="teamreq_prev"),
         InlineKeyboardButton("📅 Upcoming",callback_data="teamreq_upcoming")],
        [InlineKeyboardButton("↩️ Back",callback_data="menu_leave"),bm()]]
    await q.edit_message_text("📂 Team Requests\n\nSelect:",reply_markup=InlineKeyboardMarkup(kb))

async def teamreq_list(u,c):
    q=u.callback_query; await q.answer(); mode=q.data.replace("teamreq_","")
    await q.edit_message_text("⏳ Loading...")
    try:
        mc=find_emp_code_by_tid(str(q.from_user.id)); mr=get_user_role(str(q.from_user.id))
        team=get_my_team(mc,mr)
        if not team: await q.edit_message_text("ℹ️ No team.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="menu_team_requests"),bm()]])); return
        today=datetime.now().date()
        rows=get_sheet("Leave_Log").get_all_values(); reqs=[]
        for i,r in enumerate(rows):
            if i==0: continue
            if r[1].strip() not in team: continue
            ed=_parse_date(r[4]) if len(r)>4 else None
            if mode=="prev" and ed and ed<today: reqs.append(r)
            elif mode=="upcoming" and ed and ed>=today: reqs.append(r)
        if not reqs:
            await q.edit_message_text(f"ℹ️ No {'previous' if mode=='prev' else 'upcoming'} team requests.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="menu_team_requests"),bm()]])); return
        reqs.reverse(); reqs=reqs[:15]
        kb=[]
        for r in reqs:
            nm,_=get_employee_name(r[1]); lt=r[2]; em=TYPE_EMOJI.get(lt,"📋")
            final=r[15].strip() if len(r)>15 else "⏳"
            si="✅" if final=="Approved" else "❌" if final=="Rejected" else "⏳"
            kb.append([InlineKeyboardButton(f"{em} {si} {nm} {r[3]}-{r[4]}",callback_data=f"rview_{r[0]}")])
        kb.append([InlineKeyboardButton("↩️ Back",callback_data="menu_team_requests"),bm()])
        title="📁 Previous" if mode=="prev" else "📅 Upcoming"
        await q.edit_message_text(f"{title} Team ({len(reqs)})\n\nTap to view:",reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="menu_team_requests"),bm()]]))


# ══════════════════════════════════════════════════════════════════
#  VIEW REQUEST DETAIL (from My Requests or Team Requests)
# ══════════════════════════════════════════════════════════════════
async def request_view_handler(u,c):
    q=u.callback_query; await q.answer()
    rid=q.data.replace("rview_","")
    try:
        rd=None
        for i,r in enumerate(get_sheet("Leave_Log").get_all_values()):
            if i==0: continue
            if r[0].strip()==rid: rd=r; break
        if not rd: await q.edit_message_text("❌ Not found.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ My Requests",callback_data="menu_my_requests"),bm()]])); return
        ec=rd[1]; lt=rd[2]; nm,dept=get_employee_name(ec)
        em=TYPE_EMOJI.get(lt,"📋"); final=rd[15].strip() if len(rd)>15 else "Pending"
        sub=rd[21].strip() if len(rd)>21 else "-"
        chain=get_chain(ec,lt); st=build_status(rd,chain)
        si="✅" if final=="Approved" else "❌" if final=="Rejected" else "⏳"
        rej=f"\nRejection: {rd[16].strip()}" if final=="Rejected" and len(rd)>16 and rd[16].strip() else ""

        msg=(f"{em} {lt} Leave - {si} {final}\n{'─'*28}\n"
             f"👤 {nm} ({ec})\n🏢 {dept}\n"
             f"📅 {rd[3]} to {rd[4]} ({rd[5]} days)\n"
             f"💬 {rd[8]}\n🕐 Submitted: {sub}\n🔖 {rid}{rej}\n\n"
             f"Approvals:\n{st}\n")

        kb=[]
        if final in ("Approved","Rejected"):
            kb.append([InlineKeyboardButton("📄 Download PDF",callback_data=f"pdf_{rid}")])
        kb.append([InlineKeyboardButton("↩️ Close",callback_data="menu_my_requests"),bm()])
        await q.edit_message_text(msg,reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ My Requests",callback_data="menu_my_requests"),bm()]]))


# ══════════════════════════════════════════════════════════════════
#  PDF DOWNLOAD
# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
#  GOOGLE DRIVE UPLOAD
# ══════════════════════════════════════════════════════════════════
def _get_drive_folder_id(emp_code):
    """Get the Google Drive folder ID from Employee_DB Drive_Folder_Link column."""
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code", "")) == str(emp_code):
            link = str(r.get("Drive_Folder_Link", "")).strip()
            print(f"[DRIVE] Employee {emp_code} folder link: '{link}'")
            if not link:
                print(f"[DRIVE] No folder link for {emp_code}")
                return None
            if "/folders/" in link:
                fid = link.split("/folders/")[-1].split("?")[0].split("/")[0]
                print(f"[DRIVE] Extracted folder ID: {fid}")
                return fid if fid else None
            print(f"[DRIVE] Link format not recognized: {link}")
            return None
    print(f"[DRIVE] Employee {emp_code} not found in DB")
    return None


def _upload_to_drive(pdf_bytes, filename, folder_id):
    """Upload PDF to Google Drive via Apps Script middleman."""
    import base64
    import urllib.request
    import json

    APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxKtTNn_1TRofVi_QUGoF6aMOVJdmzs4LyMksvaIVg2j_lzadK0VJ-vrUwM0ss72FEIpA/exec"

    try:
        print(f"[DRIVE] Uploading {filename} to folder {folder_id} via Apps Script")

        payload = json.dumps({
            "folder_id": folder_id,
            "filename": filename,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8")
        }).encode("utf-8")

        req = urllib.request.Request(
            APPS_SCRIPT_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # Apps Script redirects, so we need to follow it
        import urllib.request as ur
        opener = ur.build_opener(ur.HTTPRedirectHandler)
        response = opener.open(req, timeout=30)
        result = json.loads(response.read().decode("utf-8"))

        if result.get("success"):
            print(f"[DRIVE] Success! URL: {result.get('file_url', '')}")
            return result.get("file_url", "")
        else:
            print(f"[DRIVE] Apps Script error: {result.get('error', 'unknown')}")
            return None
    except Exception as e:
        print(f"[DRIVE] Upload FAILED: {type(e).__name__}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
#  PDF DOWNLOAD + DRIVE UPLOAD
# ══════════════════════════════════════════════════════════════════
async def pdf_download_handler(u,c):
    q=u.callback_query; await q.answer(); rid=q.data.replace("pdf_","")
    await c.bot.send_message(chat_id=q.message.chat_id,text="⏳ Generating PDF...")
    try:
        rd=None
        for i,r in enumerate(get_sheet("Leave_Log").get_all_values()):
            if i==0: continue
            if r[0].strip()==rid: rd=r; break
        if not rd: await c.bot.send_message(chat_id=q.message.chat_id,text="❌",reply_markup=InlineKeyboardMarkup([[bm()]])); return
        ec=rd[1]; lt=rd[2]; nm,dept=get_employee_name(ec)
        chain=get_chain(ec,lt); cd=[]
        emp_d=None
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code",""))==str(ec): emp_d=r; break
        for idx,role in enumerate(chain):
            sc=STAGE_COLUMNS[idx][0]-1; dc=STAGE_COLUMNS[idx][1]-1
            aname=""
            if role=="manager" and emp_d:
                mc=str(emp_d.get("Manager_Code","")); n,_=get_employee_name(mc) if mc else ("",""); aname=n if n!=mc else ""
            elif role=="hr":
                for i2,r2 in enumerate(get_sheet("User_Registry").get_all_values()):
                    if i2==0: continue
                    if len(r2)>3 and r2[3].strip()=="HR_Manager" and r2[0].strip():
                        n,_=get_employee_name(r2[0].strip()); aname=n if n!=r2[0].strip() else ""; break
            elif role=="director":
                for i2,r2 in enumerate(get_sheet("User_Registry").get_all_values()):
                    if i2==0: continue
                    if len(r2)>3 and r2[3].strip()=="Director" and r2[0].strip():
                        n,_=get_employee_name(r2[0].strip()); aname=n if n!=r2[0].strip() else ""; break
            cd.append({"role":ROLE_LABELS_MAP.get(role,role),"status":rd[sc].strip() if sc<len(rd) else "Pending",
                       "date":rd[dc].strip() if dc<len(rd) else "","name":aname})
        pdf_data={"request_id":rid,"emp_code":ec,"full_name":nm,"department":dept,
            "leave_type":lt,"start_date":rd[3],"end_date":rd[4],"working_days":rd[5],
            "reason":rd[8],"final_status":rd[15].strip() if len(rd)>15 else "?",
            "approval_chain":cd,"rejection_reason":rd[16].strip() if len(rd)>16 else "",
            "submitted_at":rd[21].strip() if len(rd)>21 else "-"}
        pdf_bytes=generate_leave_pdf(pdf_data)

        # Build filename: EmpCode-type_vacation-RequestID-StartDate.pdf
        # e.g. 1011-paid_vacation-LVE-2026-0019-30-03-2026.pdf
        type_label = lt.lower() + "_vacation"
        start_clean = rd[3].replace("/", "-") if len(rd) > 3 else "unknown"
        filename = f"{ec}-{type_label}-{rid}-{start_clean}.pdf"

        # Upload to Drive and show link
        from drive_utils import upload_to_drive as drive_upload
        drive_link = drive_upload(pdf_bytes, filename, "leave_approvals")
        if drive_link:
            await c.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"📄 {rid} — {pdf_data['final_status']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 View PDF", url=drive_link)]]))
        else:
            f=io.BytesIO(pdf_bytes); f.name=filename
            await c.bot.send_document(chat_id=q.message.chat_id,document=f,filename=filename,
                caption=f"📄 {rid} - {pdf_data['final_status']}")
    except Exception as e:
        await c.bot.send_message(chat_id=q.message.chat_id,text=f"❌ PDF: {e}",reply_markup=InlineKeyboardMarkup([[bm()]]))


# ══════════════════════════════════════════════════════════════════
#  BALANCE
# ══════════════════════════════════════════════════════════════════
async def leave_balance_handler(u,c):
    q=u.callback_query; await q.answer(); await q.edit_message_text("⏳")
    try:
        ec=find_emp_code_by_tid(str(q.from_user.id))
        if not ec: await q.edit_message_text("❌",reply_markup=InlineKeyboardMarkup([[bm()]])); return
        emp=None
        for r in get_sheet("Leave_Balance").get_all_records():
            if str(r.get("Emp_Code",""))==str(ec): emp=r; break
        if not emp: await q.edit_message_text("❌ No record.",reply_markup=InlineKeyboardMarkup([[bm()]])); return
        msg=(f"📊 {emp.get('Full_Name',ec)}\n{'─'*28}\n\n✅ Available: {emp.get('Total_Balance_Remaining',0)} days\n\n{'─'*28}\n"
             f"  🏖 Paid: {emp.get('Annual_Used',0)}  🤒 Sick: {emp.get('Sick_Used',0)}\n"
             f"  🚨 Emergency: {emp.get('Emergency_Used',0)}  📋 Unpaid: {emp.get('Unpaid_Used',0)}\n"
             f"{'─'*28}\nUpdated: {emp.get('Last_Updated','-')}")
        bk2=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="menu_leave"),bm()]])
        await q.edit_message_text(msg,reply_markup=bk2)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back",callback_data="menu_leave"),bm()]]))
