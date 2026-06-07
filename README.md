# NaughtyDogLocalizationTool Plus

Tool สำหรับ export/import ไฟล์ localization ของเกม **Naughty Dog** ทุกภาค  
รองรับทุกแพลตฟอร์ม: **PS3 / PS4 / PS5 / PC**

Original by NoobInCoding | Python port + improvements

---

## ความสามารถ

- **Export** — แปลง binary localization เป็น `.txt` (key|text) + `.ids`
- **Import** — แปลง `.txt` กลับเป็น binary `.new`
- **Key ใน .txt** — ทุกบรรทัดมี `key|text` ใช้ key จับคู่ข้ามแพลตฟอร์มได้
- **Recursive folder** — ลากโฟลเดอร์มาวาง ประมวลผลทุกไฟล์ใน subfolder
- **Drag & drop** — ลากไฟล์หรือโฟลเดอร์มาวางที่ script (หรือ .exe)
- **Backward compatible** — ไฟล์ `.txt` แบบเก่า (ข้อความล้วน) ยัง import ได้

## Requirements

- **Python 3.7+**
- ไม่ต้องติดตั้ง package เพิ่มเติม (standard library ล้วน)

## วิธีใช้

### Export (binary → text)

```bash
python ndlt.py game.subtitles
python ndlt.py game.common
python ndlt.py game.subtitles-systemic
python ndlt.py game.web
```

Output:
- `game.subtitles.txt` — key|text สำหรับแปล/แก้ไข
- `game.subtitles.ids` — ข้อมูล version + keys (ใช้คู่กับ import)

### Import (text → binary)

```bash
python ndlt.py game.subtitles.txt
```

Output:
- `game.subtitles.new` — binary ใหม่ พร้อมใช้ (เปลี่ยนชื่อเอา `.new` ออก)

### โฟลเดอร์ (recursive)

```bash
# ประมวลผลทุกไฟล์ในโฟลเดอร์และ subfolder ทั้งหมด
python ndlt.py "C:\Game Files\localization\"

# หลายไฟล์/โฟลเดอร์พร้อมกัน
python ndlt.py file1.subtitles file2.common "folder1/" "folder2/"
```

### Drag & drop

ลากไฟล์ หรือโฟลเดอร์ มาวางที่ `ndlt.py` (หรือ `ndlt.exe` ถ้า compile แล้ว)

---

## ฟอร์แมตไฟล์

### `.txt` — key|text format

```text
302613|Slow Motion
1545394|Press Start
2182163|Loading...
```

- **key** — ID ตัวเลข ใช้จับคู่ข้ามแพลตฟอร์ม
- **text** — ข้อความสำหรับแปล/แก้ไข
- แก้ไขเฉพาะข้อความหลัง `|` ได้เลย
- key ต้องคงเดิมไว้สำหรับ import

### `.ids` — metadata

```text
1|subtitles
302613
1545394
2182163
```

- บรรทัดแรก: `version|นามสกุล`
- บรรทัดถัดมา: key เรียงตามลำดับใน `.txt`

---

## รูปแบบ Binary

| Version | แพลตฟอร์ม | Endian | ID/Offset size | หมายเหตุ |
|---------|-----------|--------|----------------|----------|
| **v0** | PS3 | Big-endian | 32-bit | first byte = 0x00 |
| **v1** | PS4 | Little-endian | 32-bit | มี `UNKNOWN STRING!!!` ใน string table |
| **v2** | PS5 / PC | Little-endian | 64-bit | ID และ offset ใช้ 8 bytes |

### โครงสร้าง Binary

```
[4 bytes: จำนวน string (int32)]
[for each string: ID + offset]
[string table: null-terminated UTF-8 strings]
```

- v0/v1: แต่ละ entry = 8 bytes (4 ID + 4 offset)
- v2: แต่ละ entry = 16 bytes (8 ID + 8 offset)
- String table เริ่มด้วย `UNKNOWN STRING!!!\0` (18 bytes) ใน v1/v2

---

## เกมที่รองรับ

- **Uncharted** (ทุกภาค)
- **The Last of Us** (ทุกภาค)

นามสกุลไฟล์: `.subtitles` `.common` `.subtitles-systemic` `.web`

---

## Build .exe (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --icon=Icon.ico ndlt.py
```

ได้ `ndlt.exe` ใน `dist/` — ใช้งานเหมือนของเดิม ลากวางได้

---

## Improvements จากเวอร์ชัน C# เดิม

| ฟีเจอร์ | C# เดิม | Python |
|---------|---------|--------|
| Export / Import | ✓ | ✓ |
| v0 / v1 / v2 | ✓ | ✓ |
| key\|text ใน .txt | ✗ | **✓** |
| โฟลเดอร์ recursive | ✗ | **✓** |
| หลายไฟล์พร้อมกัน | ✗ | **✓** |
| `--help` | ✗ | **✓** |
| Bug Fix: Import0 offset | มี bug | **✓** แก้แล้ว |
| Backward compat (ไฟล์เก่า) | ✓ | ✓ |
| Drag & drop | ✓ | ✓ |

---

## License

Original tool by NoobInCoding. Python port released under same terms.
