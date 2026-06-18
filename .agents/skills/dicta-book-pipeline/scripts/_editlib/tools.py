import re
from typing import List, Dict, Any

import gematriapy
from bs4 import BeautifulSoup


def _ensure_txt(file_path: str) -> None:
    if not file_path:
        raise ValueError("נא לבחור קובץ תחילה")
    if not file_path.lower().endswith(".txt"):
        raise ValueError("סוג הקובץ אינו נתמך. בחר קובץ טקסט [בסיומת TXT.]")


def add_page_number_to_heading(file_path: str, replace_with: str) -> Dict[str, Any]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.readlines()
    except FileNotFoundError:
        raise FileNotFoundError("הקובץ לא נמצא")

    changes_made = False
    updated_content: List[str] = []
    i = 0

    while i < len(content):
        line = content[i]
        match = re.match(r"<h([2-9])>(דף \S+)</h\1>", line)
        if match:
            level = match.group(1)
            title = match.group(2)
            next_line_index = i + 1
            if next_line_index < len(content):
                next_line = content[next_line_index].strip()
                pattern = r"(<[a-z]+>)?(ע[\"']+?[אב]|עמוד [אב])[.,:()\[\]'\"״׳]?(</[a-z]+>)?\s?"
                match_next_line = re.match(pattern, next_line)
                if match_next_line:
                    changes_made = True
                    if replace_with == "נקודה ונקודותיים":
                        if "א" in match_next_line.group(2):
                            new_title = f"<h{level}>{title.rstrip('.')}.</h{level}>\n"
                        else:
                            new_title = f"<h{level}>{title.rstrip('.')}:</h{level}>\n"
                    elif replace_with == "ע\"א וע\"ב":
                        suffix = "ע\"א" if "א" in match_next_line.group(2) else "ע\"ב"
                        new_title = f"<h{level}>{title.rstrip('.')} {suffix}</h{level}>\n"
                    else:
                        new_title = line
                    updated_content.append(new_title)
                    modified_next_line = re.sub(pattern, "", next_line, count=1).strip()
                    if modified_next_line != "":
                        updated_content.append(modified_next_line + "\n")
                    i += 1
                else:
                    updated_content.append(line)
            else:
                updated_content.append(line)
        else:
            updated_content.append(line)
        i += 1

    if changes_made:
        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(updated_content)
        return {"changed": True, "message": "ההחלפה הושלמה בהצלחה!"}
    return {"changed": False, "message": "אין מה להחליף בקובץ זה"}


def change_heading_level(file_path: str, current_level: str, new_level: str) -> Dict[str, Any]:
    _ensure_txt(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    current_tag = f"h{current_level}"
    new_tag = f"h{new_level}"
    updated_content = re.sub(
        f"<{current_tag}>(.*?)</{current_tag}>",
        f"<{new_tag}>\\1</{new_tag}>",
        content,
        flags=re.DOTALL
    )

    if content == updated_content:
        return {"changed": False, "message": "אין מה להחליף בקובץ זה"}

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(updated_content)
    return {"changed": True, "message": "רמות הכותרות עודכנו בהצלחה!"}


def _strip_html_tags(text: str, tags: List[str]) -> str:
    for tag in tags:
        text = text.replace(tag, "")
    return text


def _is_gematria(text: str, end: int, gematria_module=gematriapy) -> bool:
    remove = ["<b>", "</b>", "<big>", "</big>", ":", '"', ",", ";", "[", "]", "(", ")", "'", ".", "״", "‚"]
    aa = ["ק", "ר", "ש", "ת", "תק", "תר", "תש", "תת", "תתק", "יה", "יו", "קיה", "קיו", "ריה", "ריו", "שיה", "שיו", "תיה", "תיו", "תקיה", "תקיו", "תריה", "תריו", "תשיה", "תשיו", "תתיה", "תתיו", "תתקיה", "תתקיו"]
    bb = ["ם", "ן", "ץ", "ף", "ך"]
    cc = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "ששי", "שביעי", "שמיני", "תשיעי", "עשירי", "יוד", "למד", "נון", "דש", "חי", "טל", "שדמ", "ער", "שדם", "תשדם", "תשדמ", "ערב", "ערה", "עדר", "רחצ"]
    append_list = [i + ot_sofit for i in aa for ot_sofit in bb]
    for tage in remove:
        text = text.replace(tage, "")
    withaute_gershayim = [gematria_module.to_hebrew(i) for i in range(1, end)] + bb + cc + append_list + aa
    return text in withaute_gershayim


def create_headers(file_path: str, finde: str, end: int, level_num: int) -> Dict[str, Any]:
    _ensure_txt(file_path)
    found = False
    count_headings = 0
    html_tags = ["<b>", "</b>", "<big>", "</big>", ":", '"', ",", ";", "[", "]", "(", ")", "'", "״", ".", "‚"]
    finde_cleaned = _strip_html_tags(finde, html_tags).strip()

    with open(file_path, "r", encoding="utf-8") as file_input:
        content = file_input.read().splitlines()
        all_lines = content[0:2]
        i = 2
        while i < len(content):
            line = content[i]
            words = line.split()
            try:
                if len(words) >= 2 and _strip_html_tags(words[0], html_tags) == finde_cleaned and _is_gematria(_strip_html_tags(words[1], html_tags), end + 1):
                    found = True
                    count_headings += 1
                    heading_line = f"<h{level_num}>{_strip_html_tags(words[0], html_tags)} {_strip_html_tags(words[1], html_tags)}</h{level_num}>"
                    all_lines.append(heading_line)
                    if words[2:]:
                        all_lines.append(" ".join(words[2:]))
                elif len(words) == 1 and _strip_html_tags(words[0], html_tags) == finde_cleaned and i + 1 < len(content):
                    next_line = content[i + 1]
                    next_words = next_line.split()
                    if len(next_words) >= 1 and _is_gematria(_strip_html_tags(next_words[0], html_tags), end + 1):
                        found = True
                        count_headings += 1
                        heading_line = f"<h{level_num}>{_strip_html_tags(words[0], html_tags)} {_strip_html_tags(next_words[0], html_tags)}</h{level_num}>"
                        all_lines.append(heading_line)
                        if next_words[1:]:
                            all_lines.append(" ".join(next_words[1:]))
                        i += 1
                    else:
                        all_lines.append(line)
                else:
                    all_lines.append(line)
            except IndexError:
                all_lines.append(line)
            i += 1

    with open(file_path, "w", encoding="utf-8") as output_file:
        output_file.write("\n".join(all_lines))

    if finde == "דף":
        add_page_number_to_heading(file_path, "נקודה ונקודותיים")

    return {"found": found, "count": count_headings}


def create_single_letter_headers(
    file_path: str,
    end_suffix: str,
    end: int,
    level_num: int,
    ignore: List[str],
    start: str,
    remove: List[str],
    bold_only: bool
) -> Dict[str, Any]:
    _ensure_txt(file_path)
    count = 0

    if bold_only:
        end_suffix += "</b>"
        start = "<b>" + start
    else:
        ignore = ignore + ["<b>", "</b>"]

    def strip_html(text: str, ignore_tags: List[str]) -> str:
        for tag in ignore_tags:
            text = text.replace(tag, "")
        return text

    with open(file_path, "r", encoding="utf-8") as file_input:
        content = file_input.read().splitlines()
        all_lines = content[0:1]
        for line in content[1:]:
            words = line.split()
            try:
                if strip_html(words[0], ignore).endswith(end_suffix) and _is_gematria(words[0], end + 1) and strip_html(words[0], ignore).startswith(start):
                    heading_line = f"<h{level_num}>{strip_html(words[0], remove)}</h{level_num}>"
                    all_lines.append(heading_line)
                    if words[1:]:
                        all_lines.append(" ".join(words[1:]))
                    count += 1
                else:
                    all_lines.append(line)
            except IndexError:
                all_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as output_file:
        output_file.write("\n".join(all_lines))

    return {"count": count}


def create_page_b_headers(file_path: str, header_level: int) -> Dict[str, Any]:
    _ensure_txt(file_path)

    def build_tag_agnostic_pattern(word, optional_end_chars="['\"']*"):
        any_tags = r"(?:<[^>]+>\s*)*"
        pattern = "".join(any_tags + re.escape(char) for char in word) + any_tags
        if optional_end_chars:
            pattern += optional_end_chars + any_tags
        return pattern

    def strip_and_replace(text, header_level, counter):
        any_tags = r"(?:<[^>]+>\s*)*"
        non_word = r"(?:[^\w<>]|$)"
        pattern = r"^\s*" + any_tags

        shem_pattern = build_tag_agnostic_pattern("שם", optional_end_chars="")
        pattern += r"(?P<shem>" + shem_pattern + r"\s*)?"

        gmarah_variants = ["גמרא", "בגמרא", "גמ'", "בגמ'"]
        gmarah_patterns = [build_tag_agnostic_pattern(word, optional_end_chars="") for word in gmarah_variants]
        gmarah_pattern = r"(?P<gmarah>" + "|".join(gmarah_patterns) + r")\s*"
        pattern += r"(?:" + gmarah_pattern + r")?"

        ab_variants = ["עמוד ב", "ע\"ב", "ע''ב", "ע'ב"]
        ab_patterns = [r"(?<!\w)" + build_tag_agnostic_pattern(word) + r"(?!\w)" for word in ab_variants]
        ab_pattern = r"(?P<ab>" + "|".join(ab_patterns) + r")"

        pattern += ab_pattern + non_word + r"(?P<rest>.*)"
        match_pattern = re.compile(pattern, re.IGNORECASE | re.UNICODE)

        def replace_function(match):
            header = f"<h{header_level}>עמוד ב</h{header_level}>"
            rest_of_line = match.group("rest").lstrip()
            gmarah_text = match.group("gmarah")
            if gmarah_text:
                gmarah_text = re.sub(any_tags, "", gmarah_text).strip()
            counter[0] += 1
            if gmarah_text:
                return f"{header}\n{gmarah_text} {rest_of_line}\n" if rest_of_line else f"{header}\n{gmarah_text}\n"
            return f"{header}\n{rest_of_line}\n" if rest_of_line else f"{header}\n"

        if re.search(r"<h\d>.*?</h\d>", text, re.IGNORECASE):
            return text
        new_text = match_pattern.sub(replace_function, text)
        new_text = re.sub(r"\n\s*\n", "\n", new_text)
        return new_text

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    new_lines = []
    counter = [0]
    for line in lines:
        new_lines.append(strip_and_replace(line, header_level, counter))

    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(new_lines)

    return {"count": counter[0]}


def replace_page_b_headers(file_path: str, replace_type: str) -> Dict[str, Any]:
    _ensure_txt(file_path)

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    previous_title = ""
    previous_level = ""
    replacements_made = 0

    def replace_match(match):
        nonlocal previous_title, previous_level, replacements_made
        level = match.group(1)
        title = match.group(2)
        if re.match(r"דף \S+\.?", title):
            previous_title = title.strip()
            previous_level = level
            return match.group(0)
        if title == "עמוד ב":
            replacements_made += 1
            if replace_type == "נקודותיים":
                return f"<h{previous_level}>{previous_title.rstrip('.')}:</h{previous_level}>"
            if replace_type == "ע\"ב":
                modified_title = re.sub(r"( ע\"א| עמוד א)", "", previous_title)
                return f"<h{previous_level}>{modified_title.rstrip('.')} ע\"ב</h{previous_level}>"
        return match.group(0)

    content = re.sub(r"<h([1-9])>(.*?)</h\1>", replace_match, content)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

    return {"count": replacements_made}


def emphasize_and_punctuate(file_path: str, add_ending: str, emphasize_start: bool) -> Dict[str, Any]:
    _ensure_txt(file_path)

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    changed = False
    for i in range(len(lines)):
        line = lines[i].rstrip("\n")
        words = line.split()
        if len(words) > 10 and not any(line.startswith(f"<h{n}>") for n in range(2, 10)):
            if add_ending != "ללא שינוי":
                if line.endswith(","):
                    line = line.rstrip(", ")
                    line += "." if add_ending == "הוסף נקודה" else ":"
                    changed = True
                elif not line.endswith((".", ":", "!", "?")) and not any(line.endswith(tag) for tag in ["</small>", "</big>", "</b>"]):
                    line += "." if add_ending == "הוסף נקודה" else ":"
                    changed = True
            if emphasize_start:
                first_word = words[0]
                if not any(tag in first_word for tag in ["<b>", "<small>", "<big>", "<h2>", "<h3>", "<h4>", "<h5>", "<h6>"]):
                    if not (first_word.startswith("<") and first_word.endswith(">")):
                        line = "<b>" + first_word + "</b> " + " ".join(words[1:])
                        changed = True
            lines[i] = line + "\n"

    if changed:
        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(lines)

    return {"changed": changed}


def text_cleaner(file_path: str, options: Dict[str, bool]) -> Dict[str, Any]:
    _ensure_txt(file_path)

    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    original = text
    if options.get("remove_empty_lines", False):
        text = re.sub(r"\n\s*\n", "\n", text)
    if options.get("remove_double_spaces", False):
        text = re.sub(r" +", " ", text)
    if options.get("remove_spaces_before", False):
        text = re.sub(r"[ \t]+([\)\],.:])", r"\1", text)
    if options.get("remove_spaces_after", False):
        text = re.sub(r"(\s|^)([\[\(])(\s+)", r"\1\2", text, flags=re.MULTILINE)
    if options.get("remove_spaces_around_newlines", False):
        text = re.sub(r"\s*\n\s*", "\n", text)
    if options.get("replace_double_quotes", False):
        text = text.replace("''", '"').replace("``", '"').replace("’’", '"').replace("׳׳", '"').replace("‘‘", '"')
    if options.get("normalize_quotes", False):
        text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("„", '"').replace("׳", "'").replace("`", "'")

    text = text.rstrip()
    if text == original:
        return {"changed": False}

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)

    return {"changed": True}


def header_error_checker(file_path: str, re_start: str, re_end: str, gershayim: bool, is_shas: bool) -> Dict[str, Any]:
    _ensure_txt(file_path)

    with open(file_path, "r", encoding="utf-8") as file:
        html_content = file.read()
        lines = html_content.splitlines()

    opening_without_closing_list = []
    closing_without_opening_list = []
    heading_errors_list = []

    def check_tags(line, line_number):
        all_tags = []
        for match in re.finditer(r"<(/?\w+)>", line):
            tag = match.group(1)
            position = match.start()
            if tag.startswith("/"):
                all_tags.append(("close", tag[1:], position))
            else:
                all_tags.append(("open", tag, position))
        all_tags.sort(key=lambda x: x[2])
        open_stack = []
        for tag_type, tag_name, _ in all_tags:
            if tag_type == "open":
                open_stack.append(tag_name)
            else:
                found = False
                for i in range(len(open_stack) - 1, -1, -1):
                    if open_stack[i] == tag_name:
                        open_stack.pop(i)
                        found = True
                        break
                if not found:
                    closing_without_opening_list.append(f"שורה {line_number}: </{tag_name}> || {line.strip()}")
        for tag in open_stack:
            opening_without_closing_list.append(f"שורה {line_number}: <{tag}> || {line.strip()}")

    def check_heading_errors(line, line_number):
        for tag in ["h2", "h3", "h4", "h5", "h6"]:
            heading_pattern = rf"<{tag}>.*?</{tag}>"
            heading_match = re.search(heading_pattern, line)
            if heading_match:
                start, end = heading_match.span()
                before = line[:start].strip()
                after = line[end:].strip()
                if before or after:
                    heading_errors_list.append(f"שורה {line_number}: {line.strip()}")

    for line_number, line in enumerate(lines, start=1):
        check_tags(line, line_number)
        check_heading_errors(line, line_number)

    soup = BeautifulSoup(html_content, "html.parser")
    if re_start and re_end:
        pattern = re.compile(rf"^[{re.escape(re_start)}]*[א-ת]([א-ת \-]*[א-ת])?[{re.escape(re_end)}]*$")
    elif re_start:
        pattern = re.compile(rf"^[{re.escape(re_start)}]*[א-ת]([א-ת \-]*[א-ת])?$")
    elif re_end:
        pattern = re.compile(rf"^[א-ת]([א-ת \-]*[א-ת])?[{re.escape(re_end)}]*$")
    else:
        pattern = re.compile(r"^[א-ת]([א-ת \-]*[א-ת])?$")

    unmatched_regex = []
    unmatched_tags = []
    missing_levels = []
    for i in range(2, 7):
        tags = soup.find_all(f"h{i}")
        if not tags:
            missing_levels.append(i)
            continue
        step = 2 if is_shas else 1
        for index in range(0, len(tags) - step, step):
            current_tag = tags[index].string or ""
            next_tag = tags[index + step].string or ""
            if not current_tag or not next_tag:
                continue
            current_heading_parts = current_tag.split()
            next_heading_parts = next_tag.split()
            current_heading = current_heading_parts[1] if len(current_heading_parts) > 1 else current_tag
            next_heading = next_heading_parts[1] if len(next_heading_parts) > 1 else next_tag
            if not re.match(pattern, current_tag):
                if not (gershayim and ("'" in current_tag or '"' in current_tag)):
                    unmatched_regex.append(current_tag)
            if "'" in current_heading or '"' in current_heading:
                unmatched_tags.append(current_heading)
            if not gematriapy.to_number(current_heading) + step == gematriapy.to_number(next_heading):
                unmatched_tags.append(f"כותרת נוכחית - {current_tag} || כותרת הבאה - {next_tag}")

    return {
        "unmatched_regex": unmatched_regex,
        "unmatched_tags": unmatched_tags,
        "opening_without_closing": opening_without_closing_list,
        "closing_without_opening": closing_without_opening_list,
        "heading_errors": heading_errors_list,
        "missing_levels": missing_levels,
    }
