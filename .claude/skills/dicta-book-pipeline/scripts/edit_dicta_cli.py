#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""edit_dicta_cli.py — עטיפת CLI סביב src/services/tools.py.

נועד לשימוש ע"י הסקיל dicta-book-pipeline (Stage 3.5 ו‑Stage 6).
כל תת‑פקודה מקבלת ``--file`` ותומכת ב‑``--json`` לפלט מכונה.

תת‑פקודות (עוטפות 1:1 את הכלים שבני אדם משתמשים בהם באפליקציית EditingDictaBooks):
  clean-text                    ניקוי טקסט (נרמול גרשיים, רווחים כפולים, שורות ריקות)
  emphasize-first               הדגשת מילה ראשונה + פיסוק סוף קטע
  create-headers                יצירת כותרות מתבנית "<מילה> <גימטריה>" (דף ב, פרק ג)
  create-single-letter-headers  יצירת כותרות מאות/מילה בודדת (סימן א)
  create-page-b-headers         יצירת כותרת "עמוד ב" מסמן ע"ב מוטבע
  page-number                   נרמול כותרת "דף" לפי הסמן בשורה הבאה (סגנון . / :)
  replace-page-b                המרת כותרת "עמוד ב" לעמוד ב של הדף הקודם (. / :)
  change-heading-level          המרת רמת כל הכותרות מ‑hN ל‑hM
  validate-tags                 בדיקת איזון תגים בלבד (פותח/סוגר)
  validate-otzaria              גייט מוסכמות אוצריא המלא (קוד יציאה 0=עבר, 1=הפרה קשה, 2=שגיאה)

קודי יציאה: 0 = הצלחה/עבר, 1 = הפרת מוסכמה קשה (validate-otzaria בלבד), 2 = שגיאת ריצה.
"""

import argparse
import json
import os
import re
import sys

# אכיפת UTF-8 על הפלט — קונסולת Windows עלולה לברירת‑מחדל ל‑cp1255 ולשבש עברית.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# לוגיקת העריכה מוטמעת בתוך הסקיל — אפס תלות במאגרים חיצוניים או ב‑venv.
# `_editlib/tools.py` הוא עותק של src/services/tools.py מהמאגר EditingDictaBooks_USERBOT;
# הוסרו ממנו אך ורק שורות ה‑import המיותרות (requests, PyPDF2, dotenv + load_dotenv())
# שאינן בשימוש אף פונקציה שה‑CLI קורא לה — לוגיקת הפונקציות עצמן לא נגעה.
# ספריות הצד‑שלישי הנחוצות בלבד מוטמעות תחת `_editlib/vendor/` (gematriapy, bs4).
_HERE = os.path.abspath(os.path.dirname(__file__))
_LIB = os.path.join(_HERE, "_editlib")
_VENDOR = os.path.join(_LIB, "vendor")
for _p in (_VENDOR, _LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# soupsieve אינו מוטמע (נחוץ רק ל‑CSS selectors של bs4, שאינם בשימוש). bs4 עובד
# בלעדיו אך פולט אזהרה קוסמטית בעת ה‑import — משתיקים אותה כדי לשמור על פלט נקי.
import warnings  # noqa: E402
warnings.filterwarnings("ignore", message=r".*soupsieve.*")

try:
    import tools  # noqa: E402  — העתק מדויק של src/services/tools.py
except ImportError as _ex:  # noqa: BLE001
    sys.stderr.write(
        "שגיאה: לא נמצאה לוגיקת העריכה המוטמעת (_editlib/tools.py).\n"
        f"פרטים: {_ex}\n"
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# עזרי פלט
# ---------------------------------------------------------------------------

def _emit(payload, as_json):
    """פלט אחיד: JSON אם ביקשו, אחרת סיכום עברי קצר."""
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        msg = payload.get("message")
        if msg:
            print(msg)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))


def _read_lines(file_path):
    with open(file_path, "r", encoding="utf-8") as fh:
        return fh.read().splitlines()


# ---------------------------------------------------------------------------
# תת‑פקודות עיבוד (כתיבה לקובץ)
# ---------------------------------------------------------------------------

_CLEAN_DEFAULTS = {
    "remove_empty_lines": True,
    "remove_double_spaces": True,
    "replace_double_quotes": True,
    "normalize_quotes": True,
    "remove_spaces_before": False,
    "remove_spaces_after": False,
    "remove_spaces_around_newlines": False,
}


def cmd_clean_text(args):
    options = dict(_CLEAN_DEFAULTS)
    if args.all:
        options = {k: True for k in options}
    for opt in (args.enable or []):
        options[opt] = True
    for opt in (args.disable or []):
        options[opt] = False
    res = tools.text_cleaner(args.file, options)
    res.setdefault("message", "הקובץ נוקה" if res.get("changed") else "אין מה לנקות")
    res["options"] = options
    _emit(res, args.json)
    return 0


def cmd_emphasize_first(args):
    ending_map = {"colon": "הוסף נקודותיים", "dot": "הוסף נקודה", "none": "ללא שינוי"}
    res = tools.emphasize_and_punctuate(
        args.file,
        add_ending=ending_map[args.ending],
        emphasize_start=not args.no_emphasize,
    )
    res.setdefault("message", "הודגשו מילים ראשונות" if res.get("changed") else "אין שינוי")
    _emit(res, args.json)
    return 0


def cmd_page_number(args):
    style_map = {"dot-colon": "נקודה ונקודותיים", "ab": "ע\"א וע\"ב"}
    res = tools.add_page_number_to_heading(args.file, style_map[args.style])
    res.setdefault("message", res.get("message", ""))
    _emit(res, args.json)
    return 0


def cmd_replace_page_b(args):
    type_map = {"colon": "נקודותיים", "ab": "ע\"ב"}
    res = tools.replace_page_b_headers(args.file, type_map[args.type])
    res.setdefault("message", f"הומרו {res.get('count', 0)} כותרות 'עמוד ב'")
    _emit(res, args.json)
    return 0


def cmd_create_headers(args):
    res = tools.create_headers(args.file, args.find, args.end, args.level)
    res.setdefault("message",
                   f"נוצרו {res.get('count', 0)} כותרות" if res.get("found")
                   else "לא נמצא מה להפוך לכותרת")
    _emit(res, args.json)
    return 0


# ברירות המחדל של create-single-letter-headers, זהות ל‑GUI (frontend/web/app.js)
_SLH_IGNORE_DEFAULT = ["<big>", "</big>", "<i>", "</i>", "</small>", "</small>",
                       "<span>", "</span>", "<br>", "</br>", "<p>", "</p>"]
_SLH_REMOVE_DEFAULT = ["<b>", "</b>", "<big>", "</big>", "<i>", "</i>", "</small>",
                       "</small>", "<span>", "</span>", "<br>", "</br>", "<p>", "</p>",
                       ",", ":", '"', "'", ".", "(", ")", "[", "]", "{", "}"]


def cmd_create_single_letter_headers(args):
    res = tools.create_single_letter_headers(
        args.file,
        end_suffix=args.end_suffix,
        end=args.max,
        level_num=args.level,
        ignore=args.ignore if args.ignore is not None else list(_SLH_IGNORE_DEFAULT),
        start=args.start,
        remove=args.remove if args.remove is not None else list(_SLH_REMOVE_DEFAULT),
        bold_only=not args.no_bold_only,
    )
    res.setdefault("message", f"נוצרו {res.get('count', 0)} כותרות")
    _emit(res, args.json)
    return 0


def cmd_create_page_b(args):
    res = tools.create_page_b_headers(args.file, args.level)
    res.setdefault("message", f"נוצרו {res.get('count', 0)} כותרות 'עמוד ב'")
    _emit(res, args.json)
    return 0


def cmd_change_heading_level(args):
    res = tools.change_heading_level(args.file, str(args.from_level), str(args.to_level))
    res.setdefault("message", res.get("message", ""))
    _emit(res, args.json)
    return 0


# ---------------------------------------------------------------------------
# בדיקות (קריאה בלבד)
# ---------------------------------------------------------------------------

def _run_header_checker(file_path, is_shas):
    """קורא ל‑header_error_checker בצורה עמידה לשגיאות (gematriapy עלול להיכשל)."""
    try:
        return tools.header_error_checker(
            file_path, re_start="", re_end="", gershayim=True, is_shas=is_shas
        ), None
    except Exception as ex:  # noqa: BLE001 — אסור שהגייט יקרוס בגלל כותרת חריגה
        return None, f"{type(ex).__name__}: {ex}"


def cmd_validate_tags(args):
    checker, err = _run_header_checker(args.file, args.shas)
    if err is not None:
        _emit({"error": err}, args.json)
        return 2
    payload = {
        "opening_without_closing": checker["opening_without_closing"],
        "closing_without_opening": checker["closing_without_opening"],
    }
    bad = bool(payload["opening_without_closing"] or payload["closing_without_opening"])
    payload["ok"] = not bad
    payload["message"] = "כל התגים מאוזנים" if not bad else "נמצאו תגים לא מאוזנים"
    _emit(payload, args.json)
    return 1 if bad else 0


# --- בדיקות מוסכמות נוספות עבור validate-otzaria -------------------------------

_GERSHAYIM_CHARS = ['"', "”", "“", "’", "‘", "״", "׳"]
_COLOPHON_RE = re.compile(r"(תם ונשלם|סליק|נשלמה?\b)")
_H1_RE = re.compile(r"<h1>(.*?)</h1>")
_HEADING_RE = re.compile(r"<h([1-6])>(.*?)</h\1>")
_DAF_HEADING_RE = re.compile(r"<h([2-6])>\s*דף\b(.*?)</h\1>")


def _check_h1_gershayim(lines):
    hits = []
    for n, line in enumerate(lines, 1):
        for m in _H1_RE.finditer(line):
            inner = m.group(1)
            if any(ch in inner for ch in _GERSHAYIM_CHARS):
                hits.append(f"שורה {n}: {line.strip()}")
    return hits


def _check_big_in_heading(lines):
    hits = []
    for n, line in enumerate(lines, 1):
        if re.search(r"<h[1-6]>.*<big>", line):
            hits.append(f"שורה {n}: {line.strip()}")
    return hits


def _check_decorative_big(lines):
    """שורת <big>...</big> בודדת שאינה קולופון סיום."""
    hits = []
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        m = re.fullmatch(r"<big>(.*?)</big>", stripped)
        if m and not _COLOPHON_RE.search(m.group(1)):
            hits.append(f"שורה {n}: {stripped}")
    return hits


def _check_multi_masechta(lines):
    """מספר מסכתות בקובץ אחד — אסור (מוסכמה §3).

    סימן: יותר מ‑<h1> אחד, או קולופון 'תם ונשלם'/'סליק' שאחריו עוד כותרת.
    """
    h1_lines = [f"שורה {n}: {line.strip()}"
                for n, line in enumerate(lines, 1) if "<h1>" in line]
    signals = list(h1_lines)
    violation = len(h1_lines) > 1

    colophon_idx = [n for n, line in enumerate(lines) if _COLOPHON_RE.search(line)]
    for idx in colophon_idx:
        # האם אחרי הקולופון מופיעה עוד כותרת h1/h2 (מסכת חדשה)?
        for later in lines[idx + 1:]:
            if re.search(r"<h[12]>", later):
                violation = True
                signals.append(f"שורה {idx + 1}: קולופון ואחריו כותרת חדשה — {lines[idx].strip()}")
                break
    return {"violation": violation, "signals": signals}


def _check_daf_format(lines):
    """advisory: כותרת 'דף' בלי סיומת . או : (מוסכמה §4)."""
    hits = []
    for n, line in enumerate(lines, 1):
        m = _DAF_HEADING_RE.search(line)
        if m:
            inner = ("דף" + m.group(2)).strip()
            if not (inner.endswith(".") or inner.endswith(":")):
                hits.append(f"שורה {n}: {line.strip()}")
    return hits


def cmd_validate_otzaria(args):
    try:
        lines = _read_lines(args.file)
    except FileNotFoundError:
        _emit({"error": "הקובץ לא נמצא"}, args.json)
        return 2

    checker, checker_err = _run_header_checker(args.file, args.shas)

    multi = _check_multi_masechta(lines)
    report = {
        "file": args.file,
        "shas": args.shas,
        # --- הפרות קשות (מכשילות exit) ---
        "multi_masechta": multi["signals"] if multi["violation"] else [],
        "h1_gershayim": _check_h1_gershayim(lines),
        "big_in_heading": _check_big_in_heading(lines),
        "decorative_big": _check_decorative_big(lines),
        "opening_without_closing": checker["opening_without_closing"] if checker else [],
        "closing_without_opening": checker["closing_without_opening"] if checker else [],
        "heading_errors": checker["heading_errors"] if checker else [],
        # --- advisory (לא מכשילות) ---
        "advisory_daf_format": _check_daf_format(lines),
        "advisory_heading_sequence": checker["unmatched_tags"] if checker else [],
    }
    if checker_err is not None:
        report["checker_error"] = checker_err

    hard_keys = [
        "multi_masechta", "h1_gershayim", "big_in_heading", "decorative_big",
        "opening_without_closing", "closing_without_opening", "heading_errors",
    ]
    hard_hits = {k: report[k] for k in hard_keys if report[k]}
    passed = not hard_hits
    report["passed"] = passed
    report["hard_violations"] = sorted(hard_hits.keys())

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if passed:
            print("✅ עבר את גייט המוסכמות (exit=0)")
        else:
            print("❌ נמצאו הפרות קשות:")
            for k in report["hard_violations"]:
                print(f"  • {k}: {len(report[k])} מופעים")
        adv = report["advisory_daf_format"] or report["advisory_heading_sequence"]
        if adv:
            print(f"⚠ advisory: {len(report['advisory_daf_format'])} כותרות דף ללא סיומת, "
                  f"{len(report['advisory_heading_sequence'])} חריגות רצף.")
        if checker_err:
            print(f"⚠ בדיקת הכותרות חלקית: {checker_err}")

    return 0 if passed else 1


# ---------------------------------------------------------------------------
# פרסר
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="edit_dicta_cli.py",
        description="CLI לעריכת ספרי דיקטה (עוטף src/services/tools.py)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp):
        sp.add_argument("--file", required=True, help="נתיב לקובץ TXT")
        sp.add_argument("--json", action="store_true", help="פלט JSON למכונה")

    sp = sub.add_parser("clean-text", help="ניקוי טקסט")
    add_common(sp)
    sp.add_argument("--all", action="store_true", help="הפעל את כל אפשרויות הניקוי")
    sp.add_argument("--enable", nargs="*", choices=list(_CLEAN_DEFAULTS),
                    help="הפעל אפשרויות ספציפיות")
    sp.add_argument("--disable", nargs="*", choices=list(_CLEAN_DEFAULTS),
                    help="כבה אפשרויות ספציפיות")
    sp.set_defaults(func=cmd_clean_text)

    sp = sub.add_parser("emphasize-first", help="הדגשת מילה ראשונה + פיסוק")
    add_common(sp)
    sp.add_argument("--ending", choices=["colon", "dot", "none"], default="colon",
                    help="פיסוק סוף קטע (ברירת מחדל: נקודותיים)")
    sp.add_argument("--no-emphasize", action="store_true",
                    help="אל תדגיש מילה ראשונה, רק פיסוק")
    sp.set_defaults(func=cmd_emphasize_first)

    sp = sub.add_parser("page-number", help="נרמול כותרת 'דף'")
    add_common(sp)
    sp.add_argument("--style", choices=["dot-colon", "ab"], default="dot-colon",
                    help="dot-colon = . / :  |  ab = ע\"א / ע\"ב")
    sp.set_defaults(func=cmd_page_number)

    sp = sub.add_parser("replace-page-b", help="המרת 'עמוד ב' לעמוד ב של הדף הקודם")
    add_common(sp)
    sp.add_argument("--type", choices=["colon", "ab"], default="colon",
                    help="colon = :  |  ab = ע\"ב")
    sp.set_defaults(func=cmd_replace_page_b)

    sp = sub.add_parser("create-headers",
                        help="יצירת כותרות מתבנית '<מילה> <גימטריה>' (למשל 'דף ב', 'פרק ג')")
    add_common(sp)
    sp.add_argument("--find", default="דף",
                    help="המילה שפותחת את הכותרת (ברירת מחדל: דף)")
    sp.add_argument("--end", type=int, default=999,
                    help="הגימטריה המקסימלית לזיהוי (ברירת מחדל: 999)")
    sp.add_argument("--level", type=int, default=2,
                    help="רמת הכותרת ליצירה (ברירת מחדל: 2)")
    sp.set_defaults(func=cmd_create_headers)

    sp = sub.add_parser("create-single-letter-headers",
                        help="יצירת כותרות מאות/מילה בודדת (למשל 'סימן א')")
    add_common(sp)
    sp.add_argument("--end-suffix", default="",
                    help="סיומת שהמילה חייבת להסתיים בה (למשל גרש)")
    sp.add_argument("--max", type=int, default=999,
                    help="הגימטריה המקסימלית (ברירת מחדל: 999)")
    sp.add_argument("--level", type=int, default=3,
                    help="רמת הכותרת (ברירת מחדל: 3)")
    sp.add_argument("--start", default="",
                    help="קידומת שהמילה חייבת להתחיל בה")
    sp.add_argument("--ignore", nargs="*", default=None,
                    help="תגים להתעלם מהם בזיהוי (ברירת מחדל כמו ב‑GUI)")
    sp.add_argument("--remove", nargs="*", default=None,
                    help="תווים/תגים להסיר מטקסט הכותרת (ברירת מחדל כמו ב‑GUI)")
    sp.add_argument("--no-bold-only", action="store_true",
                    help="חפש גם מילים שאינן מודגשות (ברירת מחדל: מודגשות בלבד)")
    sp.set_defaults(func=cmd_create_single_letter_headers)

    sp = sub.add_parser("create-page-b-headers",
                        help="יצירת כותרת 'עמוד ב' מתוך סמן ע\"ב/עמוד ב מוטבע בטקסט")
    add_common(sp)
    sp.add_argument("--level", type=int, default=3,
                    help="רמת הכותרת (ברירת מחדל: 3)")
    sp.set_defaults(func=cmd_create_page_b)

    sp = sub.add_parser("change-heading-level", help="המרת רמת כל הכותרות מ‑hN ל‑hM")
    add_common(sp)
    sp.add_argument("--from", dest="from_level", type=int, required=True,
                    help="רמת המקור (למשל 2)")
    sp.add_argument("--to", dest="to_level", type=int, required=True,
                    help="רמת היעד (למשל 3)")
    sp.set_defaults(func=cmd_change_heading_level)

    sp = sub.add_parser("validate-tags", help="בדיקת איזון תגים")
    add_common(sp)
    sp.add_argument("--shas", action="store_true", help="ספר ש\"ס (עמוד ב כפול)")
    sp.set_defaults(func=cmd_validate_tags)

    sp = sub.add_parser("validate-otzaria", help="גייט מוסכמות אוצריא המלא")
    add_common(sp)
    sp.add_argument("--shas", action="store_true", help="ספר ש\"ס (עמוד ב כפול)")
    sp.set_defaults(func=cmd_validate_otzaria)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as ex:
        payload = {"error": str(ex)}
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"שגיאה: {ex}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
