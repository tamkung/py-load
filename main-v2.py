import sys
import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QProgressBar, QFileDialog, QMessageBox, QGroupBox, QTabWidget)
from PyQt6.QtCore import QThread, pyqtSignal
import requests
from requests.exceptions import RequestException
from moviepy.editor import VideoFileClip, AudioFileClip

def extract_aid_from_url(url):
    # ดึง aid จาก URL
    try:
        if "/video/" in url:
            aid = url.split("/video/")[1].split("?")[0]
            return aid
    except:
        return None
    return None

def get_bilibili_urls(video_url):
    try:
        # ดึง aid จาก URL
        aid = extract_aid_from_url(video_url)
        if not aid:
            raise ValueError("ไม่สามารถดึง aid จาก URL ได้")

        # สร้าง URL สำหรับเรียก API
        api_url = f"https://api.bilibili.tv/intl/gateway/web/playurl?s_locale=th_TH&platform=web&aid={aid}&qn=80&type=0&device=wap&tf=0"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.bilibili.tv/'
        }

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise ValueError(f"API Error: {data.get('message')}")

        playurl_data = data.get("data", {}).get("playurl", {})
        # print("Full API Response:", data)
        # print("Playurl Data:", playurl_data)
        
        # ดึง URL วิดีโอและเสียง
        video_url = None
        audio_url = None

        # ดึง URL วิดีโอคุณภาพสูงสุด (1080P หรือ 720P)
        videos = playurl_data.get("video", [])
        if videos:
            # ลองหาวิดีโอคุณภาพ 1080P (quality=80) ก่อน
            for video in videos:
                video_resource = video.get("video_resource", {})
                if video_resource.get("quality") == 80:
                    temp_url = video_resource.get("url")
                    if temp_url and temp_url.strip():  # ตรวจสอบว่า URL ไม่ว่างเปล่า
                        video_url = temp_url
                        print("Found 1080P video URL:", video_url)
                        break
            
            # ถ้าไม่มี 1080P หรือ URL ว่างเปล่า ให้ใช้ 720P (quality=64)
            if not video_url:
                for video in videos:
                    video_resource = video.get("video_resource", {})
                    if video_resource.get("quality") == 64:
                        temp_url = video_resource.get("url")
                        if temp_url and temp_url.strip():  # ตรวจสอบว่า URL ไม่ว่างเปล่า
                            video_url = temp_url
                            print("Found 720P video URL:", video_url)
                            break

        # ดึง URL เสียงคุณภาพสูงสุด
        audio_resources = playurl_data.get("audio_resource", [])
        if audio_resources:
            # เลือกเสียงคุณภาพสูงสุด (quality=30280)
            for audio in audio_resources:
                if audio.get("quality") == 30280:
                    audio_url = audio.get("url")
                    print("Found audio URL:", audio_url)
                    break

        if not video_url or not audio_url:
            raise ValueError("ไม่พบ URL วิดีโอหรือเสียง")

        print("Final Video URL:", video_url)
        print("Final Audio URL:", audio_url)

        return video_url, audio_url

    except Exception as e:
        print("Error:", str(e))
        raise Exception(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {str(e)}")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def merge_files(video_path, audio_path, output_path):
    try:
        # สร้าง temp directory สำหรับเก็บไฟล์ชั่วคราว
        temp_dir = os.path.join(os.environ.get('TEMP') or os.environ.get('TMP') or os.getcwd(), 'bilibili_temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        print(f"Video path: {video_path}")
        print(f"Audio path: {audio_path}")
        print(f"Output path: {output_path}")
        
        # ใช้ subprocess เรียก ffmpeg โดยตรง
        command = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c', 'copy',
            '-y',  # ให้เขียนทับไฟล์ที่มีอยู่
            output_path
        ]
        
        # รันคำสั่ง ffmpeg
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # รอให้ process เสร็จสิ้น
        stdout, stderr = process.communicate()
        
        # ตรวจสอบผลลัพธ์
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr}")
            
        # ลบ temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
            
    except Exception as e:
        print(f"Error in merge_files: {str(e)}")
        # ลบไฟล์ชั่วคราวถ้ามีข้อผิดพลาด
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        raise Exception(f"เกิดข้อผิดพลาดในการรวมไฟล์: {str(e)}")

def download_file(url, output_path, progress_callback=None):
    try:
        # ใช้ temporary directory สำหรับดาวน์โหลด
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "temp_download")
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # ขนาดไฟล์ทั้งหมด
            total_size = int(response.headers.get('content-length', 0))
            
            # ดาวน์โหลดไฟล์
            with open(temp_file, 'wb') as f:
                if total_size == 0:  # ไม่ทราบขนาดไฟล์
                    f.write(response.content)
                else:
                    downloaded = 0
                    for data in response.iter_content(chunk_size=4096):
                        downloaded += len(data)
                        f.write(data)
                        if progress_callback:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            # ย้ายไฟล์จาก temp ไปยังที่หมายปลายทาง
            if os.path.exists(temp_file):
                # ถ้ามีไฟล์เดิมอยู่ ให้ลบก่อน
                if os.path.exists(output_path):
                    os.remove(output_path)
                # ย้ายไฟล์
                os.rename(temp_file, output_path)
            else:
                raise Exception("ไม่พบไฟล์ที่ดาวน์โหลด")
                
    except Exception as e:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise Exception(f"เกิดข้อผิดพลาดในการดาวน์โหลด: {str(e)}")

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self._stop = False

    def run(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.bilibili.tv/'
            }
            
            with requests.get(self.url, stream=True, headers=headers) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                downloaded = 0

                with open(self.save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if self._stop:
                            self.status.emit("ยกเลิกการดาวน์โหลด")
                            return
                            
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = int((downloaded / total_size) * 100)
                                self.progress.emit(progress)
                                self.status.emit(f"กำลังดาวน์โหลด: {progress}%")

            if not self._stop:
                self.status.emit("ดาวน์โหลดเสร็จสิ้น")
                self.finished.emit()

        except RequestException as e:
            if not self._stop:
                self.error.emit(str(e))

    def stop(self):
        self._stop = True

class MergeThread(QThread):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, video_path, audio_path, output_path):
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_path = output_path
        self._stop = False

    def run(self):
        try:
            self.status.emit("กำลังรวมไฟล์...")
            merge_files(self.video_path, self.audio_path, self.output_path)
            if not self._stop:
                self.progress.emit(100)
                self.status.emit("รวมไฟล์เสร็จสิ้น")
                self.finished.emit()
        except Exception as e:
            if not self._stop:
                self.error.emit(str(e))

    def stop(self):
        self._stop = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("โปรแกรมดาวน์โหลดและรวมไฟล์ Bilibili")
        self.setGeometry(100, 100, 800, 600)

        # สร้าง widget หลัก
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # สร้างแท็บสำหรับโหมดง่ายและขั้นสูง
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # สร้างแท็บโหมดง่าย
        easy_tab = QWidget()
        easy_layout = QVBoxLayout(easy_tab)
        
        # ส่วน URL และปุ่มดาวน์โหลด
        url_group = QGroupBox("ดาวน์โหลดอัตโนมัติ")
        url_layout = QVBoxLayout()
        url_group.setLayout(url_layout)

        # URL input
        url_input_layout = QHBoxLayout()
        self.easy_url = QLineEdit()
        self.easy_download_btn = QPushButton("ดาวน์โหลดและรวมไฟล์")
        self.easy_download_btn.clicked.connect(self.easy_download)
        url_input_layout.addWidget(QLabel("Bilibili URL:"))
        url_input_layout.addWidget(self.easy_url)
        url_input_layout.addWidget(self.easy_download_btn)
        url_layout.addLayout(url_input_layout)

        # Progress bar และ status
        self.easy_progress = QProgressBar()
        url_layout.addWidget(self.easy_progress)
        self.easy_status = QLabel()
        url_layout.addWidget(self.easy_status)

        easy_layout.addWidget(url_group)
        tab_widget.addTab(easy_tab, "โหมดง่าย")

        # สร้างแท็บโหมดขั้นสูง
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)

        # ส่วน URL Bilibili
        bilibili_group = QGroupBox("Bilibili URL")
        bilibili_layout = QHBoxLayout()
        bilibili_group.setLayout(bilibili_layout)

        self.bilibili_url = QLineEdit()
        self.fetch_btn = QPushButton("ดึงข้อมูล")
        self.fetch_btn.clicked.connect(self.fetch_bilibili)

        bilibili_layout.addWidget(QLabel("URL:"))
        bilibili_layout.addWidget(self.bilibili_url)
        bilibili_layout.addWidget(self.fetch_btn)

        advanced_layout.addWidget(bilibili_group)

        # ส่วนดาวน์โหลดวิดีโอ
        video_group = QGroupBox("ดาวน์โหลดวิดีโอ")
        video_layout = QVBoxLayout()
        video_group.setLayout(video_layout)

        url_layout = QHBoxLayout()
        self.video_url = QLineEdit()
        url_layout.addWidget(QLabel("URL วิดีโอ:"))
        url_layout.addWidget(self.video_url)
        video_layout.addLayout(url_layout)

        self.video_progress = QProgressBar()
        video_layout.addWidget(self.video_progress)

        self.video_status = QLabel()
        video_layout.addWidget(self.video_status)

        button_layout = QHBoxLayout()
        self.video_download_btn = QPushButton("ดาวน์โหลดวิดีโอ")
        self.video_download_btn.clicked.connect(lambda: self.download_file("video"))
        self.video_cancel_btn = QPushButton("ยกเลิก")
        self.video_cancel_btn.clicked.connect(lambda: self.cancel_download("video"))
        self.video_cancel_btn.setEnabled(False)
        button_layout.addWidget(self.video_download_btn)
        button_layout.addWidget(self.video_cancel_btn)
        video_layout.addLayout(button_layout)

        advanced_layout.addWidget(video_group)

        # ส่วนดาวน์โหลดเสียง
        audio_group = QGroupBox("ดาวน์โหลดเสียง")
        audio_layout = QVBoxLayout()
        audio_group.setLayout(audio_layout)

        url_layout = QHBoxLayout()
        self.audio_url = QLineEdit()
        url_layout.addWidget(QLabel("URL เสียง:"))
        url_layout.addWidget(self.audio_url)
        audio_layout.addLayout(url_layout)

        self.audio_progress = QProgressBar()
        audio_layout.addWidget(self.audio_progress)

        self.audio_status = QLabel()
        audio_layout.addWidget(self.audio_status)

        button_layout = QHBoxLayout()
        self.audio_download_btn = QPushButton("ดาวน์โหลดเสียง")
        self.audio_download_btn.clicked.connect(lambda: self.download_file("audio"))
        self.audio_cancel_btn = QPushButton("ยกเลิก")
        self.audio_cancel_btn.clicked.connect(lambda: self.cancel_download("audio"))
        self.audio_cancel_btn.setEnabled(False)
        button_layout.addWidget(self.audio_download_btn)
        button_layout.addWidget(self.audio_cancel_btn)
        audio_layout.addLayout(button_layout)

        advanced_layout.addWidget(audio_group)

        # ส่วนรวมไฟล์
        merge_group = QGroupBox("รวมไฟล์")
        merge_layout = QVBoxLayout()
        merge_group.setLayout(merge_layout)

        video_layout = QHBoxLayout()
        self.video_path = QLineEdit()
        video_select_btn = QPushButton("เลือกไฟล์")
        video_select_btn.clicked.connect(lambda: self.select_file("video"))
        video_layout.addWidget(QLabel("ไฟล์วิดีโอ:"))
        video_layout.addWidget(self.video_path)
        video_layout.addWidget(video_select_btn)
        merge_layout.addLayout(video_layout)

        audio_layout = QHBoxLayout()
        self.audio_path = QLineEdit()
        audio_select_btn = QPushButton("เลือกไฟล์")
        audio_select_btn.clicked.connect(lambda: self.select_file("audio"))
        audio_layout.addWidget(QLabel("ไฟล์เสียง:"))
        audio_layout.addWidget(self.audio_path)
        audio_layout.addWidget(audio_select_btn)
        merge_layout.addLayout(audio_layout)

        self.merge_status = QLabel()
        merge_layout.addWidget(self.merge_status)

        button_layout = QHBoxLayout()
        self.merge_btn = QPushButton("รวมไฟล์")
        self.merge_btn.clicked.connect(self.merge_files)
        self.merge_cancel_btn = QPushButton("ยกเลิกและปิดโปรแกรม")
        self.merge_cancel_btn.clicked.connect(self.cancel_merge)
        self.merge_cancel_btn.setEnabled(False)
        button_layout.addWidget(self.merge_btn)
        button_layout.addWidget(self.merge_cancel_btn)
        merge_layout.addLayout(button_layout)

        advanced_layout.addWidget(merge_group)
        tab_widget.addTab(advanced_tab, "โหมดขั้นสูง")

        # ตัวแปรสำหรับเก็บ thread
        self.video_thread = None
        self.audio_thread = None
        self.merge_thread = None
        self.easy_video_path = None
        self.easy_audio_path = None

    def easy_download(self):
        url = self.easy_url.text()
        if not url:
            QMessageBox.warning(self, "คำเตือน", "กรุณาใส่ URL Bilibili")
            return

        # ให้ผู้ใช้เลือกที่บันทึกไฟล์
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "บันทึกไฟล์วิดีโอ",
            "",
            "MP4 files (*.mp4)"
        )
        if not output_path:
            return

        try:
            # ดึง URL วิดีโอและเสียง
            self.easy_status.setText("กำลังดึงข้อมูล URL...")
            video_url, audio_url = get_bilibili_urls(url)

            # สร้าง temp directory
            temp_dir = os.path.join(os.environ.get('TEMP') or os.environ.get('TMP') or os.getcwd(), 'bilibili_temp')
            os.makedirs(temp_dir, exist_ok=True)

            # กำหนดพาธสำหรับไฟล์ชั่วคราว
            self.easy_video_path = os.path.join(temp_dir, "temp_video.mp4")
            self.easy_audio_path = os.path.join(temp_dir, "temp_audio.m4s")

            # ดาวน์โหลดวิดีโอ
            self.easy_status.setText("กำลังดาวน์โหลดวิดีโอ...")
            self.easy_progress.setValue(0)
            
            def video_progress(progress):
                self.easy_progress.setValue(int(progress * 0.4))  # 40% สำหรับวิดีโอ
            
            download_file(video_url, self.easy_video_path, video_progress)

            # ดาวน์โหลดเสียง
            self.easy_status.setText("กำลังดาวน์โหลดเสียง...")
            self.easy_progress.setValue(40)
            
            def audio_progress(progress):
                self.easy_progress.setValue(40 + int(progress * 0.4))  # 40% สำหรับเสียง
            
            download_file(audio_url, self.easy_audio_path, audio_progress)

            # รวมไฟล์
            self.easy_status.setText("กำลังรวมไฟล์...")
            self.easy_progress.setValue(80)
            merge_files(self.easy_video_path, self.easy_audio_path, output_path)

            # เสร็จสิ้น
            self.easy_progress.setValue(100)
            self.easy_status.setText("ดำเนินการเสร็จสิ้น")
            QMessageBox.information(self, "สำเร็จ", "ดาวน์โหลดและรวมไฟล์เสร็จสิ้น")

            # ลบไฟล์ชั่วคราว
            try:
                os.remove(self.easy_video_path)
                os.remove(self.easy_audio_path)
                os.rmdir(temp_dir)
            except:
                pass

        except Exception as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))
            self.easy_status.setText("เกิดข้อผิดพลาด")
            # ลบไฟล์ชั่วคราวถ้ามีข้อผิดพลาด
            try:
                if self.easy_video_path and os.path.exists(self.easy_video_path):
                    os.remove(self.easy_video_path)
                if self.easy_audio_path and os.path.exists(self.easy_audio_path):
                    os.remove(self.easy_audio_path)
                os.rmdir(temp_dir)
            except:
                pass

    def fetch_bilibili(self):
        url = self.bilibili_url.text()
        if not url:
            QMessageBox.warning(self, "คำเตือน", "กรุณาใส่ URL Bilibili")
            return

        try:
            video_url, audio_url = get_bilibili_urls(url)
            self.video_url.setText(video_url)
            self.audio_url.setText(audio_url)
        except Exception as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", str(e))

    def download_file(self, file_type):
        url = self.video_url.text() if file_type == "video" else self.audio_url.text()
        if not url:
            QMessageBox.warning(self, "คำเตือน", f"กรุณาใส่ URL {file_type}")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"บันทึกไฟล์ {file_type}",
            "",
            "MP4 files (*.mp4)"
        )
        if not save_path:
            return

        progress_bar = self.video_progress if file_type == "video" else self.audio_progress
        status_label = self.video_status if file_type == "video" else self.audio_status
        download_btn = self.video_download_btn if file_type == "video" else self.audio_download_btn
        cancel_btn = self.video_cancel_btn if file_type == "video" else self.audio_cancel_btn

        progress_bar.setValue(0)
        status_label.setText("กำลังดาวน์โหลด...")
        download_btn.setEnabled(False)
        cancel_btn.setEnabled(True)

        thread = DownloadThread(url, save_path)
        thread.progress.connect(progress_bar.setValue)
        thread.status.connect(status_label.setText)
        thread.error.connect(lambda e: QMessageBox.critical(self, "ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการดาวน์โหลด: {e}"))
        thread.finished.connect(lambda: self.download_finished(file_type))

        if file_type == "video":
            self.video_thread = thread
        else:
            self.audio_thread = thread
        thread.start()

    def download_finished(self, file_type):
        download_btn = self.video_download_btn if file_type == "video" else self.audio_download_btn
        cancel_btn = self.video_cancel_btn if file_type == "video" else self.audio_cancel_btn
        download_btn.setEnabled(True)
        cancel_btn.setEnabled(False)
        QMessageBox.information(self, "สำเร็จ", "ดาวน์โหลดเสร็จสิ้น")

    def cancel_download(self, file_type):
        thread = self.video_thread if file_type == "video" else self.audio_thread
        if thread:
            thread.stop()
            
        download_btn = self.video_download_btn if file_type == "video" else self.audio_download_btn
        cancel_btn = self.video_cancel_btn if file_type == "video" else self.audio_cancel_btn
        download_btn.setEnabled(True)
        cancel_btn.setEnabled(False)

    def select_file(self, file_type):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"เลือกไฟล์ {file_type}",
            "",
            "MP4 files (*.mp4)"
        )
        if file_path:
            if file_type == "video":
                self.video_path.setText(file_path)
            else:
                self.audio_path.setText(file_path)

    def merge_files(self):
        video_path = self.video_path.text()
        audio_path = self.audio_path.text()

        if not video_path or not audio_path:
            QMessageBox.warning(self, "คำเตือน", "กรุณาเลือกไฟล์วิดีโอและเสียง")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "บันทึกไฟล์ผลลัพธ์",
            "",
            "MP4 files (*.mp4)"
        )
        if not output_path:
            return

        self.merge_status.setText("กำลังรวมไฟล์...")
        self.merge_btn.setEnabled(False)
        self.merge_cancel_btn.setEnabled(True)

        self.merge_thread = MergeThread(video_path, audio_path, output_path)
        self.merge_thread.status.connect(self.merge_status.setText)
        self.merge_thread.error.connect(lambda e: QMessageBox.critical(self, "ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการรวมไฟล์: {e}"))
        self.merge_thread.finished.connect(self.merge_finished)
        self.merge_thread.start()

    def merge_finished(self):
        self.merge_btn.setEnabled(True)
        self.merge_cancel_btn.setEnabled(False)
        QMessageBox.information(self, "สำเร็จ", "รวมไฟล์เสร็จสิ้น")

    def cancel_merge(self):
        if self.merge_thread:
            self.merge_thread.stop()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 