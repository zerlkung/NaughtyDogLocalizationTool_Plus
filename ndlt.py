#!/usr/bin/env python3
"""
Naughty Dog Localization Tool (Python)
Export/Import localization files for Naughty Dog games.
Supports: Uncharted (ALL), Last of Us (ALL)
Platforms: PS3 (v0), PS4 (v1), PS5/PC (v2)

Usage:
  python ndlt.py <localization file>    Export binary to .txt + .ids
  python ndlt.py <exported txt file>    Import .txt back to binary
  python ndlt.py <folder>               Process all files in folder (recursive)
  Drop file/folder onto ndlt.py/.exe    Same as CLI
"""

import sys
import os
import struct
from pathlib import Path

UNKNOWN_STRING = b"UNKNOWN STRING!!!\0"
LOCALIZATION_EXTENSIONS = {'.subtitles', '.common', '.subtitles-systemic', '.web'}
# Compound suffixes for game-prefixed files (e.g. 2.tll-subtitles, 1.uncharted-common)
LOCALIZATION_SUFFIXES = {'-subtitles', '-common', '-subtitles-systemic', '-web'}
SUPPORTED_GAMES = ["Uncharted (ALL Games)", "Last Of Us (ALL Games)"]


# ═══════════════════════════════════════════════════════════════
# String helpers
# ═══════════════════════════════════════════════════════════════

def string_clear(s: str) -> str:
    """Encode special characters for safe text file storage."""
    s = s.replace('\r\n', '<cf>')
    s = s.replace('\r', '<cr>')
    s = s.replace('\n', '<lf>')
    if s == '':
        s = '[EmptyString]'
    return s


def string_declear(s: str) -> str:
    """Decode special markers back to original characters."""
    s = s.replace('<cf>', '\r\n')
    s = s.replace('<cr>', '\r')
    s = s.replace('<lf>', '\n')
    s = s.replace('<ll>', '\\')
    if s == '[EmptyString]':
        s = ''
    return s


def read_null_terminated(data: bytes, offset: int) -> str:
    """Read null-terminated UTF-8 string from bytes at given offset."""
    end = data.find(b'\0', offset)
    if end == -1:
        return data[offset:].decode('utf-8')
    return data[offset:end].decode('utf-8')


# ═══════════════════════════════════════════════════════════════
# Version detection
# ═══════════════════════════════════════════════════════════════

def check_version(path: str) -> int:
    """
    Detect binary format version.
    0 = PS3 (big-endian, 32-bit)
    1 = PS4 (little-endian, 32-bit)
    2 = PS5/PC (little-endian, 64-bit)
    """
    with open(path, 'rb') as f:
        first_byte = f.read(1)[0]
    if first_byte == 0:
        return 0
    with open(path, 'rb') as f:
        f.seek(16)
        val = struct.unpack('<i', f.read(4))[0]
        return 2 if val == 0 else 1


# ═══════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════

def export_file(path: str) -> bool:
    """Export binary localization file to .txt (key|text) + .ids."""
    ver = check_version(path)
    print(f"  Ver: {ver}  |  {path}")

    with open(path, 'rb') as f:
        data = f.read()

    ext_clean = Path(path).suffix[1:]  # "subtitles" from ".subtitles"
    ids = [f"{ver}|{ext_clean}"]
    strings = []
    offsets = []

    # ── Parse header based on version ──
    if ver == 0:
        count = struct.unpack('>i', data[0:4])[0]
        pos = 4
        for _ in range(count):
            ids.append(str(struct.unpack('>I', data[pos:pos+4])[0]))
            offsets.append(struct.unpack('>i', data[pos+4:pos+8])[0])
            pos += 8

    elif ver == 1:
        count = struct.unpack('<i', data[0:4])[0]
        pos = 4
        for _ in range(count):
            ids.append(str(struct.unpack('<I', data[pos:pos+4])[0]))
            offsets.append(struct.unpack('<i', data[pos+4:pos+8])[0])
            pos += 8

    elif ver == 2:
        count = struct.unpack('<i', data[0:4])[0]
        pos = 4
        for _ in range(count):
            ids.append(str(struct.unpack('<Q', data[pos:pos+8])[0]))
            offsets.append(struct.unpack('<q', data[pos+8:pos+16])[0])
            pos += 16

    # ── Read strings from string table ──
    st_pos = pos
    for off in offsets:
        s = read_null_terminated(data, st_pos + off)
        strings.append(string_clear(s))

    # ── Write: key|text format ──
    keyed = [f"{ids[i+1]}|{strings[i]}" for i in range(count)]

    txt_path = path + '.txt'
    ids_path = path + '.ids'

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(keyed) + '\n')
    with open(ids_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ids) + '\n')

    print(f"  -> {txt_path} ({count} strings)")
    return True


# ═══════════════════════════════════════════════════════════════
# Import
# ═══════════════════════════════════════════════════════════════

def import_file(txt_path: str) -> bool:
    """Import .txt file back to binary format (.new)."""
    ids_path = Path(txt_path).with_suffix('.ids')
    if not ids_path.exists():
        print(f"  SKIP: {txt_path} — missing .ids file")
        return False

    with open(ids_path, 'r', encoding='utf-8') as f:
        ids = [line.rstrip('\n').rstrip('\r') for line in f]
    with open(txt_path, 'r', encoding='utf-8') as f:
        strings = [line.rstrip('\n').rstrip('\r') for line in f]

    # ── Detect format: new (key|text) vs old (text only) ──
    has_keys = len(strings) > 0 and '|' in strings[0]
    if has_keys:
        parsed_keys = []
        parsed_texts = []
        for line in strings:
            sep = line.index('|')
            parsed_keys.append(line[:sep])
            parsed_texts.append(line[sep + 1:])
        header = ids[0]
        ids.clear()
        ids.append(header)
        ids.extend(parsed_keys)
        strings = parsed_texts

    # ── Parse header ──
    ver = int(ids[0].split('|')[0])
    file_ext = ids[0].split('|')[1]
    ids = ids[1:]  # remove header row
    count = len(strings)

    buf = bytearray()
    strings_in_byte = []

    # ── Write binary based on version ──
    if ver == 0:
        buf += struct.pack('>i', count)
        temp_off = len(UNKNOWN_STRING)
        for i in range(count):
            sb = (string_declear(strings[i]) + '\0').encode('utf-8')
            strings_in_byte.append(sb)
            buf += struct.pack('>I', int(ids[i]))
            buf += struct.pack('>i', temp_off)
            temp_off += len(sb)

    elif ver == 1:
        buf += struct.pack('<i', count)
        temp_off = len(UNKNOWN_STRING)
        for i in range(count):
            sb = (string_declear(strings[i]) + '\0').encode('utf-8')
            strings_in_byte.append(sb)
            buf += struct.pack('<I', int(ids[i]))
            buf += struct.pack('<i', temp_off)
            temp_off += len(sb)

    elif ver == 2:
        buf += struct.pack('<i', count)
        temp_off = len(UNKNOWN_STRING)
        for i in range(count):
            sb = (string_declear(strings[i]) + '\0').encode('utf-8')
            strings_in_byte.append(sb)
            buf += struct.pack('<Q', int(ids[i]))
            buf += struct.pack('<q', temp_off)
            temp_off += len(sb)

    buf += UNKNOWN_STRING
    for sb in strings_in_byte:
        buf += sb

    # ── Write output: file.ext.new ──
    stem = str(Path(txt_path).with_suffix(''))  # remove .txt
    out_path = f"{stem}.{file_ext}.new"

    with open(out_path, 'wb') as f:
        f.write(buf)

    print(f"  -> {out_path} ({count} strings)")
    return True


# ═══════════════════════════════════════════════════════════════
# Path processing (file / folder / recursive)
# ═══════════════════════════════════════════════════════════════

def process_path(arg: str) -> int:
    """
    Process a file or directory argument.
    Returns number of files processed.
    """
    p = Path(arg)
    if not p.exists():
        print(f"  SKIP: {arg} — not found")
        return 0

    if p.is_file():
        return 1 if process_file(str(p)) else 0

    elif p.is_dir():
        count = 0
        for root, dirs, files in os.walk(p):
            for f in files:
                if process_file(os.path.join(root, f)):
                    count += 1
        if count == 0:
            print(f"  No supported files in: {arg}")
        else:
            print(f"  [{arg}] {count} file(s) processed")
        return count

    return 0


def is_localization_file(filepath: str) -> bool:
    """Check if file is a supported localization file (exact or compound extension)."""
    name = Path(filepath).name.lower()
    for ext in LOCALIZATION_EXTENSIONS:
        if name.endswith(ext):
            return True
    for suffix in LOCALIZATION_SUFFIXES:
        if name.endswith(suffix):
            return True
    return False


def process_file(filepath: str) -> bool:
    """Process single file. Returns True if processed."""
    ext = Path(filepath).suffix.lower()

    if is_localization_file(filepath):
        try:
            return export_file(filepath)
        except Exception as e:
            print(f"  ERROR exporting {filepath}: {e}")
            return False

    elif ext == '.txt':
        # Only import if matching .ids exists
        if Path(filepath).with_suffix('.ids').exists():
            print(f"  Import: {filepath}")
            try:
                return import_file(filepath)
            except Exception as e:
                print(f"  ERROR importing {filepath}: {e}")
                return False

    return False


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def show_usage():
    exe = Path(sys.argv[0]).name
    print(f"Naughty Dog Localization Tool (Python)")
    print(f"Based on original by NoobInCoding")
    print()
    print(f"Usage:")
    print(f"  {exe} <localization file>     Export binary to .txt + .ids")
    print(f"  {exe} <exported txt file>     Import .txt back to binary")
    print(f"  {exe} <folder>                Process all files in folder (recursive)")
    print(f"  {exe} <path1> <path2> ...     Process multiple files/folders")
    print()
    print(f"Supported extensions: {', '.join(sorted(LOCALIZATION_EXTENSIONS))}")
    print(f"Also matches compound: *.xxx-subtitles, *.xxx-common, etc. (e.g. 2.tll-subtitles)")
    print()
    print(f"Supported games:")
    for g in SUPPORTED_GAMES:
        print(f"  - {g}")
    print()
    print(f"Formats: v0 (PS3, BE 32-bit) | v1 (PS4, LE 32-bit) | v2 (PS5/PC, LE 64-bit)")
    print()
    print(f"Tip: Drop file or folder onto this script (or .exe) for drag-and-drop mode.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', '/?', '-?'):
        show_usage()
        if len(sys.argv) < 2:
            input("Press Enter to exit...")
        return

    print("Naughty Dog Localization Tool (Python)")
    print("=" * 50)

    total = 0
    for arg in sys.argv[1:]:
        total += process_path(arg)

    print("=" * 50)
    print(f"Done! ({total} file(s) processed)")
    if total == 0 and len(sys.argv) == 2 and Path(sys.argv[1]).is_file():
        ext = Path(sys.argv[1]).suffix.lower()
        if not is_localization_file(arg) and ext != '.txt':
            print(f"Hint: '{ext}' is not a supported file type.")


if __name__ == '__main__':
    main()
