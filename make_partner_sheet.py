#!/usr/bin/env python3
"""
Generate a Linear Clockworks fulfillment partner Google Sheet.
Usage: python3.12 make_partner_sheet.py "Ted" 40 55
       python3.12 make_partner_sheet.py "Brian" 40 58

Pricing Table sheet is the source of truth for clock pricing — partner can edit yellow cells
percentages and prices there and Summary/Drilldown recalculate live.
"""

import sys, os, pickle
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
SCOPES      = ["https://www.googleapis.com/auth/spreadsheets",
               "https://www.googleapis.com/auth/drive"]
TOKEN_FILE  = os.path.expanduser("~/shopify_scripts/franchising/sheets_token.pickle")
CLIENT_FILE = os.path.expanduser("~/shopify_scripts/franchising/sheets_oauth_client.json")

CLOCKS = [
    {"name": "3-ft No River",      "body": 325, "sled": 85, "assy_ship": 140, "price": 1225},
    {"name": "3-ft Surface River", "body": 350, "sled": 85, "assy_ship": 140, "price": 1850},
    {"name": "3-ft Through River", "body": 500, "sled": 85, "assy_ship": 140, "price": 2200},
    {"name": "5-ft No River",      "body": 480, "sled": 85, "assy_ship": 140, "price": 1550},
    {"name": "5-ft Surface River", "body": 575, "sled": 85, "assy_ship": 140, "price": 2150},
    {"name": "5-ft Through River", "body": 775, "sled": 85, "assy_ship": 140, "price": 2650},
    {"name": "RTA 3-ft Claret",    "body": 100, "sled": 85, "assy_ship":  25, "price":  500},
    {"name": "RTA 5-ft Claret",    "body": 150, "sled": 85, "assy_ship":  25, "price":  600},
]

# ── Pricing Table cell addresses (1-indexed row, used to build formulas) ──
# Row 1  : header
# Pricing Table sheet layout (no header rows above data):
# Row 1  : clock table header
# Row 2+ : clock data   A=name B=body C=assy_ship D=sled E=price

CLOCK_DATA_START = 2    # 1-indexed row where first clock data lives (no header rows above)

def clock_row(i):
    """1-indexed row in Pricing Table for clock index i (0-based)."""
    return CLOCK_DATA_START + i

# Sheet name for pricing table cross-references
A  = "Pricing Table"
def aref(cell):   return f"'{A}'!{cell}"
# Percentages baked in as literals — not editable in sheet
# PCT_A_REF and PCT_B_REF defined after CLI args below

def price_ref(i):   return aref(f"E{clock_row(i)}")
def body_ref(i):    return aref(f"B{clock_row(i)}")
def assy_ref(i):    return aref(f"C{clock_row(i)}")
def sled_ref(i):    return aref(f"D{clock_row(i)}")
def name_ref(i):    return aref(f"A{clock_row(i)}")

# ── CLI ───────────────────────────────────────────────────────────────────────
if len(sys.argv) < 4:
    print('Usage: python3.12 make_partner_sheet.py "PartnerName" <ScenarioA%> <ScenarioB%>')
    sys.exit(1)

PARTNER = sys.argv[1]
PCT_A   = int(sys.argv[2])
PCT_B   = int(sys.argv[3])
PCT_A_REF = str(PCT_A / 100)   # literal decimal baked into formulas
PCT_B_REF = str(PCT_B / 100)
TODAY   = datetime.now().strftime("%b %-d, %Y")
TITLE   = f"LCW Fulfillment — {PARTNER} — {TODAY}"

# ── Auth ──────────────────────────────────────────────────────────────────────
creds = None
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)

sheets = build("sheets", "v4", credentials=creds)
drive  = build("drive",  "v3", credentials=creds)

# ── Colors ────────────────────────────────────────────────────────────────────
NAVY   = {"red": 0.18, "green": 0.23, "blue": 0.36}
BLUE   = {"red": 0.22, "green": 0.37, "blue": 0.65}
GREEN  = {"red": 0.12, "green": 0.62, "blue": 0.46}
LGRAY  = {"red": 0.95, "green": 0.95, "blue": 0.95}
LBLUE  = {"red": 0.88, "green": 0.93, "blue": 0.98}
LGREEN = {"red": 0.86, "green": 0.96, "blue": 0.92}
WHITE  = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
DKGRAY = {"red": 0.25, "green": 0.25, "blue": 0.25}
YELLOW = {"red": 1.0,  "green": 0.98, "blue": 0.82}
POS    = {"red": 0.05, "green": 0.45, "blue": 0.20}
NEG    = {"red": 0.70, "green": 0.10, "blue": 0.10}

# ── Cell helpers ──────────────────────────────────────────────────────────────
MONEY  = {"numberFormat": {"type": "CURRENCY", "pattern": '"$"#,##0'}}
ACCT   = {"numberFormat": {"type": "NUMBER",   "pattern": '#,##0_);(#,##0)'}}
PCT_FMT= {"numberFormat": {"type": "PERCENT",  "pattern": "0%"}}
DELTA_FMT = {"numberFormat": {"type": "CURRENCY",
             "pattern": '"▲ $"#,##0;"▼ $"#,##0;"-"'},
             "textFormat": {"bold": True}}

def s(v, bold=False, italic=False, bg=None, fg=None, align=None, size=None):
    fmt, tf = {}, {}
    if bold:   tf["bold"] = True
    if italic: tf["italic"] = True
    if fg:     tf["foregroundColor"] = fg
    if size:   tf["fontSize"] = size
    if tf:     fmt["textFormat"] = tf
    if bg:     fmt["backgroundColor"] = bg
    if align:  fmt["horizontalAlignment"] = align
    return {"userEnteredValue": {"stringValue": str(v)},
            "userEnteredFormat": fmt} if fmt else {"userEnteredValue": {"stringValue": str(v)}}

def n(v, fmt=None, bg=None, bold=False):
    f = dict(fmt) if fmt else {}
    if bg:   f["backgroundColor"] = bg
    if bold: f.setdefault("textFormat", {})["bold"] = True
    return {"userEnteredValue": {"numberValue": v}, "userEnteredFormat": f} if f \
           else {"userEnteredValue": {"numberValue": v}}

def f(formula, fmt=None, bg=None, bold=False, fg=None):
    """Formula cell."""
    fm = dict(fmt) if fmt else {}
    if bg:   fm["backgroundColor"] = bg
    if bold: fm.setdefault("textFormat", {})["bold"] = True
    if fg:   fm.setdefault("textFormat", {})["foregroundColor"] = fg
    return {"userEnteredValue": {"formulaValue": formula},
            "userEnteredFormat": fm} if fm else {"userEnteredValue": {"formulaValue": formula}}

def hdr(text, bg=NAVY, fg=WHITE):
    return s(text, bold=True, bg=bg, fg=fg, align="CENTER")

def b():
    return {"userEnteredValue": {"stringValue": ""}}

def write(sheet_id, row_idx, rows):
    sheets.spreadsheets().batchUpdate(spreadsheetId=SS_ID, body={"requests": [
        {"updateCells": {
            "range": {"sheetId": sheet_id,
                      "startRowIndex": row_idx,
                      "endRowIndex":   row_idx + len(rows),
                      "startColumnIndex": 0,
                      "endColumnIndex":   max(len(r) for r in rows)},
            "rows":   [{"values": r} for r in rows],
            "fields": "userEnteredValue,userEnteredFormat"
        }}
    ]}).execute()

# ── Create spreadsheet ────────────────────────────────────────────────────────
print(f"Creating: {TITLE}")
ss    = sheets.spreadsheets().create(body={
    "properties": {"title": TITLE},
    "sheets": [
        {"properties": {"sheetId": 0, "title": "Summary",     "gridProperties": {"frozenRowCount": 3}}},
        {"properties": {"sheetId": 1, "title": "Drilldown",   "gridProperties": {"frozenRowCount": 2}}},
        {"properties": {"sheetId": 2, "title": "Pricing Table", "gridProperties": {"frozenRowCount": 1}}},
    ]
}).execute()
SS_ID = ss["spreadsheetId"]
URL   = f"https://docs.google.com/spreadsheets/d/{SS_ID}"

# ══════════════════════════════════════════════════════════════════════════════
# ASSUMPTIONS — raw inputs only, yellow-highlighted editable cells
# ══════════════════════════════════════════════════════════════════════════════
assump = [
    # Row 1: clock table header
    [hdr("Clock"), hdr("Body Fee"), hdr("Assy + Ship"), hdr("Sled (LCW)"), hdr("Sale Price")],
    # Rows 2–9: clock data  ← EDITABLE (all yellow)
    *[[s(c["name"]),
       n(c["body"],     MONEY, bg=YELLOW),
       n(c["assy_ship"],MONEY, bg=YELLOW),
       n(c["sled"],     MONEY, bg=YELLOW),
       n(c["price"],    MONEY, bg=YELLOW)] for c in CLOCKS]
]

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY — all values from Pricing Table via formulas
# ══════════════════════════════════════════════════════════════════════════════
# Column layout:
# A: Clock name
# B: Sale price
# C: Current partner gross (body fee)
# D: Scenario A LCW net
# E: Scenario A partner gross
# F: Scenario A delta vs current
# G: Scenario B LCW net
# H: Scenario B partner gross
# I: Scenario B delta vs current

summary = []

# Row 1: title
summary.append([s("Linear Clockworks — Fulfillment Partner Offer",
                   bold=True, size=14, bg=NAVY, fg=WHITE, align="CENTER")] + [b()]*8)
# Row 2: subtitle — static string baked in at generation time
summary.append([s(
    f"For: {PARTNER}   |   Scenario A: partner {PCT_A}% / LCW {100-PCT_A}%   |   Scenario B: partner {PCT_B}% / LCW {100-PCT_B}%   |   {TODAY}",
    italic=True, bg=LGRAY, align="CENTER")] + [b()]*8)
# Row 3: column headers
summary.append([
    hdr("Clock"),
    hdr("Sale Price"),
    hdr("Current\nPartner Net"),
    hdr("Scenario A\nLCW Net",       bg=BLUE),
    hdr("Scenario A\nPartner Net", bg=BLUE),
    hdr("Scenario A\nDelta",         bg=BLUE),
    hdr("Scenario B\nLCW Net",       bg=GREEN),
    hdr("Scenario B\nPartner Net", bg=GREEN),
    hdr("Scenario B\nDelta",         bg=GREEN),
])

for i in range(len(CLOCKS)):
    bg   = WHITE if i % 2 == 0 else LGRAY
    pr   = price_ref(i)
    br   = body_ref(i)
    ar   = assy_ref(i)
    sr   = sled_ref(i)
    pa   = PCT_A_REF
    pb   = PCT_B_REF

    # Partner net = gross share - assy (only new cost vs current)
    # Delta = partner net - body fee (current net)

    p1_fml   = f"ROUND({pr}*{pa},0)-{ar}"
    p2_fml   = f"ROUND({pr}*{pb},0)-{ar}"
    lcwa_fml = f"{pr}*(1-{pa})-{sr}"
    lcwb_fml = f"{pr}*(1-{pb})-{sr}"
    d1_fml   = f"ROUND({pr}*{pa},0)-{ar}-{br}"
    d2_fml   = f"ROUND({pr}*{pb},0)-{ar}-{br}"

    def mf(formula, bold=False):
        fmt = dict(MONEY)
        fmt["backgroundColor"] = bg
        if bold: fmt.setdefault("textFormat", {})["bold"] = True
        return {"userEnteredValue": {"formulaValue": f"={formula}"},
                "userEnteredFormat": fmt}

    def df(formula):
        fmt = {"numberFormat": {"type": "NUMBER",
                                "pattern": '+ #,##0;(#,##0);"-"'},
               "textFormat": {"bold": True},
               "backgroundColor": bg}
        return {"userEnteredValue": {"formulaValue": f"={formula}"},
                "userEnteredFormat": fmt}

    summary.append([
        f(f"={name_ref(i)}", bg=bg, bold=True),
        mf(pr),
        mf(br),
        mf(lcwa_fml),
        mf(p1_fml, bold=True),
        df(d1_fml),
        mf(lcwb_fml),
        mf(p2_fml, bold=True),
        df(d2_fml),
    ])

# Notes rows
notes_start = len(summary)
summary += [
    [b()]*9,
    [s("Partner's share covers: body/materials, assembly, calibration, testing, photography, and shipping to customer. Sled supplied by LCW at no charge.",
       italic=True, fg=DKGRAY)] + [b()]*8,
    [s("LCW's share covers: sled kit, Shopify fees, payment processing, packaging, all marketing & advertising, website, gallery relationships, award submissions, customer service, warranty, firmware development, brand equity, and IP. See Fulfillment Partner Agreement for full detail.",
       italic=True, fg=DKGRAY)] + [b()]*8,
    [s("→ To model different sale prices, edit the yellow cells on the Pricing Table tab.",
       bold=True, fg=BLUE)] + [b()]*8,
]

# ══════════════════════════════════════════════════════════════════════════════
# DRILLDOWN — full line-item breakdown per clock, all formulas
# ══════════════════════════════════════════════════════════════════════════════
# Column layout: A=clock, B=line item,
#   C=current amount, D=current note,
#   E=ScenA amount,   F=ScenA note,
#   G=ScenB amount,   H=ScenB note

dd = []

dd.append([
    hdr(""), hdr("Line Item"),
    hdr("CURRENT — LCW does everything"), hdr(""),
    hdr("SCENARIO A — LCW customer", bg=BLUE),    hdr("", bg=BLUE),
    hdr("SCENARIO B — Partner customer", bg=GREEN), hdr("", bg=GREEN),
])
dd.append([
    hdr("Clock"), hdr(""),
    hdr("Amount"), hdr(""),
    hdr("Amount", bg=BLUE), hdr("vs. Current", bg=BLUE),
    hdr("Amount", bg=GREEN), hdr("vs. Current", bg=GREEN),
])

for i, c in enumerate(CLOCKS):
    bg  = LBLUE if i % 2 == 0 else LGREEN
    pr  = price_ref(i)
    br  = body_ref(i)
    ar  = assy_ref(i)
    sr  = sled_ref(i)
    pa  = PCT_A_REF
    pb  = PCT_B_REF

    def mfdd(formula, bold=False):
        fmt = dict(ACCT)
        fmt["backgroundColor"] = bg
        if bold: fmt.setdefault("textFormat", {})["bold"] = True
        return {"userEnteredValue": {"formulaValue": f"={formula}"},
                "userEnteredFormat": fmt}

    def sfdd(v, bold=False, italic=False, fg=None):
        fmt = {"backgroundColor": bg}
        tf = {}
        if bold:   tf["bold"] = True
        if italic: tf["italic"] = True
        if fg:     tf["foregroundColor"] = fg
        if tf:     fmt["textFormat"] = tf
        v = str(v or "")
        val = {"formulaValue": v} if v.startswith("=") else {"stringValue": v}
        return {"userEnteredValue": val, "userEnteredFormat": fmt}

    def row(label, c_fml, c_note, a_fml, a_note, b_fml, b_note, total=False):
        return [
            sfdd("", bold=total),
            sfdd(label, bold=total),
            mfdd(c_fml, bold=total) if c_fml else sfdd("", bold=total),
            sfdd(c_note or ""),
            mfdd(a_fml, bold=total) if a_fml else sfdd(""),
            sfdd(a_note or ""),
            mfdd(b_fml, bold=total) if b_fml else sfdd(""),
            sfdd(b_note or ""),
        ]

    p1_gross  = f"ROUND({pr}*{pa},0)"
    p2_gross  = f"ROUND({pr}*{pb},0)"
    p1_net    = f"ROUND({pr}*{pa},0)-{ar}"
    p2_net    = f"ROUND({pr}*{pb},0)-{ar}"
    p0_net    = br
    lcwa_fml  = f"{pr}*(1-{pa})-{sr}"
    lcwb_fml  = f"{pr}*(1-{pb})-{sr}"
    lcw0_fml  = f"{pr}-{br}-{sr}-{ar}"
    d_p1      = f"(ROUND({pr}*{pa},0)-{ar})-{br}"
    d_p2      = f"(ROUND({pr}*{pb},0)-{ar})-{br}"
    d_l1      = f"({pr}*(1-{pa})-{sr})-({lcw0_fml})"
    d_l2      = f"({pr}*(1-{pb})-{sr})-({lcw0_fml})"

    def delta_cell(fml):
        fmt = {"numberFormat": {"type": "NUMBER",
                                "pattern": '+ #,##0;(#,##0);"-"'},
               "textFormat": {"bold": True, "foregroundColor": DKGRAY},
               "backgroundColor": bg}
        return {"userEnteredValue": {"formulaValue": f"={fml}"},
                "userEnteredFormat": fmt}

    def total_row_with_delta(label, c_fml, a_fml, a_delta, b_fml, b_delta):
        def mc(fml):
            fmt = dict(MONEY)
            fmt["backgroundColor"] = bg
            fmt.setdefault("textFormat", {})["bold"] = True
            return {"userEnteredValue": {"formulaValue": f"={fml}"},
                    "userEnteredFormat": fmt}
        return [
            sfdd("", bold=True), sfdd(label, bold=True),
            mc(c_fml),  sfdd(""),
            mc(a_fml),  delta_cell(a_delta) if a_delta else sfdd(""),
            mc(b_fml),  delta_cell(b_delta) if b_delta else sfdd(""),
        ]

    # Sale price
    dd.append([
        sfdd(c["name"], bold=True), sfdd("Sale Price", bold=True),
        mfdd(pr, bold=True), sfdd(""),
        mfdd(pr, bold=True), sfdd(""),
        mfdd(pr, bold=True), sfdd(""),
    ])
    # Partner gross share row — blank for current (flat fee, not % based)
    pa_note = f'=TEXT({pa},"0%")&" x sale price"'
    pb_note = f'=TEXT({pb},"0%")&" x sale price"'
    dd.append([
        sfdd(""), sfdd("Partner gross share"),
        mfdd(br), sfdd("body fee (flat)"),
        mfdd(p1_gross), sfdd(pa_note),
        mfdd(p2_gross), sfdd(pb_note),
    ])
    # Deductions — current col shows what LCW used to pay/absorb
    dd.append(row("  less: assembly + shipping",
                  f"-{ar}", "LCW cost",
                  f"-{ar}", "Partner cost",
                  f"-{ar}", "Partner cost"))
    dd.append(row("  less: sled kit",
                  f"-{sr}", "LCW cost",
                  "0",      "LCW cost",
                  "0",      "LCW cost"))
    dd.append([sfdd(""), sfdd("─────────────")] + [sfdd("")]*6)
    dd.append(total_row_with_delta(
        "Partner net", p0_net, p1_net, d_p1, p2_net, d_p2))
    dd.append(total_row_with_delta(
        "LCW net", lcw0_fml, lcwa_fml, None, lcwb_fml, None))
    dd.append([sfdd("")]*8)

# ══════════════════════════════════════════════════════════════════════════════
# Create + format
# ══════════════════════════════════════════════════════════════════════════════
requests = [
    # Summary merges
    {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": 0, "endColumnIndex": 9}, "mergeType": "MERGE_ALL"}},
    {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 2,
                              "startColumnIndex": 0, "endColumnIndex": 9}, "mergeType": "MERGE_ALL"}},
    {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": notes_start+1, "endRowIndex": notes_start+2,
                              "startColumnIndex": 0, "endColumnIndex": 9}, "mergeType": "MERGE_ALL"}},
    {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": notes_start+2, "endRowIndex": notes_start+3,
                              "startColumnIndex": 0, "endColumnIndex": 9}, "mergeType": "MERGE_ALL"}},
    {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": notes_start+3, "endRowIndex": notes_start+4,
                              "startColumnIndex": 0, "endColumnIndex": 9}, "mergeType": "MERGE_ALL"}},
    # Drilldown header merges
    {"mergeCells": {"range": {"sheetId": 1, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": 2, "endColumnIndex": 4}, "mergeType": "MERGE_ALL"}},
    {"mergeCells": {"range": {"sheetId": 1, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": 4, "endColumnIndex": 6}, "mergeType": "MERGE_ALL"}},
    {"mergeCells": {"range": {"sheetId": 1, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": 6, "endColumnIndex": 8}, "mergeType": "MERGE_ALL"}},
]

# Column widths
for i, w in enumerate([180, 90, 110, 90, 110, 100, 90, 110, 100]):
    requests.append({"updateDimensionProperties": {
        "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": i, "endIndex": i+1},
        "properties": {"pixelSize": w}, "fields": "pixelSize"}})
for i, w in enumerate([180, 180, 90, 160, 90, 120, 90, 120]):
    requests.append({"updateDimensionProperties": {
        "range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": i, "endIndex": i+1},
        "properties": {"pixelSize": w}, "fields": "pixelSize"}})
for i, w in enumerate([220, 100, 280, 100, 110]):
    requests.append({"updateDimensionProperties": {
        "range": {"sheetId": 2, "dimension": "COLUMNS", "startIndex": i, "endIndex": i+1},
        "properties": {"pixelSize": w}, "fields": "pixelSize"}})

# Conditional formatting: delta cells green if positive, red if negative
# Summary col F (index 5) and I (index 8), rows 3 to 3+len(CLOCKS)
for col in [5, 8]:
    requests.append({"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": 0, "startRowIndex": 3, "endRowIndex": 3+len(CLOCKS),
                    "startColumnIndex": col, "endColumnIndex": col+1}],
        "booleanRule": {
            "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
            "format": {"textFormat": {"foregroundColor": POS}}
        }
    }, "index": 0}})
    requests.append({"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": 0, "startRowIndex": 3, "endRowIndex": 3+len(CLOCKS),
                    "startColumnIndex": col, "endColumnIndex": col+1}],
        "booleanRule": {
            "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
            "format": {"textFormat": {"foregroundColor": NEG}}
        }
    }, "index": 1}})

sheets.spreadsheets().batchUpdate(spreadsheetId=SS_ID,
                                  body={"requests": requests}).execute()

write(0, 0, summary)
write(1, 0, dd)
write(2, 0, assump)

# Share: anyone with link can view
drive.permissions().create(
    fileId=SS_ID,
    body={"role": "reader", "type": "anyone"}
).execute()

import urllib.request, urllib.parse
try:
    req = urllib.request.urlopen(
        f"https://is.gd/create.php?format=simple&url={urllib.parse.quote(URL, safe='')}",
        timeout=5
    )
    short_url = req.read().decode().strip()
    if not short_url.startswith("http"):
        raise ValueError(f"Unexpected response: {short_url}")
except Exception as e:
    print(f"   (URL shortener unavailable: {e})")
    short_url = URL

print(f"\n✓  {TITLE}")
print(f"   Scenario A: {PARTNER} {PCT_A}% / LCW {100-PCT_A}%")
print(f"   Scenario B: {PARTNER} {PCT_B}% / LCW {100-PCT_B}%")
print(f"\n   {short_url}")
print(f"   ({URL})\n")
