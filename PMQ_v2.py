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
        self.root.title("مراقبة جودة البث - شبكة المجد")
        self.root.geometry("1200x900")
        self.root.configure(bg="#1a1a1a")
        
        # Initialize VLC components
        self.vlc_instance = vlc.Instance(['--intf', 'dummy'])
        self.player = self.vlc_instance.media_player_new()
        
        # Variables
        self.ts_file = None
        self.channels = []
        self.timer_thread = None
        self.stop_timer = False
        self.video_frame = None
        
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
        # Main container with two panels
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1a1a1a", 
                                       sashrelief=tk.RAISED, sashwidth=5)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for controls
        left_panel = tk.Frame(main_container, bg="#1a1a1a", width=500)
        main_container.add(left_panel, minsize=450)
        
        # Right panel for video player
        right_panel = tk.Frame(main_container, bg="#000000", width=700)
        main_container.add(right_panel, minsize=600)
        
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)
        
    def setup_left_panel(self, parent):
        # Scrollable frame for left panel
        canvas = tk.Canvas(parent, bg="#1a1a1a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#1a1a1a")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Title
        tk.Label(scrollable_frame, text="مراقبة جودة البث - شبكة المجد", 
                font=("Arial", 16, "bold"), bg="#1a1a1a", fg="#ffffff").pack(pady=(10, 15))
        
        # File selection
        file_frame = tk.Frame(scrollable_frame, bg="#1a1a1a")
        file_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        tk.Button(file_frame, text="اختيار ملف", font=("Arial", 11), bg="#404040", 
                 fg="white", command=self.browse_file).pack(side=tk.LEFT)
        
        self.file_label = tk.Label(file_frame, text="لا يوجد ملف محدد", 
                                  font=("Arial", 10), bg="#1a1a1a", fg="#cccccc")
        self.file_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Analysis buttons
        test_frame = tk.Frame(scrollable_frame, bg="#1a1a1a")
        test_frame.pack(pady=10, padx=10)
        
        tk.Button(test_frame, text="تحليل القنوات", font=("Arial", 10), 
                 bg="#404040", fg="white", command=self.analyze_channels).pack(side=tk.LEFT, padx=3)
        
        tk.Button(test_frame, text="اختبار الملف والنظام", font=("Arial", 10), 
                 bg="#404040", fg="white", command=self.test_system).pack(side=tk.LEFT, padx=3)
        
        # Channel list
        channel_frame = tk.LabelFrame(scrollable_frame, text="القنوات المتاحة", 
                                     font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#ffffff")
        channel_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.channel_listbox = tk.Listbox(channel_frame, height=4, bg="#2d2d2d", 
                                         fg="#ffffff", font=("Arial", 10), selectbackground="#404040")
        self.channel_listbox.pack(fill=tk.X, padx=5, pady=5)
        self.channel_listbox.bind('<Double-Button-1>', self.play_selected_channel)
        
        # Manual controls
        manual_frame = tk.LabelFrame(scrollable_frame, text="تشغيل القناة", 
                                    font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#ffffff")
        manual_frame.pack(fill=tk.X, pady=15, padx=10)
        
        # Input controls
        input_frame = tk.Frame(manual_frame, bg="#1a1a1a")
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text="رقم القناة:", bg="#1a1a1a", fg="#ffffff").grid(row=0, column=0, padx=5)
        self.channel_entry = tk.Entry(input_frame, width=8, justify='center', bg="#2d2d2d", 
                                     fg="white", insertbackground="white")
        self.channel_entry.grid(row=0, column=1, padx=5)
        self.channel_entry.insert(0, "0")
        
        tk.Label(input_frame, text="المدة (ثانية):", bg="#1a1a1a", fg="#ffffff").grid(row=0, column=2, padx=5)
        self.duration_entry = tk.Entry(input_frame, width=8, justify='center', bg="#2d2d2d", 
                                      fg="white", insertbackground="white")
        self.duration_entry.grid(row=0, column=3, padx=5)
        self.duration_entry.insert(0, "0")
        
        # Volume control
        volume_frame = tk.Frame(manual_frame, bg="#1a1a1a")
        volume_frame.pack(pady=5)
        
        tk.Label(volume_frame, text="الصوت:", bg="#1a1a1a", fg="#ffffff").pack(side=tk.LEFT, padx=5)
        self.volume_var = tk.IntVar(value=80)
        tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.volume_var,
                bg="#1a1a1a", fg="#ffffff", troughcolor="#404040", length=150, 
                command=self.change_volume).pack(side=tk.LEFT, padx=5)
        
        # Quick channel buttons
        quick_frame = tk.Frame(manual_frame, bg="#1a1a1a")
        quick_frame.pack(pady=5)
        
        tk.Label(quick_frame, text="قنوات سريعة:", bg="#1a1a1a", fg="#ffffff").pack(side=tk.LEFT, padx=5)
        for i in range(1, 6):
            tk.Button(quick_frame, text=str(i), font=("Arial", 9), bg="#404040", fg="white", 
                     width=3, command=lambda ch=i: self.quick_channel(ch)).pack(side=tk.LEFT, padx=2)
        
        # Control buttons
        buttons_frame = tk.Frame(manual_frame, bg="#1a1a1a")
        buttons_frame.pack(pady=10)
        
        tk.Button(buttons_frame, text="تشغيل", font=("Arial", 10), bg="#008000", 
                 fg="white", command=self.play_channel, width=8).grid(row=0, column=0, padx=3)
        
        tk.Button(buttons_frame, text="إيقاف", font=("Arial", 10), bg="#800000", 
                 fg="white", command=self.stop_playback, width=8).grid(row=0, column=1, padx=3)
        
        tk.Button(buttons_frame, text="إيقاف مؤقت", font=("Arial", 9), bg="#404040", 
                 fg="white", command=self.pause_playback, width=8).grid(row=0, column=2, padx=3)
        
        tk.Button(buttons_frame, text="متابعة", font=("Arial", 10), bg="#404040", 
                 fg="white", command=self.resume_playback, width=8).grid(row=1, column=0, padx=3, pady=3)
        
        tk.Button(buttons_frame, text="استخراج القناة", font=("Arial", 9), bg="#404040", 
                 fg="white", command=self.extract_channel, width=12).grid(row=1, column=1, columnspan=2, padx=3, pady=3)
        
        # Status
        self.status_label = tk.Label(scrollable_frame, text="جاهز", 
                                    font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#00ff00")
        self.status_label.pack(pady=10)
        
        # Log
        log_frame = tk.LabelFrame(scrollable_frame, text="سجل الأحداث", bg="#1a1a1a", fg="#ffffff")
        log_frame.pack(fill=tk.X, expand=True, pady=10, padx=10)
        
        log_controls = tk.Frame(log_frame, bg="#1a1a1a")
        log_controls.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(log_controls, text="مسح السجل", font=("Arial", 9), bg="#404040", 
                 fg="white", command=self.clear_log).pack(side=tk.RIGHT)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, bg="#2d2d2d", 
                                                 fg="#ffffff", font=("Courier", 9), insertbackground="white")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Load last file if exists
        if self.last_file and os.path.exists(self.last_file):
            self.ts_file = self.last_file
            self.file_label.config(text=f"الملف: {os.path.basename(self.last_file)}")
            self.log_message(f"تم تحميل آخر ملف: {os.path.basename(self.last_file)}")

    def setup_right_panel(self, parent):
        # Video player frame
        video_container = tk.Frame(parent, bg="#000000")
        video_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Title for video panel
        tk.Label(video_container, text="شاشة العرض", font=("Arial", 14, "bold"), 
                bg="#000000", fg="#ffffff").pack(pady=(5, 10))
        
        # Video frame
        self.video_frame = tk.Frame(video_container, bg="#000000", relief=tk.SUNKEN, bd=2)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Video info label
        self.video_info_label = tk.Label(video_container, 
                                        text="اختر ملف وقناة لبدء التشغيل", 
                                        font=("Arial", 12), bg="#000000", fg="#888888")
        self.video_info_label.pack(pady=5)
        
        # Playback controls
        controls_frame = tk.Frame(video_container, bg="#000000")
        controls_frame.pack(pady=10)
        
        tk.Button(controls_frame, text="⏪", font=("Arial", 16), bg="#404040", fg="white",
                 command=self.seek_backward, width=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(controls_frame, text="⏯️", font=("Arial", 16), bg="#404040", fg="white",
                 command=self.toggle_play_pause, width=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(controls_frame, text="⏩", font=("Arial", 16), bg="#404040", fg="white",
                 command=self.seek_forward, width=3).pack(side=tk.LEFT, padx=5)
        
        tk.Button(controls_frame, text="⏹️", font=("Arial", 16), bg="#800000", fg="white",
                 command=self.stop_playback, width=3).pack(side=tk.LEFT, padx=5)

    def setup_vlc_player(self):
        """Setup VLC player to embed in tkinter frame"""
        try:
            # Get the window handle/ID of the video frame
            if platform.system() == "Windows":
                self.video_frame.update()
                wid = self.video_frame.winfo_id()
                self.player.set_hwnd(wid)
            elif platform.system() == "Linux":
                self.video_frame.update()
                wid = self.video_frame.winfo_id()
                self.player.set_xwindow(wid)
            elif platform.system() == "Darwin":  # macOS
                self.video_frame.update()
                wid = self.video_frame.winfo_id()
                self.player.set_nsobject(wid)
            
            self.log_message("✓ تم إعداد مشغل الفيديو المدمج")
            
        except Exception as e:
            self.log_message(f"⚠️ خطأ في إعداد المشغل المدمج: {str(e)}")

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
        
        # Try multiple analysis methods
        found = False
        
        # Method 1: TSDuck analyze
        if self.analyze_with_tsduck_analyze():
            found = True
        # Method 2: TSDuck psi
        elif self.analyze_with_tsduck_psi():
            found = True
        # Method 3: FFprobe
        elif self.analyze_with_ffprobe():
            found = True
        # Method 4: Simple program scan
        else:
            self.simple_program_scan()
            found = True
        
        if self.channels:
            self.log_message(f"✓ تم العثور على {len(self.channels)} قناة/برنامج")
        else:
            self.log_message("⚠️ لم يتم العثور على قنوات - جرب التشغيل المباشر")

    def analyze_with_tsduck_analyze(self):
        """استخدام TSDuck analyze command"""
        try:
            test_cmd = ['tsp', '--version']
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                self.log_message("TSDuck غير متاح")
                return False
                
            self.log_message("جاري التحليل بـ TSDuck analyze...")
            
            cmd = ['tsp', '-I', 'file', self.ts_file, '-P', 'analyze', '--service-list', '-O', 'drop']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                output = result.stdout + "\n" + result.stderr
                return self.parse_tsduck_analyze_output(output)
            else:
                self.log_message("فشل تحليل TSDuck analyze")
                return False
                
        except Exception as e:
            self.log_message(f"خطأ في TSDuck: {str(e)}")
            return False

    def analyze_with_tsduck_psi(self):
        """استخدام TSDuck PSI command"""
        try:
            self.log_message("جاري التحليل بـ TSDuck psi...")
            
            cmd = ['tsp', '-I', 'file', self.ts_file, '-P', 'psi', '--service-list', '-O', 'drop']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                output = result.stdout + "\n" + result.stderr
                return self.parse_tsduck_psi_output(output)
            else:
                self.log_message("فشل تحليل TSDuck PSI")
                return False
                
        except Exception as e:
            self.log_message(f"خطأ في TSDuck PSI: {str(e)}")
            return False

    def parse_tsduck_analyze_output(self, output):
        """تحليل مخرجات TSDuck analyze"""
        found = False
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            service_match = re.search(r'Service:\s+0x[0-9a-fA-F]+\s+\((\d+)\).*?name:\s*["\']([^"\']*)["\']', line, re.IGNORECASE)
            if service_match:
                service_id = int(service_match.group(1))
                service_name = service_match.group(2).strip()
                if service_id > 0:
                    self.channels.append({'id': service_id, 'name': service_name or f"قناة {service_id}"})
                    self.channel_listbox.insert(tk.END, f"قناة {service_id}: {service_name}")
                    found = True
                continue
            
            service_match2 = re.search(r'Service\s+(\d+).*?["\']([^"\']*)["\']', line, re.IGNORECASE)
            if service_match2:
                service_id = int(service_match2.group(1))
                service_name = service_match2.group(2).strip()
                if service_id > 0:
                    self.channels.append({'id': service_id, 'name': service_name or f"قناة {service_id}"})
                    self.channel_listbox.insert(tk.END, f"قناة {service_id}: {service_name}")
                    found = True
                continue
            
            program_match = re.search(r'Program:\s+(\d+)', line, re.IGNORECASE)
            if program_match:
                prog_id = int(program_match.group(1))
                if prog_id > 0:
                    self.channels.append({'id': prog_id, 'name': f"برنامج {prog_id}"})
                    self.channel_listbox.insert(tk.END, f"برنامج {prog_id}")
                    found = True
        
        return found

    def parse_tsduck_psi_output(self, output):
        """تحليل مخرجات TSDuck PSI"""
        found = False
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'service' in line.lower() and ('id' in line.lower() or 'name' in line.lower()):
                id_match = re.search(r'(\d+)', line)
                if id_match:
                    service_id = int(id_match.group(1))
                    if service_id > 0:
                        name_match = re.search(r'["\']([^"\']*)["\']', line)
                        service_name = name_match.group(1) if name_match else f"قناة {service_id}"
                        
                        self.channels.append({'id': service_id, 'name': service_name})
                        self.channel_listbox.insert(tk.END, f"قناة {service_id}: {service_name}")
                        found = True
        
        return found

    def analyze_with_ffprobe(self):
        """استخدام FFprobe للتحليل"""
        try:
            self.log_message("جاري التحليل بـ FFprobe...")
            
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_programs', self.ts_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            found = False
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    programs = data.get('programs', [])
                    
                    for program in programs:
                        prog_id = program.get('program_id')
                        if prog_id and prog_id > 0:
                            prog_name = program.get('program_name', f"برنامج {prog_id}")
                            self.channels.append({'id': prog_id, 'name': prog_name})
                            self.channel_listbox.insert(tk.END, f"برنامج {prog_id}: {prog_name}")
                            found = True
                    
                    if found:
                        return True
                        
                except json.JSONDecodeError:
                    pass
            
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', self.ts_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    streams = data.get('streams', [])
                    
                    programs = set()
                    for stream in streams:
                        prog_id = stream.get('program_num')
                        if prog_id and prog_id > 0:
                            programs.add(prog_id)
                    
                    for prog_id in sorted(programs):
                        self.channels.append({'id': prog_id, 'name': f"برنامج {prog_id}"})
                        self.channel_listbox.insert(tk.END, f"برنامج {prog_id}")
                        found = True
                        
                except json.JSONDecodeError:
                    pass
            
            return found
            
        except Exception as e:
            self.log_message(f"خطأ في FFprobe: {str(e)}")
            return False

    def simple_program_scan(self):
        """فحص بسيط للبرامج الشائعة"""
        self.log_message("فحص البرامج الشائعة...")
        
        common_programs = [1, 100, 101, 102, 103, 104, 105, 200, 201, 300, 400, 500]
        
        for prog_id in common_programs:
            self.channels.append({'id': prog_id, 'name': f"برنامج {prog_id}"})
            self.channel_listbox.insert(tk.END, f"برنامج {prog_id}")
        
        self.log_message("تمت إضافة البرامج الشائعة - جرب تشغيل كل برنامج")

    def test_system(self):
        self.log_message("=== اختبار النظام ===")
        
        # Test VLC
        try:
            version = vlc.libvlc_get_version().decode('utf-8')
            self.log_message(f"✓ VLC متاح - الإصدار: {version}")
        except:
            self.log_message("✗ VLC غير متاح")
            
        # Test TSDuck
        try:
            result = subprocess.run(['tsp', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_match = re.search(r'TSDuck\s+(\d+\.\d+)', result.stderr)
                version = version_match.group(1) if version_match else "غير معروف"
                self.log_message(f"✓ TSDuck متاح - الإصدار: {version}")
            else:
                self.log_message("✗ TSDuck غير متاح")
        except:
            self.log_message("✗ TSDuck غير مثبت")
            
        # Test FFprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log_message("✓ FFprobe متاح")
            else:
                self.log_message("✗ FFprobe غير متاح")
        except:
            self.log_message("✗ FFprobe غير مثبت")
            
        # Test file
        if self.ts_file and os.path.exists(self.ts_file):
            size_mb = os.path.getsize(self.ts_file) / (1024 * 1024)
            self.log_message(f"✓ الملف موجود - الحجم: {size_mb:.1f} MB")
        else:
            self.log_message("✗ لا يوجد ملف محدد")

    def quick_channel(self, channel_num):
        self.channel_entry.delete(0, tk.END)
        self.channel_entry.insert(0, str(channel_num))

    def play_selected_channel(self, event=None):
        selection = self.channel_listbox.curselection()
        if selection and self.channels:
            channel = self.channels[selection[0]]
            self.channel_entry.delete(0, tk.END)
            self.channel_entry.insert(0, str(channel['id']))
            self.play_channel()

    def play_channel(self):
        if not self.ts_file:
            messagebox.showerror("خطأ", "اختر ملف أولاً")
            return
            
        try:
            channel_num = int(self.channel_entry.get())
            duration = int(self.duration_entry.get())
        except ValueError:
            messagebox.showerror("خطأ", "أدخل أرقام صحيحة")
            return
            
        self.log_message(f"تشغيل القناة {channel_num}")
        
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
            
            result = self.player.play()
            if result == 0:
                self.status_label.config(text=f"يتم تشغيل القناة {channel_num}", fg="#00ff00")
                self.video_info_label.config(text=f"القناة {channel_num} - جاري التشغيل...")
                self.log_message("✓ بدأ التشغيل في المشغل المدمج")
                
                if duration > 0:
                    self.start_timer(duration)
            else:
                self.log_message("✗ فشل التشغيل")
                self.status_label.config(text="فشل التشغيل", fg="#ff0000")
                
        except Exception as e:
            self.log_message(f"خطأ: {str(e)}")
            self.status_label.config(text="خطأ في التشغيل", fg="#ff0000")

    def extract_channel(self):
        if not self.ts_file:
            messagebox.showerror("خطأ", "اختر ملف أولاً")
            return
            
        try:
            channel_num = int(self.channel_entry.get())
        except ValueError:
            messagebox.showerror("خطأ", "أدخل رقم القناة")
            return
            
        output_file = filedialog.asksaveasfilename(
            title="حفظ القناة",
            defaultextension=".ts",
            filetypes=[("Transport Stream", "*.ts")]
        )
        
        if not output_file:
            return
            
        self.log_message(f"استخراج القناة {channel_num}...")
        
        try:
            cmd = ['tsp', '-I', 'file', self.ts_file, '-P', 'zap', str(channel_num), '-O', 'file', output_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                self.log_message(f"✓ تم استخراج القناة إلى: {os.path.basename(output_file)}")
            else:
                self.log_message("✗ فشل الاستخراج")
                
        except subprocess.TimeoutExpired:
            self.log_message("✗ انتهت مهلة الاستخراج")
        except FileNotFoundError:
            self.log_message("✗ TSDuck غير متاح للاستخراج")
        except Exception as e:
            self.log_message(f"خطأ: {str(e)}")

    def change_volume(self, value):
        try:
            if self.player:
                self.player.audio_set_volume(int(value))
        except:
            pass

    def toggle_play_pause(self):
        """Toggle between play and pause"""
        try:
            if self.player.is_playing():
                self.pause_playback()
            else:
                self.resume_playback()
        except:
            pass

    def pause_playback(self):
        try:
            if self.player and self.player.is_playing():
                self.player.pause()
                self.log_message("تم الإيقاف المؤقت")
                self.status_label.config(text="متوقف مؤقتاً", fg="#ffff00")
                self.video_info_label.config(text="متوقف مؤقتاً")
        except:
            pass

    def resume_playback(self):
        try:
            if self.player:
                self.player.play()
                self.log_message("تم استئناف التشغيل")
                self.status_label.config(text="جاري التشغيل", fg="#00ff00")
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
        """Seek forward 30 seconds"""
        try:
            if self.player and self.player.is_playing():
                current_time = self.player.get_time()
                new_time = current_time + 30000  # 30 seconds in milliseconds
                self.player.set_time(new_time)
                self.log_message("تقديم 30 ثانية")
        except:
            pass

    def seek_backward(self):
        """Seek backward 30 seconds"""
        try:
            if self.player and self.player.is_playing():
                current_time = self.player.get_time()
                new_time = max(0, current_time - 30000)  # 30 seconds backward
                self.player.set_time(new_time)
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
    
    # Make window resizable
    root.minsize(1000, 700)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()