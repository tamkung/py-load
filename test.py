import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
from requests.exceptions import RequestException
from moviepy.editor import VideoFileClip, AudioFileClip

class DownloadThread(threading.Thread):
    def __init__(self, url, save_path, progress_var, status_var):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.progress_var = progress_var
        self.status_var = status_var
        self._stop_event = threading.Event()

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
                        if self._stop_event.is_set():
                            self.status_var.set("ยกเลิกการดาวน์โหลด")
                            return
                            
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = int((downloaded / total_size) * 100)
                                self.progress_var.set(progress)
                                self.status_var.set(f"กำลังดาวน์โหลด: {progress}%")

            if not self._stop_event.is_set():
                self.status_var.set("ดาวน์โหลดเสร็จสิ้น")
                messagebox.showinfo("สำเร็จ", "ดาวน์โหลดเสร็จสิ้น")

        except RequestException as e:
            if not self._stop_event.is_set():
                self.status_var.set("เกิดข้อผิดพลาด")
                messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการดาวน์โหลด: {str(e)}")

    def stop(self):
        self._stop_event.set()

class MergeThread(threading.Thread):
    def __init__(self, video_path, audio_path, output_path, status_var):
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_path = output_path
        self.status_var = status_var
        self._stop_event = threading.Event()

    def run(self):
        try:
            video_clip = VideoFileClip(self.video_path)
            audio_clip = AudioFileClip(self.audio_path)
            
            if self._stop_event.is_set():
                self.status_var.set("ยกเลิกการรวมไฟล์")
                return
                
            video_clip = video_clip.set_audio(audio_clip)
            
            if self._stop_event.is_set():
                self.status_var.set("ยกเลิกการรวมไฟล์")
                return
                
            video_clip.write_videofile(self.output_path, codec="libx264", audio_codec="aac", audio_bitrate="111k", audio_fps=48000)
            
            video_clip.close()
            audio_clip.close()
            
            if not self._stop_event.is_set():
                self.status_var.set("รวมไฟล์เสร็จสิ้น")
                messagebox.showinfo("สำเร็จ", "รวมไฟล์เสร็จสิ้น")

        except Exception as e:
            if not self._stop_event.is_set():
                self.status_var.set("เกิดข้อผิดพลาด")
                messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการรวมไฟล์: {str(e)}")

    def stop(self):
        self._stop_event.set()

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("โปรแกรมรวมไฟล์วิดีโอและเสียง")
        self.root.geometry("800x600")

        # สร้างเฟรมหลัก
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ส่วนดาวน์โหลดวิดีโอ
        video_frame = ttk.LabelFrame(main_frame, text="ดาวน์โหลดวิดีโอ", padding="5")
        video_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(video_frame, text="URL วิดีโอ:").grid(row=0, column=0, sticky=tk.W)
        self.video_url = ttk.Entry(video_frame, width=50)
        self.video_url.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        self.video_progress_var = tk.IntVar()
        self.video_progress = ttk.Progressbar(video_frame, length=300, mode='determinate', variable=self.video_progress_var)
        self.video_progress.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.video_status_var = tk.StringVar()
        ttk.Label(video_frame, textvariable=self.video_status_var).grid(row=2, column=1, sticky=tk.W)

        button_frame = ttk.Frame(video_frame)
        button_frame.grid(row=3, column=1, sticky=(tk.W, tk.E))
        self.video_download_btn = ttk.Button(button_frame, text="ดาวน์โหลดวิดีโอ", command=lambda: self.download_file("video"))
        self.video_download_btn.pack(side=tk.LEFT, padx=5)
        self.video_cancel_btn = ttk.Button(button_frame, text="ยกเลิก", command=lambda: self.cancel_download("video"), state=tk.DISABLED)
        self.video_cancel_btn.pack(side=tk.LEFT)

        # ส่วนดาวน์โหลดเสียง
        audio_frame = ttk.LabelFrame(main_frame, text="ดาวน์โหลดเสียง", padding="5")
        audio_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(audio_frame, text="URL เสียง:").grid(row=0, column=0, sticky=tk.W)
        self.audio_url = ttk.Entry(audio_frame, width=50)
        self.audio_url.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        self.audio_progress_var = tk.IntVar()
        self.audio_progress = ttk.Progressbar(audio_frame, length=300, mode='determinate', variable=self.audio_progress_var)
        self.audio_progress.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.audio_status_var = tk.StringVar()
        ttk.Label(audio_frame, textvariable=self.audio_status_var).grid(row=2, column=1, sticky=tk.W)

        button_frame = ttk.Frame(audio_frame)
        button_frame.grid(row=3, column=1, sticky=(tk.W, tk.E))
        self.audio_download_btn = ttk.Button(button_frame, text="ดาวน์โหลดเสียง", command=lambda: self.download_file("audio"))
        self.audio_download_btn.pack(side=tk.LEFT, padx=5)
        self.audio_cancel_btn = ttk.Button(button_frame, text="ยกเลิก", command=lambda: self.cancel_download("audio"), state=tk.DISABLED)
        self.audio_cancel_btn.pack(side=tk.LEFT)

        # ส่วนรวมไฟล์
        merge_frame = ttk.LabelFrame(main_frame, text="รวมไฟล์", padding="5")
        merge_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(merge_frame, text="ไฟล์วิดีโอ:").grid(row=0, column=0, sticky=tk.W)
        self.video_path = ttk.Entry(merge_frame, width=50)
        self.video_path.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(merge_frame, text="เลือกไฟล์", command=lambda: self.select_file("video")).grid(row=0, column=2)

        ttk.Label(merge_frame, text="ไฟล์เสียง:").grid(row=1, column=0, sticky=tk.W)
        self.audio_path = ttk.Entry(merge_frame, width=50)
        self.audio_path.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(merge_frame, text="เลือกไฟล์", command=lambda: self.select_file("audio")).grid(row=1, column=2)

        self.merge_status_var = tk.StringVar()
        ttk.Label(merge_frame, textvariable=self.merge_status_var).grid(row=2, column=1, sticky=tk.W)

        button_frame = ttk.Frame(merge_frame)
        button_frame.grid(row=3, column=1, sticky=(tk.W, tk.E))
        self.merge_btn = ttk.Button(button_frame, text="รวมไฟล์", command=self.merge_files)
        self.merge_btn.pack(side=tk.LEFT, padx=5)
        self.merge_cancel_btn = ttk.Button(button_frame, text="ยกเลิกและปิดโปรแกรม", command=self.cancel_merge, state=tk.DISABLED)
        self.merge_cancel_btn.pack(side=tk.LEFT)

        # ตัวแปรสำหรับเก็บ thread
        self.video_thread = None
        self.audio_thread = None
        self.merge_thread = None

    def download_file(self, file_type):
        url_entry = self.video_url if file_type == "video" else self.audio_url
        progress_var = self.video_progress_var if file_type == "video" else self.audio_progress_var
        status_var = self.video_status_var if file_type == "video" else self.audio_status_var
        download_btn = self.video_download_btn if file_type == "video" else self.audio_download_btn
        cancel_btn = self.video_cancel_btn if file_type == "video" else self.audio_cancel_btn
        
        url = url_entry.get()
        if not url:
            messagebox.showwarning("คำเตือน", f"กรุณาใส่ URL {file_type}")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")],
            title=f"บันทึกไฟล์ {file_type}"
        )
        if not save_path:
            return

        progress_var.set(0)
        status_var.set("กำลังดาวน์โหลด...")
        download_btn.config(state=tk.DISABLED)
        cancel_btn.config(state=tk.NORMAL)

        thread = DownloadThread(url, save_path, progress_var, status_var)
        if file_type == "video":
            self.video_thread = thread
        else:
            self.audio_thread = thread
        thread.start()

    def cancel_download(self, file_type):
        thread = self.video_thread if file_type == "video" else self.audio_thread
        if thread:
            thread.stop()
            
        download_btn = self.video_download_btn if file_type == "video" else self.audio_download_btn
        cancel_btn = self.video_cancel_btn if file_type == "video" else self.audio_cancel_btn
        download_btn.config(state=tk.NORMAL)
        cancel_btn.config(state=tk.DISABLED)

    def select_file(self, file_type):
        file_path = filedialog.askopenfilename(
            filetypes=[("MP4 files", "*.mp4")],
            title=f"เลือกไฟล์ {file_type}"
        )
        if file_path:
            if file_type == "video":
                self.video_path.delete(0, tk.END)
                self.video_path.insert(0, file_path)
            else:
                self.audio_path.delete(0, tk.END)
                self.audio_path.insert(0, file_path)

    def merge_files(self):
        video_path = self.video_path.get()
        audio_path = self.audio_path.get()

        if not video_path or not audio_path:
            messagebox.showwarning("คำเตือน", "กรุณาเลือกไฟล์วิดีโอและเสียง")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")],
            title="บันทึกไฟล์ผลลัพธ์"
        )
        if not output_path:
            return

        self.merge_status_var.set("กำลังรวมไฟล์...")
        self.merge_btn.config(state=tk.DISABLED)
        self.merge_cancel_btn.config(state=tk.NORMAL)

        self.merge_thread = MergeThread(video_path, audio_path, output_path, self.merge_status_var)
        self.merge_thread.start()

    def cancel_merge(self):
        if self.merge_thread:
            self.merge_thread.stop()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop() 