import sys
import requests
from requests.exceptions import RequestException
from moviepy.editor import VideoFileClip, AudioFileClip
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                            QFileDialog, QProgressBar, QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

def merge_video_audio(video_path, audio_path, output_path):
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)
    
    video_clip = video_clip.set_audio(audio_clip)
    video_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", audio_bitrate="111k", audio_fps=48000)
    
    video_clip.close()
    audio_clip.close()

class DownloadThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, save_path, file_type):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.file_type = file_type
        self._is_cancelled = False

    def run(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.bilibili.com/'
            }
            
            with requests.get(self.url, stream=True, headers=headers) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                downloaded = 0

                with open(self.save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if self._is_cancelled:
                            self.progress.emit(f"ยกเลิกการดาวน์โหลด{self.file_type}")
                            return
                            
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = int((downloaded / total_size) * 100)
                                self.progress.emit(f"กำลังดาวน์โหลด{self.file_type}: {progress}%")

            if not self._is_cancelled:
                self.progress.emit(f"ดาวน์โหลด{self.file_type}เสร็จสิ้น")
                self.finished.emit()

        except RequestException as e:
            if not self._is_cancelled:
                self.error.emit(f"เกิดข้อผิดพลาดในการดาวน์โหลด{self.file_type}: {str(e)}")

    def cancel(self):
        self._is_cancelled = True

class MergeThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, video_path, audio_path, output_path):
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_path = output_path
        self._is_cancelled = False

    def run(self):
        try:
            video_clip = VideoFileClip(self.video_path)
            audio_clip = AudioFileClip(self.audio_path)
            
            if self._is_cancelled:
                self.progress.emit("ยกเลิกการรวมไฟล์")
                return
                
            video_clip = video_clip.set_audio(audio_clip)
            
            if self._is_cancelled:
                self.progress.emit("ยกเลิกการรวมไฟล์")
                return
                
            video_clip.write_videofile(self.output_path, codec="libx264", audio_codec="aac", audio_bitrate="111k", audio_fps=48000)
            
            video_clip.close()
            audio_clip.close()
            
            if not self._is_cancelled:
                self.progress.emit("รวมไฟล์เสร็จสิ้น")
                self.finished.emit()

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(f"เกิดข้อผิดพลาดในการรวมไฟล์: {str(e)}")

    def cancel(self):
        self._is_cancelled = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("โปรแกรมรวมไฟล์วิดีโอและเสียง")
        self.setMinimumSize(800, 400)

        # สร้าง widget หลัก
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # ส่วนดาวน์โหลด
        download_group = QGroupBox("ดาวน์โหลด")
        download_layout = QVBoxLayout(download_group)
        
        # ส่วนดาวน์โหลดวิดีโอ
        video_download_layout = QHBoxLayout()
        self.video_url_input = QLineEdit()
        self.video_url_input.setPlaceholderText("ใส่ URL วิดีโอที่นี่")
        video_download_layout.addWidget(self.video_url_input)
        
        video_btn_layout = QHBoxLayout()
        self.video_download_btn = QPushButton("ดาวน์โหลดวิดีโอ")
        self.video_download_btn.clicked.connect(lambda: self.download_file("วิดีโอ"))
        video_btn_layout.addWidget(self.video_download_btn)
        
        self.video_cancel_btn = QPushButton("ยกเลิก")
        self.video_cancel_btn.clicked.connect(lambda: self.cancel_download("วิดีโอ"))
        self.video_cancel_btn.setEnabled(False)
        video_btn_layout.addWidget(self.video_cancel_btn)
        
        video_download_layout.addLayout(video_btn_layout)
        download_layout.addLayout(video_download_layout)
        self.video_status = QLabel("")
        download_layout.addWidget(self.video_status)
        
        # ส่วนดาวน์โหลดเสียง
        audio_download_layout = QHBoxLayout()
        self.audio_url_input = QLineEdit()
        self.audio_url_input.setPlaceholderText("ใส่ URL เสียงที่นี่")
        audio_download_layout.addWidget(self.audio_url_input)
        
        audio_btn_layout = QHBoxLayout()
        self.audio_download_btn = QPushButton("ดาวน์โหลดเสียง")
        self.audio_download_btn.clicked.connect(lambda: self.download_file("เสียง"))
        audio_btn_layout.addWidget(self.audio_download_btn)
        
        self.audio_cancel_btn = QPushButton("ยกเลิก")
        self.audio_cancel_btn.clicked.connect(lambda: self.cancel_download("เสียง"))
        self.audio_cancel_btn.setEnabled(False)
        audio_btn_layout.addWidget(self.audio_cancel_btn)
        
        audio_download_layout.addLayout(audio_btn_layout)
        download_layout.addLayout(audio_download_layout)
        self.audio_status = QLabel("")
        download_layout.addWidget(self.audio_status)
        
        layout.addWidget(download_group)

        # ส่วนเลือกไฟล์
        file_group = QGroupBox("เลือกไฟล์")
        file_layout = QVBoxLayout(file_group)
        
        video_layout = QHBoxLayout()
        self.video_path = QLineEdit()
        self.video_path.setPlaceholderText("เลือกไฟล์วิดีโอ")
        video_layout.addWidget(self.video_path)
        video_btn = QPushButton("เลือกไฟล์")
        video_btn.clicked.connect(lambda: self.select_file("video"))
        video_layout.addWidget(video_btn)
        
        audio_layout = QHBoxLayout()
        self.audio_path = QLineEdit()
        self.audio_path.setPlaceholderText("เลือกไฟล์เสียง")
        audio_layout.addWidget(self.audio_path)
        audio_btn = QPushButton("เลือกไฟล์")
        audio_btn.clicked.connect(lambda: self.select_file("audio"))
        audio_layout.addWidget(audio_btn)
        
        file_layout.addLayout(video_layout)
        file_layout.addLayout(audio_layout)
        
        layout.addWidget(file_group)

        # ปุ่มรวมไฟล์
        merge_group = QGroupBox("รวมไฟล์")
        merge_layout = QVBoxLayout(merge_group)
        
        merge_btn_layout = QHBoxLayout()
        self.merge_btn = QPushButton("รวมไฟล์วิดีโอและเสียง")
        self.merge_btn.clicked.connect(self.merge_files)
        merge_btn_layout.addWidget(self.merge_btn)
        
        self.merge_cancel_btn = QPushButton("ยกเลิก")
        self.merge_cancel_btn.clicked.connect(self.cancel_merge)
        self.merge_cancel_btn.setEnabled(False)
        merge_btn_layout.addWidget(self.merge_cancel_btn)
        
        merge_layout.addLayout(merge_btn_layout)
        self.status_label = QLabel("")
        merge_layout.addWidget(self.status_label)
        layout.addWidget(merge_group)

        # กำหนดตัวแปร
        self.video_download_thread = None
        self.audio_download_thread = None
        self.merge_thread = None

    def download_file(self, file_type):
        url_input = self.video_url_input if file_type == "วิดีโอ" else self.audio_url_input
        status_label = self.video_status if file_type == "วิดีโอ" else self.audio_status
        download_btn = self.video_download_btn if file_type == "วิดีโอ" else self.audio_download_btn
        cancel_btn = self.video_cancel_btn if file_type == "วิดีโอ" else self.audio_cancel_btn
        
        url = url_input.text()
        if not url:
            QMessageBox.warning(self, "คำเตือน", f"กรุณาใส่ URL {file_type}")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, f"บันทึกไฟล์{file_type}", "", "Video Files (*.mp4)"
        )
        if not save_path:
            return

        status_label.setText(f"กำลังดาวน์โหลด{file_type}...")
        download_thread = DownloadThread(url, save_path, file_type)
        download_thread.progress.connect(lambda msg: status_label.setText(msg))
        download_thread.finished.connect(lambda: self.download_finished(file_type))
        download_thread.error.connect(lambda msg: self.download_error(msg))
        
        if file_type == "วิดีโอ":
            self.video_download_thread = download_thread
        else:
            self.audio_download_thread = download_thread
            
        download_btn.setEnabled(False)
        cancel_btn.setEnabled(True)
        download_thread.start()

    def cancel_download(self, file_type):
        if file_type == "วิดีโอ" and self.video_download_thread:
            self.video_download_thread.cancel()
            self.video_download_btn.setEnabled(True)
            self.video_cancel_btn.setEnabled(False)
        elif file_type == "เสียง" and self.audio_download_thread:
            self.audio_download_thread.cancel()
            self.audio_download_btn.setEnabled(True)
            self.audio_cancel_btn.setEnabled(False)

    def download_finished(self, file_type):
        if file_type == "วิดีโอ":
            self.video_download_btn.setEnabled(True)
            self.video_cancel_btn.setEnabled(False)
        else:
            self.audio_download_btn.setEnabled(True)
            self.audio_cancel_btn.setEnabled(False)
            
        QMessageBox.information(self, "สำเร็จ", f"ดาวน์โหลด{file_type}เสร็จสิ้น")

    def download_error(self, error_message):
        QMessageBox.critical(self, "ข้อผิดพลาด", error_message)

    def select_file(self, file_type):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"เลือกไฟล์{file_type}", "", "Video Files (*.mp4)"
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
            self, "บันทึกไฟล์ผลลัพธ์", "", "Video Files (*.mp4)"
        )
        if not output_path:
            return

        try:
            self.status_label.setText("กำลังรวมไฟล์...")
            self.merge_thread = MergeThread(video_path, audio_path, output_path)
            self.merge_thread.progress.connect(lambda msg: self.status_label.setText(msg))
            self.merge_thread.finished.connect(self.merge_finished)
            self.merge_thread.error.connect(lambda msg: self.merge_error(msg))
            
            self.merge_btn.setEnabled(False)
            self.merge_cancel_btn.setEnabled(True)
            self.merge_thread.start()
            
        except Exception as e:
            self.status_label.setText("เกิดข้อผิดพลาด")
            QMessageBox.critical(self, "ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการรวมไฟล์: {str(e)}")

    def cancel_merge(self):
        if self.merge_thread:
            self.merge_thread.cancel()
            self.merge_btn.setEnabled(True)
            self.merge_cancel_btn.setEnabled(False)

    def merge_finished(self):
        self.merge_btn.setEnabled(True)
        self.merge_cancel_btn.setEnabled(False)
        QMessageBox.information(self, "สำเร็จ", "รวมไฟล์เสร็จสิ้น")

    def merge_error(self, error_message):
        self.merge_btn.setEnabled(True)
        self.merge_cancel_btn.setEnabled(False)
        self.status_label.setText("เกิดข้อผิดพลาด")
        QMessageBox.critical(self, "ข้อผิดพลาด", error_message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
