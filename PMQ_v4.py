import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import vlc
import subprocess
import threading
import os
import time
import json
import re
import platform

class TSChannelPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("مراقبة جودة البث ")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1a1a1a")
        
        # Initialize VLC
        self.vlc_instance = vlc.Instance(['--intf', 'dummy'])
        self.player = self.vlc_instance.media_player_new()
        
        # Variables
        self.ts_file = None
        self.channels = []
        self.timer_thread = None
        self.stop_timer = False
        self.video_frame = None
        self.current_channel = None  # لحفظ القناة المشغلة حالياً
        
        self.load_config()
        self.setup_ui()
        self.setup_vlc_player()
        
    def load_config(self):
        try:
            if os.path.exists("player_config.json"):
                with open("player_config.json", 'r', encoding='utf-8') as f:
                    self.last_file = json.load(f).get('last_file', '')
            else:
                self.last_file = ''
        except:
            self.last_file = ''
    
    def save_config(self):
        try:
            with open("player_config.json", 'w', encoding='utf-8') as f:
                json.dump({'last_file': self.ts_file or ''}, f, ensure_ascii=False)
        except:
            pass

    def setup_ui(self):
        main_container = tk.Frame(self.root, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        top_section = tk.Frame(main_container, bg="#1a1a1a")
        top_section.pack(fill=tk.BOTH, expand=True)
        
        left_panel = tk.Frame(top_section, bg="#1a1a1a", width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        right_panel = tk.Frame(top_section, bg="#000000")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)
        self.setup_log_panel(main_container)
        
    def setup_left_panel(self, parent):
        tk.Label(parent, text="مراقبة جودة البث ", 
                font=("Arial", 14, "bold"), bg="#1a1a1a", fg="#ffffff").pack(pady=(10, 15))
        
        file_frame = tk.Frame(parent, bg="#1a1a1a")
        file_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        tk.Button(file_frame, text="اختيار ملف", font=("Arial", 13, "bold"), bg="#404040", 
                 fg="white", command=self.browse_file).pack(side=tk.LEFT)
        
        self.file_label = tk.Label(file_frame, text="لا يوجد ملف محدد", 
                                  font=("Arial", 10), bg="#1a1a1a", fg="#cccccc", wraplength=250)
        self.file_label.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(parent, text="تحليل القنوات", font=("Arial", 13, "bold"), 
                 bg="#0066cc", fg="white", command=self.analyze_channels, width=20).pack(pady=10)
        
        channel_frame = tk.LabelFrame(parent, text="القنوات المتاحة", 
                                     font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#ffffff")
        channel_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        list_frame = tk.Frame(channel_frame, bg="#1a1a1a")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_channels = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar_channels.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.channel_listbox = tk.Listbox(list_frame, bg="#2d2d2d", 
                                         fg="#ffffff", font=("Arial", 12, "bold"), selectbackground="#0066cc",
                                         activestyle='dotbox', yscrollcommand=scrollbar_channels.set)
        self.channel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_channels.config(command=self.channel_listbox.yview)
        
        self.channel_listbox.bind('<Double-Button-1>', self.play_selected_channel)
        self.channel_listbox.bind('<Button-1>', self.on_channel_select)
        
        control_frame = tk.LabelFrame(parent, text="تشغيل القناة", 
                                    font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#ffffff")
        control_frame.pack(fill=tk.X, pady=15, padx=10)
        
        duration_frame = tk.Frame(control_frame, bg="#1a1a1a")
        duration_frame.pack(pady=10)
        
        tk.Label(duration_frame, text="المدة (ثانية):", bg="#1a1a1a", fg="#ffffff", font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 5))
        self.duration_entry = tk.Entry(duration_frame, width=8, justify='center', bg="#2d2d2d", 
                                      fg="white", insertbackground="white", font=("Arial", 11))
        self.duration_entry.pack(side=tk.LEFT, padx=5)
        self.duration_entry.insert(0, "0")
        
        volume_frame = tk.Frame(control_frame, bg="#1a1a1a")
        volume_frame.pack(pady=5)
        
        self.volume_var = tk.IntVar(value=80)
        tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.volume_var,
                bg="#1a1a1a", fg="#ffffff", troughcolor="#404040", length=200, 
                command=self.change_volume, font=("Arial", 10)).pack()
        
        tk.Button(control_frame, text="استخراج القناة", font=("Arial", 12, "bold"), bg="#404040", 
                 fg="white", command=self.extract_channel, width=15).pack(pady=10)
        
        self.status_label = tk.Label(parent, text="جاهز", 
                                    font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#00ff00")
        self.status_label.pack(pady=10)

    def setup_right_panel(self, parent):
        video_container = tk.Frame(parent, bg="#000000")
        video_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(video_container, text="شاشة العرض", font=("Arial", 14, "bold"), 
                bg="#000000", fg="#ffffff").pack(pady=(5, 10))
        
        self.video_frame = tk.Frame(video_container, bg="#000000", relief=tk.SUNKEN, bd=2)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.video_info_label = tk.Label(video_container, 
                                        text="اختر ملف وقناة لبدء التشغيل", 
                                        font=("Arial", 12), bg="#000000", fg="#888888")
        self.video_info_label.pack(pady=5)
        
        controls_frame = tk.Frame(video_container, bg="#000000")
        controls_frame.pack(pady=15)
        
        btn_style = {"font": ("Arial", 14), "bg": "#808080", "fg": "white", "width": 3, "height": 1}
        
        tk.Button(controls_frame, text="⏪", command=self.seek_backward, **btn_style).pack(side=tk.LEFT, padx=8)
        tk.Button(controls_frame, text="▶️", command=self.play_channel, **btn_style).pack(side=tk.LEFT, padx=8)
        tk.Button(controls_frame, text="⏸️", command=self.pause_playback, **btn_style).pack(side=tk.LEFT, padx=8)
        tk.Button(controls_frame, text="⏩", command=self.seek_forward, **btn_style).pack(side=tk.LEFT, padx=8)
        tk.Button(controls_frame, text="⏹️", command=self.stop_playback, **btn_style).pack(side=tk.LEFT, padx=8)

    def setup_log_panel(self, parent):
        log_frame = tk.LabelFrame(parent, text="سجل الأحداث", 
                                 font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#ffffff")
        log_frame.pack(fill=tk.X, pady=(10, 0), padx=10)
        
        log_controls = tk.Frame(log_frame, bg="#1a1a1a")
        log_controls.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(log_controls, text="مسح السجل", font=("Arial", 9), bg="#404040", 
                 fg="white", command=self.clear_log).pack(side=tk.RIGHT)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, bg="#2d2d2d", 
                                                 fg="#ffffff", font=("Courier", 9), insertbackground="white")
        self.log_text.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        if self.last_file and os.path.exists(self.last_file):
            self.ts_file = self.last_file
            self.file_label.config(text=f"الملف: {os.path.basename(self.last_file)}")
            self.log_message(f"تم تحميل آخر ملف: {os.path.basename(self.last_file)}")

    def setup_vlc_player(self):
        try:
            if platform.system() == "Windows":
                self.video_frame.update()
                self.player.set_hwnd(self.video_frame.winfo_id())
            elif platform.system() == "Linux":
                self.video_frame.update()
                self.player.set_xwindow(self.video_frame.winfo_id())
            elif platform.system() == "Darwin":
                self.video_frame.update()
                self.player.set_nsobject(self.video_frame.winfo_id())
            
            self.log_message("✓ تم إعداد مشغل الفيديو المدمج")
        except Exception as e:
            self.log_message(f"⚠️ خطأ في إعداد المشغل: {str(e)}")

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="اختيار ملف Transport Stream",
            filetypes=[("Transport Stream", "*.ts"), ("Video files", "*.ts *.m2ts *.mts"), ("All files", "*.*")]
        )
        if file_path:
            self.ts_file = file_path
            self.file_label.config(text=f"الملف: {os.path.basename(file_path)}")
            self.log_message(f"تم اختيار الملف: {os.path.basename(file_path)}")
            self.save_config()

    def analyze_channels(self):
        if not self.ts_file:
            messagebox.showerror("خطأ", "اختر ملف أولاً")
            return
            
        self.log_message("=== بدء التحليل ===")
        self.channels = []
        self.channel_listbox.delete(0, tk.END)
        
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_programs', self.ts_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for program in data.get("programs", []):
                    prog_id = program.get("program_id")
                    tags = program.get("tags", {})
                    prog_name = tags.get("service_name") or f"قناة {prog_id}"
                    if prog_id:
                        self.channels.append({"id": prog_id, "name": prog_name})
                        self.channel_listbox.insert(tk.END, f"{prog_name} ({prog_id})")
        except Exception as e:
            self.log_message(f"خطأ في التحليل: {str(e)}")
        
        if self.channels:
            self.log_message(f"✓ تم العثور على {len(self.channels)} قناة")
        else:
            self.log_message("⚠️ لم يتم العثور على قنوات")

    def on_channel_select(self, event=None):
        selection = self.channel_listbox.curselection()
        if selection and self.channels:
            channel = self.channels[selection[0]]
            self.log_message(f"تم اختيار: {channel['name']} (رقم {channel['id']})")

    def play_selected_channel(self, event=None):
        selection = self.channel_listbox.curselection()
        if selection and self.channels:
            channel = self.channels[selection[0]]
            self.play_channel_by_id(channel['id'], channel['name'])

    def play_channel(self):
        selection = self.channel_listbox.curselection()
        if not selection:
            messagebox.showerror("خطأ", "اختر قناة أولاً")
            return
        channel = self.channels[selection[0]]
        self.play_channel_by_id(channel['id'], channel['name'])

    def play_channel_by_id(self, channel_num, channel_name):
        if not self.ts_file:
            return
        try:
            duration = int(self.duration_entry.get())
        except:
            duration = 0
            
        self.log_message(f"تشغيل {channel_name} ({channel_num})")
        self.current_channel = {"id": channel_num, "name": channel_name}  # حفظ القناة الحالية
        
        try:
            self.stop_timer = True
            if self.player.is_playing():
                self.player.stop()
                time.sleep(0.3)
                
            media = self.vlc_instance.media_new(self.ts_file)
            if channel_num > 0:
                media.add_option(f":program={channel_num}")
                
            self.player.set_media(media)
            self.player.audio_set_volume(self.volume_var.get())
            self.player.play()
            
            self.status_label.config(text=f"يتم تشغيل {channel_name}", fg="#00ff00")
            self.video_info_label.config(text=f"{channel_name} - جاري التشغيل...")
            if duration > 0:
                self.start_timer(duration)
        except Exception as e:
            self.log_message(f"خطأ: {str(e)}")

    def extract_channel(self):
        if not self.current_channel:
            messagebox.showerror("خطأ", "لم يتم تشغيل أي قناة بعد")
            return
        
        channel = self.current_channel
        safe_name = re.sub(r'[^\w\s-]', '', channel['name']).strip()
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        default_filename = f"{safe_name}_{channel['id']}.ts"
        
        output_file = filedialog.asksaveasfilename(
            title="حفظ القناة",
            defaultextension=".ts",
            initialfile=default_filename,
            filetypes=[("Transport Stream", "*.ts")]
        )
        
        if not output_file:
            return
        
        self.log_message(f"استخراج {channel['name']}...")
        try:
            cmd = [
                'ffmpeg', '-i', self.ts_file,
                '-map', f'p:{channel["id"]}',
                '-c', 'copy',
                output_file, '-y'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                self.log_message(f"✓ تم استخراج {channel['name']} إلى {os.path.basename(output_file)}")
            else:
                self.log_message("✗ فشل الاستخراج")
        except Exception as e:
            self.log_message(f"خطأ: {str(e)}")

    def change_volume(self, value):
        try:
            if self.player:
                self.player.audio_set_volume(int(value))
        except:
            pass

    def pause_playback(self):
        try:
            if self.player and self.player.is_playing():
                self.player.pause()
                self.log_message("تم الإيقاف المؤقت")
                self.status_label.config(text="متوقف مؤقتاً", fg="#ffff00")
        except:
            pass

    def stop_playback(self):
        try:
            self.stop_timer = True
            if self.player:
                self.player.stop()
            self.status_label.config(text="تم الإيقاف", fg="#ff8800")
            self.video_info_label.config(text="تم إيقاف التشغيل")
            self.log_message("تم إيقاف التشغيل")
        except:
            pass

    def seek_forward(self):
        try:
            if self.player and self.player.is_playing():
                self.player.set_time(self.player.get_time() + 30000)
                self.log_message("تقديم 30 ثانية")
        except:
            pass

    def seek_backward(self):
        try:
            if self.player and self.player.is_playing():
                self.player.set_time(max(0, self.player.get_time() - 30000))
                self.log_message("تراجع 30 ثانية")
        except:
            pass

    def start_timer(self, duration):
        self.stop_timer = False
        self.timer_thread = threading.Thread(target=self.timer_worker, args=(duration,), daemon=True)
        self.timer_thread.start()
        
    def timer_worker(self, duration):
        for i in range(duration):
            if self.stop_timer:
                return
            remaining = duration - i
            self.root.after(0, lambda r=remaining: self.status_label.config(text=f"متبقي: {r} ثانية", fg="#00ff00"))
            time.sleep(1)
        if not self.stop_timer:
            self.root.after(0, self.stop_playback)

    def on_closing(self):
        try:
            self.stop_timer = True
            if self.player:
                self.player.stop()
                self.player.release()
            if self.vlc_instance:
                self.vlc_instance.release()
        except:
            pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TSChannelPlayer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.minsize(1200, 800)
    root.mainloop()

if __name__ == "__main__":
    main()
