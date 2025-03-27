# โปรแกรมรวมไฟล์วิดีโอและเสียง (Video Audio Merger)

โปรแกรมสำหรับดาวน์โหลดและรวมไฟล์วิดีโอกับเสียงเข้าด้วยกัน พัฒนาด้วย Python และ PyQt6

## คุณสมบัติ
- ดาวน์โหลดไฟล์วิดีโอและเสียงจาก URL
- แสดงความคืบหน้าการดาวน์โหลด
- สามารถยกเลิกการดาวน์โหลดได้
- รวมไฟล์วิดีโอและเสียงเข้าด้วยกัน
- รองรับไฟล์ .mp4

## การติดตั้ง

### วิธีที่ 1: รันจากไฟล์ .exe
1. ดาวน์โหลดไฟล์ `VideoAudioMerger.exe` จากโฟลเดอร์ `dist`
2. ดับเบิ้ลคลิกที่ไฟล์เพื่อเปิดโปรแกรม

### วิธีที่ 2: รันจากซอร์สโค้ด
1. ติดตั้ง Python 3.10 หรือใหม่กว่า
2. สร้าง virtual environment:
```bash
python -m venv env
env\Scripts\activate  # Windows
source env/bin/activate  # Linux/Mac
```
3. ติดตั้ง dependencies:
```bash
pip install PyQt6 requests moviepy
```
4. รันโปรแกรม:
```bash
python main.py
```

## วิธีใช้งาน
1. ดาวน์โหลดไฟล์:
   - ใส่ URL วิดีโอในช่องแรก และกดปุ่ม "ดาวน์โหลดวิดีโอ"
   - ใส่ URL เสียงในช่องที่สอง และกดปุ่ม "ดาวน์โหลดเสียง"
   - สามารถดาวน์โหลดพร้อมกันได้ทั้งสองไฟล์
   - กดปุ่ม "ยกเลิก" เพื่อยกเลิกการดาวน์โหลด

2. รวมไฟล์:
   - กดปุ่ม "เลือกไฟล์" เพื่อเลือกไฟล์วิดีโอและเสียง
   - กดปุ่ม "รวมไฟล์วิดีโอและเสียง"
   - รอจนกว่าการรวมไฟล์จะเสร็จสิ้น
   - กดปุ่ม "ยกเลิก" หากต้องการยกเลิกการรวมไฟล์

## ข้อกำหนดทางเทคนิค
- Python 3.10+
- PyQt6
- requests
- moviepy

## การพัฒนา
1. Clone repository:
```bash
git clone <repository-url>
cd video-audio-merger
```

2. ติดตั้ง dependencies สำหรับการพัฒนา:
```bash
pip install PyQt6 requests moviepy pyinstaller
```

3. สร้างไฟล์ .exe:
```bash
pyinstaller --onefile --windowed --name "VideoAudioMerger" main.py
```