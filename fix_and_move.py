import os
import re
import shutil
import glob

def fix_bolding(content):
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if line.startswith('<b>') or line.startswith('+<b>'):
            # Merge consecutive <b> tags
            line = re.sub(r'</b>\s+<b>', ' ', line)
            
            # If line has ד"ה and a period/colon, extend <b> to cover up to the period/colon
            # Example: <b>תוספות</b> ד"ה משהו. -> <b>תוספות ד"ה משהו.</b>
            # Example: <b>ד"ה</b> משהו: -> <b>ד"ה משהו:</b>
            
            # Find the first closing tag
            match = re.search(r'^(<b>.*?</b>)\s*(ד"ה.*?(?:\.|\:))(.*)', line)
            if match:
                first_part = match.group(1).replace('<b>', '').replace('</b>', '')
                dh_part = match.group(2)
                rest = match.group(3)
                line = f"<b>{first_part} {dh_part}</b>{rest}"
            else:
                # If it starts with <b>ד"ה</b>
                match2 = re.search(r'^<b>(ד"ה)</b>(.*?)([\.\:])(.*)', line)
                if match2:
                    dh = match2.group(1)
                    text = match2.group(2)
                    sep = match2.group(3)
                    rest = match2.group(4)
                    line = f"<b>{dh}{text}{sep}</b>{rest}"
                
        new_lines.append(line)
    return '\n'.join(new_lines)

def main():
    root_dir = r"c:\Users\user\DictaToOtzaria"
    unedited_dir = os.path.join(root_dir, "לא ערוך", "ספרים", "אוצריא")
    
    # Map filename to its target directory in "לא ערוך"
    file_to_target_dir = {}
    for dirpath, dirnames, filenames in os.walk(unedited_dir):
        for f in filenames:
            if f.endswith('.txt'):
                # Build target directory equivalent (but relative to something, or just save the relative dirpath)
                rel_path = os.path.relpath(dirpath, unedited_dir)
                file_to_target_dir[f] = rel_path

    # Iterate over txt files in root directory
    txt_files = glob.glob(os.path.join(root_dir, "*.txt"))
    
    files_moved = 0
    
    for txt_file in txt_files:
        filename = os.path.basename(txt_file)
        if filename in file_to_target_dir:
            # We found a match
            target_rel_path = file_to_target_dir[filename]
            target_dir = os.path.join(root_dir, target_rel_path)
            
            # Create target directory if it doesn't exist
            os.makedirs(target_dir, exist_ok=True)
            
            # Read, fix, and write
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            fixed_content = fix_bolding(content)
            
            target_file_path = os.path.join(target_dir, filename)
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
                
            # Remove original file
            os.remove(txt_file)
            files_moved += 1
            print(f"Moved and fixed: {filename} -> {target_rel_path}")

    print(f"\nTotal files moved and fixed: {files_moved}")

if __name__ == "__main__":
    main()
