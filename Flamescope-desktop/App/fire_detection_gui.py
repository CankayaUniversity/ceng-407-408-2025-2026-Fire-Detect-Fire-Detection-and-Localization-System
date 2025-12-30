"""
Fire Detection System - Modern GUI Application
Kamera seçimi, izleme, yangın tespiti ve kayıt
"""
import cv2
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime
from pathlib import Path
import json
import os
import queue

from fire_detector import FireDetector


class CameraManager:
    """Kamera yönetimi"""
    
    def __init__(self):
        self.cameras = {}
        self.detectors = {}
        self.fire_events = {}  # {camera_id: {'active': bool, 'start_time': datetime, 'video_writer': VideoWriter, 'frames_buffer': []}}
        
    def add_camera(self, camera_id, rtsp_url):
        """Kamera ekle"""
        self.cameras[camera_id] = {
            'rtsp_url': rtsp_url,
            'cap': None,
            'viewing': False
        }
        self.detectors[camera_id] = FireDetector(model_type="color_enhanced")
        self.fire_events[camera_id] = {
            'active': False,
            'start_time': None,
            'video_writer': None,
            'frames_buffer': [],
            'buffer_size': 150  # ~5 saniye buffer (30fps * 5)
        }
        # NOT: Detection thread'i GUI tarafından başlatılacak (start_detection)
    
    def remove_camera(self, camera_id):
        """Kamera kaldır"""
        if camera_id in self.cameras:
            if self.cameras[camera_id]['cap']:
                self.cameras[camera_id]['cap'].release()
            del self.cameras[camera_id]
            del self.detectors[camera_id]
            if camera_id in self.fire_events:
                if self.fire_events[camera_id]['video_writer']:
                    self.fire_events[camera_id]['video_writer'].release()
                del self.fire_events[camera_id]


class FireDetectionGUI:
    """Modern GUI uygulaması"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 Fire Detection System")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')
        
        # Modern renkler
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#ff4444',
            'secondary': '#2d2d2d',
            'success': '#44ff44',
            'warning': '#ffaa44'
        }
        
        # Klasörler
        self.base_dir = Path("recordings")
        self.base_dir.mkdir(exist_ok=True)
        self.photos_dir = self.base_dir / "photos"
        self.photos_dir.mkdir(exist_ok=True)
        self.fire_videos_dir = self.base_dir / "fire_events"
        self.fire_videos_dir.mkdir(exist_ok=True)
        
        # Kamera yöneticisi
        self.camera_manager = CameraManager()
        
        # Seçili kamera
        self.selected_camera = None
        self.viewing_thread = None
        self.display_thread = None
        self.detection_threads = {}
        self.frame_queue = queue.Queue(maxsize=2)  # Delay'i azaltmak için
        
        # GUI bileşenleri
        self.setup_modern_gui()
        
        # Başlangıç kameraları
        self.add_default_cameras()
        
        # Tüm kameralar için tespit başlat
        self.start_all_detections()
        
    def setup_modern_gui(self):
        """Modern GUI oluştur"""
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])
        style.configure('TButton', padding=10)
        style.map('TButton', background=[('active', self.colors['accent'])])
        
        # Ana container (tüm ekranlar için)
        self.main_container = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Ana menüyü göster
        self.show_main_menu()
    
    def show_main_menu(self):
        """Ana menü ekranını göster"""
        # Önceki ekranı temizle
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Ana menü container
        menu_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        menu_container.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title_frame = tk.Frame(menu_container, bg=self.colors['bg'])
        title_frame.pack(pady=50)
        
        title_label = tk.Label(title_frame, text="🔥 Fire Detection System", 
                              font=("Arial", 32, "bold"),
                              bg=self.colors['bg'], fg=self.colors['accent'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Yangın Tespit ve İzleme Sistemi",
                                 font=("Arial", 16),
                                 bg=self.colors['bg'], fg=self.colors['fg'])
        subtitle_label.pack(pady=10)
        
        # Butonlar
        button_container = tk.Frame(menu_container, bg=self.colors['bg'])
        button_container.pack(pady=50)
        
        # Kamera İzleme butonu
        camera_btn = tk.Button(button_container, text="📹 Kamera İzleme",
                               command=self.show_camera_view,
                               bg=self.colors['accent'], fg='#ffffff',
                               font=("Arial", 18, "bold"),
                               relief=tk.FLAT, padx=40, pady=25,
                               cursor='hand2', width=25)
        camera_btn.pack(pady=20)
        
        # Gallery butonu
        gallery_btn = tk.Button(button_container, text="🖼️ Gallery",
                                command=self.show_gallery_view,
                                bg=self.colors['success'], fg='#ffffff',
                                font=("Arial", 18, "bold"),
                                relief=tk.FLAT, padx=40, pady=25,
                                cursor='hand2', width=25)
        gallery_btn.pack(pady=20)
        
        # Durum bilgisi
        status_frame = tk.Frame(menu_container, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        status_frame.pack(pady=30)
        
        # Detection thread durumu kontrolü
        active_detections = sum(1 for t in self.detection_threads.values() if t.is_alive())
        total_cameras = len(self.camera_manager.cameras)
        status_text = f"✅ System Ready - {active_detections}/{total_cameras} cameras monitoring"
        
        self.status_label = tk.Label(status_frame, text=status_text, 
                                     font=("Arial", 12),
                                     bg=self.colors['secondary'], fg=self.colors['success'],
                                     padx=20, pady=15)
        self.status_label.pack()
        
        # Periyodik olarak detection thread'lerini kontrol et
        self.check_detection_threads()
    
    def show_camera_view(self):
        """Kamera izleme ekranını göster"""
        # Önceki ekranı temizle
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Detection thread'lerinin çalıştığından emin ol
        for camera_id in self.camera_manager.cameras.keys():
            if camera_id not in self.detection_threads:
                self.start_detection(camera_id)
            elif not self.detection_threads[camera_id].is_alive():
                # Thread ölmüşse yeniden başlat
                self.start_detection(camera_id)
        
        # Header - Ana menü butonu (sol üst)
        header_frame = tk.Frame(self.main_container, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        home_btn = tk.Button(header_frame, text="🏠 Ana Menü", 
                            command=self.show_main_menu,
                            bg='#666666', fg='#ffffff',
                            font=("Arial", 12, "bold"),
                            relief=tk.FLAT, padx=20, pady=10,
                            cursor='hand2')
        home_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Ana container
        main_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Sol panel - Kamera listesi
        left_panel = tk.Frame(main_container, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel.config(width=250)
        
        # Başlık
        title_frame = tk.Frame(left_panel, bg=self.colors['secondary'])
        title_frame.pack(fill=tk.X, pady=10)
        title_label = tk.Label(title_frame, text="📹 Cameras", 
                              font=("Arial", 16, "bold"), 
                              bg=self.colors['secondary'], fg=self.colors['fg'])
        title_label.pack()
        
        # Kamera listbox (modern)
        list_container = tk.Frame(left_panel, bg=self.colors['secondary'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_container, bg=self.colors['secondary'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.camera_listbox = tk.Listbox(list_container, 
                                         yscrollcommand=scrollbar.set,
                                         bg='#3d3d3d', fg='#ffffff',
                                         selectbackground=self.colors['accent'],
                                         selectforeground='#ffffff',
                                         font=("Arial", 11),
                                         height=15,
                                         relief=tk.FLAT,
                                         bd=0)
        self.camera_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.camera_listbox.bind('<<ListboxSelect>>', self.on_camera_select)
        scrollbar.config(command=self.camera_listbox.yview)
        
        # Butonlar (modern)
        button_frame = tk.Frame(left_panel, bg=self.colors['secondary'])
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        add_btn = tk.Button(button_frame, text="➕ Add Camera", 
                           command=self.add_camera_dialog,
                           bg=self.colors['accent'], fg='#ffffff',
                           font=("Arial", 10, "bold"),
                           relief=tk.FLAT, padx=10, pady=8,
                           cursor='hand2')
        add_btn.pack(fill=tk.X, pady=5)
        
        remove_btn = tk.Button(button_frame, text="➖ Remove Camera", 
                              command=self.remove_camera,
                              bg='#666666', fg='#ffffff',
                              font=("Arial", 10),
                              relief=tk.FLAT, padx=10, pady=8,
                              cursor='hand2')
        remove_btn.pack(fill=tk.X, pady=5)
        
        # Kamera listesini güncelle
        self.update_camera_list()
        
        # Sağ panel - Görüntü ve kontroller
        right_panel = tk.Frame(main_container, bg=self.colors['bg'])
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Görüntü frame (modern border)
        video_container = tk.Frame(right_panel, bg=self.colors['accent'], relief=tk.RAISED, bd=3)
        video_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.video_frame = tk.Label(video_container, text="📹 No camera selected\n\nSelect a camera from the list", 
                                    bg='#000000', fg='#888888',
                                    font=("Arial", 14),
                                    justify=tk.CENTER)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Kontrol butonları (modern)
        control_frame = tk.Frame(right_panel, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=5)
        
        gallery_btn = tk.Button(control_frame, text="🖼️ Gallery", 
                               command=self.show_gallery_view,
                               bg=self.colors['success'], fg='#ffffff',
                               font=("Arial", 12, "bold"),
                               relief=tk.FLAT, padx=20, pady=12,
                               cursor='hand2')
        gallery_btn.pack(side=tk.LEFT, padx=5)
        
        # Durum bilgisi (modern)
        status_frame = tk.Frame(right_panel, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(status_frame, text="✅ System Ready", 
                                     font=("Arial", 11),
                                     bg=self.colors['secondary'], fg=self.colors['success'],
                                     padx=10, pady=8)
        self.status_label.pack()
        
    def add_default_cameras(self):
        """Varsayılan kameraları ekle"""
        self.camera_manager.add_camera("camera1", "rtsp://192.168.1.193:8554/stream")
        # Liste henüz oluşturulmadıysa güncelleme yapma
        if hasattr(self, 'camera_listbox') and self.camera_listbox:
            self.update_camera_list()
    
    def update_camera_list(self):
        """Kamera listesini güncelle"""
        if hasattr(self, 'camera_listbox') and self.camera_listbox:
            self.camera_listbox.delete(0, tk.END)
            for camera_id in self.camera_manager.cameras.keys():
                self.camera_listbox.insert(tk.END, f"📹 {camera_id}")
    
    def add_camera_dialog(self):
        """Kamera ekleme dialogu (modern)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Camera")
        dialog.geometry("450x200")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"450x200+{x}+{y}")
        
        title = tk.Label(dialog, text="➕ Add New Camera", 
                        font=("Arial", 14, "bold"),
                        bg=self.colors['bg'], fg=self.colors['fg'])
        title.pack(pady=15)
        
        form_frame = tk.Frame(dialog, bg=self.colors['bg'])
        form_frame.pack(padx=20, pady=10)
        
        tk.Label(form_frame, text="Camera ID:", 
                bg=self.colors['bg'], fg=self.colors['fg'],
                font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        camera_id_entry = tk.Entry(form_frame, width=30, font=("Arial", 10))
        camera_id_entry.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="RTSP URL:", 
                bg=self.colors['bg'], fg=self.colors['fg'],
                font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        rtsp_url_entry = tk.Entry(form_frame, width=30, font=("Arial", 10))
        rtsp_url_entry.grid(row=1, column=1, padx=10, pady=8)
        rtsp_url_entry.insert(0, "rtsp://")
        
        def add_camera():
            camera_id = camera_id_entry.get().strip()
            rtsp_url = rtsp_url_entry.get().strip()
            
            if not camera_id or not rtsp_url:
                messagebox.showerror("Error", "Please fill all fields", parent=dialog)
                return
            
            if camera_id in self.camera_manager.cameras:
                messagebox.showerror("Error", "Camera ID already exists", parent=dialog)
                return
            
            self.camera_manager.add_camera(camera_id, rtsp_url)
            self.update_camera_list()
            self.start_detection(camera_id)
            self.status_label.config(text=f"✅ Camera '{camera_id}' added", fg=self.colors['success'])
            dialog.destroy()
        
        button_frame = tk.Frame(dialog, bg=self.colors['bg'])
        button_frame.pack(pady=15)
        
        add_btn = tk.Button(button_frame, text="Add", command=add_camera,
                           bg=self.colors['accent'], fg='#ffffff',
                           font=("Arial", 10, "bold"),
                           relief=tk.FLAT, padx=20, pady=8,
                           cursor='hand2')
        add_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                              bg='#666666', fg='#ffffff',
                              font=("Arial", 10),
                              relief=tk.FLAT, padx=20, pady=8,
                              cursor='hand2')
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        camera_id_entry.focus()
        dialog.bind('<Return>', lambda e: add_camera())
    
    def remove_camera(self):
        """Seçili kamerayı kaldır"""
        selection = self.camera_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a camera")
            return
        
        camera_id = self.camera_listbox.get(selection[0]).replace("📹 ", "")
        
        if messagebox.askyesno("Confirm", f"Remove camera '{camera_id}'?"):
            # Önce thread'leri durdur
            if camera_id in self.camera_manager.cameras:
                self.camera_manager.cameras[camera_id]['viewing'] = False
            
            # Yangın kaydını durdur
            if camera_id in self.camera_manager.fire_events:
                self.stop_fire_recording(camera_id)
            
            # Kamerayı kaldır
            self.camera_manager.remove_camera(camera_id)
            
            # Thread referanslarını temizle
            if camera_id in self.detection_threads:
                del self.detection_threads[camera_id]
            
            # Seçili kamerayı temizle
            if self.selected_camera == camera_id:
                self.selected_camera = None
                self.video_frame.config(image='', text="📹 No camera selected\n\nSelect a camera from the list")
            
            # Listeyi güncelle
            self.update_camera_list()
            self.status_label.config(text=f"✅ Camera '{camera_id}' removed", fg=self.colors['success'])
    
    def on_camera_select(self, event):
        """Kamera seçildiğinde"""
        selection = self.camera_listbox.curselection()
        if selection:
            camera_id = self.camera_listbox.get(selection[0]).replace("📹 ", "")
            self.selected_camera = camera_id
            self.start_viewing(camera_id)
    
    def start_viewing(self, camera_id):
        """Kamerayı izlemeye başla (delay'siz)"""
        # Önceki viewing thread'leri durdur
        if self.viewing_thread and self.viewing_thread.is_alive():
            # Önceki kamerayı durdur
            if self.selected_camera and self.selected_camera in self.camera_manager.cameras:
                self.camera_manager.cameras[self.selected_camera]['viewing'] = False
            time.sleep(0.1)  # Thread'in durması için bekle
        
        # Display thread'i durdur (selected_camera None yaparak)
        if self.display_thread and self.display_thread.is_alive():
            old_selected = self.selected_camera
            self.selected_camera = None
            time.sleep(0.2)  # Thread'in durması için bekle
            self.selected_camera = camera_id  # Yeni kamerayı set et
        
        # Queue'yu temizle
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        def view_camera():
            if camera_id not in self.camera_manager.cameras:
                print(f"❌ [{camera_id}] Camera not found in cameras list")
                return
            
            cam_info = self.camera_manager.cameras[camera_id]
            rtsp_url = cam_info['rtsp_url']
            
            print(f"📹 [{camera_id}] Starting camera view: {rtsp_url}")
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimum buffer
            
            if not cap.isOpened():
                print(f"❌ [{camera_id}] Failed to open stream for viewing")
                try:
                    if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                        self.root.after(0, lambda: self.status_label.config(
                            text=f"❌ Failed to connect to {camera_id}", 
                            fg=self.colors['accent']
                        ))
                except:
                    pass
                return
            
            print(f"✅ [{camera_id}] Camera view connected")
            cam_info['cap'] = cap
            cam_info['viewing'] = True
            
            while cam_info['viewing'] and camera_id == self.selected_camera:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                
                # Frame'i queue'ya ekle (delay'siz)
                try:
                    if not self.frame_queue.full():
                        self.frame_queue.put((camera_id, frame), block=False)
                except:
                    pass
                
                time.sleep(0.01)  # Minimum delay
            
            cap.release()
            cam_info['viewing'] = False
            print(f"🛑 [{camera_id}] Camera view stopped")
        
        # Frame gösterici thread (ayrı)
        def display_frames():
            while self.selected_camera:
                try:
                    cam_id, frame = self.frame_queue.get(timeout=0.1)
                    if cam_id == self.selected_camera:
                        # Widget'ın hala var olup olmadığını kontrol et
                        try:
                            # Yangın tespiti (hızlı preview için)
                            detection = self.camera_manager.detectors[cam_id].detect(frame)
                            if detection['fire_detected']:
                                frame = self.camera_manager.detectors[cam_id].draw_detections(frame, detection)
                            
                            # Frame'i GUI'ye göster (preview için resize, kayıt için orijinal)
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            # Preview için resize (görüntü kalitesi için INTER_LINEAR kullan)
                            frame_resized = cv2.resize(frame_rgb, (1000, 700), interpolation=cv2.INTER_LINEAR)
                            img = Image.fromarray(frame_resized)
                            img_tk = ImageTk.PhotoImage(image=img)
                            
                            # Thread-safe widget update
                            self.root.after(0, lambda img=img_tk: self._update_video_frame_safe(img))
                        except (tk.TclError, AttributeError) as e:
                            # Widget destroy edilmiş, thread'i durdur
                            print(f"⚠️ Display thread error: {e}")
                            break
                except queue.Empty:
                    continue
        
        self.viewing_thread = threading.Thread(target=view_camera, daemon=True, name=f"Viewing-{camera_id}")
        self.viewing_thread.start()
        
        self.display_thread = threading.Thread(target=display_frames, daemon=True, name=f"Display-{camera_id}")
        self.display_thread.start()
        print(f"✅ [{camera_id}] Viewing and display threads started")
    
    def _update_video_frame_safe(self, img_tk):
        """Thread-safe video frame update"""
        try:
            if hasattr(self, 'video_frame') and self.video_frame.winfo_exists():
                self.video_frame.config(image=img_tk, text='')
                self.video_frame.image = img_tk
        except (tk.TclError, AttributeError):
            pass
    
    def start_all_detections(self):
        """Tüm kameralar için tespit başlat (arka planda her zaman çalışır)"""
        print(f"🚀 Starting detection for {len(self.camera_manager.cameras)} camera(s)...")
        for camera_id in self.camera_manager.cameras.keys():
            print(f"   → Starting detection thread for {camera_id}")
            self.start_detection(camera_id)
        print(f"✅ All detection threads started")
    
    def start_detection(self, camera_id):
        """Yangın tespiti thread'ini başlat"""
        # Eğer thread zaten çalışıyorsa, yeniden başlatma
        if camera_id in self.detection_threads:
            if self.detection_threads[camera_id].is_alive():
                return
            else:
                # Thread ölmüş, temizle
                del self.detection_threads[camera_id]
        
        def detect_fire():
            try:
                cam_info = self.camera_manager.cameras[camera_id]
                rtsp_url = cam_info['rtsp_url']
                
                print(f"🔌 [{camera_id}] Connecting to stream: {rtsp_url}")
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Stream açılana kadar bekle (max 10 saniye)
                max_retries = 50
                retry_count = 0
                while not cap.isOpened() and retry_count < max_retries:
                    time.sleep(0.2)
                    retry_count += 1
                    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if not cap.isOpened():
                    print(f"❌ [{camera_id}] Failed to open stream after {max_retries} retries")
                    print(f"   URL: {rtsp_url}")
                    return
                
                print(f"✅ [{camera_id}] Detection thread started and stream connected")
                
                detector = self.camera_manager.detectors[camera_id]
                fire_event = self.camera_manager.fire_events[camera_id]
                
                last_detection_time = 0
                detection_interval = 0.3  # Her 0.3 saniyede bir tespit
                fire_duration = 0
                max_fire_duration = 40  # Maksimum 40 saniye kayıt
                frame_count = 0
                
                while camera_id in self.camera_manager.cameras:
                    ret, frame = cap.read()
                    if not ret:
                        time.sleep(0.1)
                        continue
                    
                    frame_count += 1
                    
                    # Buffer'a ekle (yangın başladığında geriye dönük kayıt için)
                    if len(fire_event['frames_buffer']) >= fire_event['buffer_size']:
                        fire_event['frames_buffer'].pop(0)
                    fire_event['frames_buffer'].append((frame.copy(), time.time()))
                    
                    current_time = time.time()
                    if current_time - last_detection_time >= detection_interval:
                        detection = detector.detect(frame)
                        last_detection_time = current_time
                        
                        # Debug: Her 50 frame'de bir durum yazdır (daha sık)
                        if frame_count % 50 == 0:
                            bbox_count = len(detection.get('bboxes', []))
                            print(f"🔍 [{camera_id}] Frame {frame_count} - Fire: {detection['fire_detected']}, Confidence: {detection['confidence']:.2f}, BBoxes: {bbox_count}")
                            
                            # Eğer yangın tespit edilmediyse ama confidence > 0 ise, debug bilgisi
                            if not detection['fire_detected'] and detection['confidence'] > 0:
                                print(f"   ⚠️ Fire-like pixels detected but below threshold (confidence: {detection['confidence']:.2f})")
                        
                        if detection['fire_detected']:
                            if not fire_event['active']:
                                # Yangın başladı
                                fire_event['active'] = True
                                fire_event['start_time'] = datetime.now()
                                fire_duration = 0
                                self.start_fire_recording(camera_id, fire_event['frames_buffer'])
                                print(f"🔥 FIRE DETECTED in {camera_id}! Confidence: {detection['confidence']:.2f}")
                                # GUI thread-safe update
                                try:
                                    if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                                        self.root.after(0, lambda cid=camera_id: self.status_label.config(
                                            text=f"🔥 FIRE DETECTED in {cid}!", 
                                            fg=self.colors['accent']
                                        ))
                                except (tk.TclError, AttributeError):
                                    pass
                            
                            # Fotoğraf kaydet (arka planda her zaman çalışır)
                            photo_path = self.save_fire_photo(camera_id, frame, detection)
                            print(f"📸 [{camera_id}] Fire photo saved: {photo_path}")
                            
                            # Video kaydına devam et
                            if fire_event['video_writer']:
                                fire_event['video_writer'].write(frame)
                                fire_duration += detection_interval
                                
                                # Maksimum süre kontrolü
                                if fire_duration >= max_fire_duration:
                                    self.stop_fire_recording(camera_id)
                        else:
                            # Yangın tespit edilmedi
                            if fire_event['active']:
                                # Yangın bitti (birkaç frame daha kaydet)
                                fire_duration += detection_interval
                                if fire_duration >= 2.0:  # 2 saniye yangın yoksa durdur
                                    self.stop_fire_recording(camera_id)
                                    print(f"✅ Fire event ended for {camera_id}")
                            elif fire_event['video_writer']:
                                # Hala kayıt devam ediyorsa birkaç frame daha ekle
                                fire_event['video_writer'].write(frame)
                                fire_duration += detection_interval
                                if fire_duration >= max_fire_duration:
                                    self.stop_fire_recording(camera_id)
                    
                    time.sleep(0.03)
                
                cap.release()
                print(f"🛑 [{camera_id}] Detection thread stopped")
            except Exception as e:
                print(f"❌ [{camera_id}] Error in detection thread: {e}")
                import traceback
                traceback.print_exc()
                # Hata olsa bile thread'i yeniden başlatmayı dene (5 saniye sonra)
                time.sleep(5)
                if camera_id in self.camera_manager.cameras:
                    print(f"🔄 [{camera_id}] Attempting to restart detection thread...")
                    self.start_detection(camera_id)
        
        thread = threading.Thread(target=detect_fire, daemon=True, name=f"Detection-{camera_id}")
        thread.start()
        self.detection_threads[camera_id] = thread
        print(f"✅ [{camera_id}] Detection thread created and started")
    
    def start_fire_recording(self, camera_id, frames_buffer):
        """Yangın başladığında video kaydını başlat (buffer'dan başla) - ARKA PLANDA HER ZAMAN ÇALIŞIR"""
        fire_event = self.camera_manager.fire_events[camera_id]
        
        timestamp = fire_event['start_time'].strftime("%Y%m%d_%H%M%S")
        video_file = self.fire_videos_dir / f"{camera_id}_fire_{timestamp}.mp4"
        
        if frames_buffer:
            height, width = frames_buffer[0][0].shape[:2]
        else:
            print(f"⚠️ [{camera_id}] No frames in buffer, cannot start recording")
            return
        
        print(f"🎥 [{camera_id}] Starting fire video recording: {video_file.name}")
        
        # Yüksek kalite codec (H.264)
        # Windows için 'H264' veya 'XVID' kullanılabilir
        # 'mp4v' yerine daha iyi codec'ler
        fourcc = cv2.VideoWriter_fourcc(*'H264')  # H.264 codec (daha iyi kalite)
        # Eğer H264 çalışmazsa XVID veya MJPG deneyin
        # fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        
        fps = 30
        
        # VideoWriter oluştur
        writer = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))
        
        # Codec kontrolü
        if not writer.isOpened():
            # H264 çalışmazsa XVID dene
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            video_file = self.fire_videos_dir / f"{camera_id}_fire_{timestamp}.avi"
            writer = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))
            
            if not writer.isOpened():
                # Son çare olarak MJPG
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                video_file = self.fire_videos_dir / f"{camera_id}_fire_{timestamp}.avi"
                writer = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))
        
        fire_event['video_writer'] = writer
        fire_event['video_file'] = str(video_file)
        
        # Buffer'daki frame'leri yaz (geriye dönük kayıt) - yüksek kalite
        buffer_frames_written = 0
        for frame, _ in frames_buffer:
            # Frame'i sıkıştırmadan yaz
            writer.write(frame)
            buffer_frames_written += 1
        
        print(f"📹 [{camera_id}] Wrote {buffer_frames_written} pre-fire frames to video")
    
    def stop_fire_recording(self, camera_id):
        """Yangın bittiğinde video kaydını durdur"""
        fire_event = self.camera_manager.fire_events[camera_id]
        
        if fire_event['video_writer']:
            video_file = fire_event.get('video_file', 'unknown')
            fire_event['video_writer'].release()
            fire_event['video_writer'] = None
            print(f"💾 [{camera_id}] Fire video saved: {video_file}")
        
        fire_event['active'] = False
        fire_event['start_time'] = None
        fire_event['frames_buffer'] = []
        
        # Thread-safe status update
        if self.selected_camera == camera_id:
            try:
                if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"✅ Recording saved for {camera_id}", 
                        fg=self.colors['success']
                    ))
            except (tk.TclError, AttributeError):
                pass
    
    def check_detection_threads(self):
        """Detection thread'lerinin çalışıp çalışmadığını kontrol et ve gerekirse yeniden başlat"""
        for camera_id in list(self.camera_manager.cameras.keys()):
            if camera_id not in self.detection_threads:
                # Thread yok, başlat
                print(f"⚠️ [{camera_id}] Detection thread missing, starting...")
                self.start_detection(camera_id)
            elif not self.detection_threads[camera_id].is_alive():
                # Thread ölmüş, yeniden başlat
                print(f"⚠️ [{camera_id}] Detection thread died, restarting...")
                if camera_id in self.detection_threads:
                    del self.detection_threads[camera_id]
                self.start_detection(camera_id)
        
        # Status label'ı güncelle (eğer varsa)
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                active_detections = sum(1 for t in self.detection_threads.values() if t.is_alive())
                total_cameras = len(self.camera_manager.cameras)
                status_text = f"✅ System Ready - {active_detections}/{total_cameras} cameras monitoring"
                self.status_label.config(text=status_text)
        except (tk.TclError, AttributeError):
            pass
        
        # 10 saniye sonra tekrar kontrol et
        self.root.after(10000, self.check_detection_threads)
    
    def save_fire_photo(self, camera_id, frame, detection):
        """Yangın fotoğrafını kaydet (yüksek kalite) - ARKA PLANDA HER ZAMAN ÇALIŞIR"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        photo_file = self.photos_dir / f"{camera_id}_fire_{timestamp}.jpg"
        
        # Tespit bilgilerini frame'e çiz
        frame_with_detection = self.camera_manager.detectors[camera_id].draw_detections(frame, detection)
        
        # Yüksek kalite JPEG kaydet (quality: 0-100, 95 = çok yüksek kalite)
        success = cv2.imwrite(str(photo_file), frame_with_detection, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if success:
            return str(photo_file)
        else:
            print(f"❌ [{camera_id}] Failed to save fire photo: {photo_file}")
            return None
    
    def stop_camera_threads(self, camera_id):
        """Kamera thread'lerini durdur"""
        if camera_id in self.camera_manager.cameras:
            self.camera_manager.cameras[camera_id]['viewing'] = False
        
        if camera_id in self.camera_manager.fire_events:
            self.stop_fire_recording(camera_id)
        
        # Thread'leri durdur
        if camera_id in self.detection_threads:
            # Thread'i durdurmak için kamera'yı listeden çıkar
            # (thread kendi kendine duracak)
            pass
    
    def show_gallery_view(self):
        """Gallery ekranını göster"""
        # Önceki ekranı temizle
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Gallery container
        gallery_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        gallery_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Başlık ve ana menü butonu (sol üst)
        header_frame = tk.Frame(gallery_container, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        home_btn = tk.Button(header_frame, text="🏠 Ana Menü", 
                            command=self.show_main_menu,
                            bg='#666666', fg='#ffffff',
                            font=("Arial", 12, "bold"),
                            relief=tk.FLAT, padx=20, pady=10,
                            cursor='hand2')
        home_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        title_label = tk.Label(header_frame, text="🖼️ Gallery - Fire Detection Records",
                               font=("Arial", 20, "bold"),
                               bg=self.colors['bg'], fg=self.colors['fg'])
        title_label.pack(side=tk.LEFT, padx=20)
        
        # Gallery içeriği
        gallery = GalleryFrame(gallery_container, self.photos_dir, self.fire_videos_dir, self.colors)
    
    def open_gallery(self):
        """Gallery penceresini aç (eski method - geriye uyumluluk)"""
        self.show_gallery_view()
    
    def on_closing(self):
        """Uygulama kapanırken"""
        # Tüm kameraları durdur
        for camera_id in list(self.camera_manager.cameras.keys()):
            if camera_id in self.camera_manager.cameras:
                self.camera_manager.cameras[camera_id]['viewing'] = False
            if camera_id in self.camera_manager.fire_events:
                self.stop_fire_recording(camera_id)
        
        # Biraz bekle (thread'lerin durması için)
        time.sleep(0.5)
        self.root.destroy()


class GalleryFrame:
    """Modern Gallery/Guid frame (ana pencerede)"""
    
    def __init__(self, parent, photos_dir, videos_dir, colors):
        self.parent = parent
        self.photos_dir = photos_dir
        self.videos_dir = videos_dir
        self.colors = colors
        self.selected_video = None
        self.video_cap = None
        self.playing = False
        
        # Notebook (tabs) - modern
        style = ttk.Style()
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['secondary'], foreground=self.colors['fg'], padding=15)
        style.map('TNotebook.Tab', background=[('selected', self.colors['accent'])])
        
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Photos tab
        photos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(photos_frame, text="📷 Photos")
        self.setup_photos_tab(photos_frame)
        
        # Videos tab
        videos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(videos_frame, text="🎥 Fire Event Videos")
        self.setup_videos_tab(videos_frame)
        
        # Başlangıçta dosyaları yükle
        self.load_photos()
        self.load_videos()
    
    def setup_photos_tab(self, parent):
        """Fotoğraflar sekmesi"""
        # Sol - Liste
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="📷 Fire Detection Photos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        # Refresh butonu (büyük ve belirgin)
        refresh_btn = tk.Button(left_frame, text="🔄 Güncelle", 
                               command=self.load_photos,
                               bg=self.colors['accent'], fg='#ffffff',
                               font=("Arial", 12, "bold"),
                               relief=tk.FLAT, padx=15, pady=10,
                               cursor='hand2')
        refresh_btn.pack(pady=10)
        
        list_container = tk.Frame(left_frame, bg=self.colors['secondary'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_container, bg=self.colors['secondary'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.photos_listbox = tk.Listbox(list_container, 
                                        yscrollcommand=scrollbar.set,
                                        bg='#3d3d3d', fg='#ffffff',
                                        selectbackground=self.colors['accent'],
                                        font=("Arial", 10),
                                        relief=tk.FLAT)
        self.photos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.photos_listbox.bind('<<ListboxSelect>>', self.on_photo_select)
        scrollbar.config(command=self.photos_listbox.yview)
        
        # Sağ - Preview
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
        self.photo_preview = tk.Label(right_frame, text="Select a photo", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.photo_preview.pack(fill=tk.BOTH, expand=True)
    
    def setup_videos_tab(self, parent):
        """Videolar sekmesi"""
        # Sol - Liste
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="🎥 Fire Event Videos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        # Refresh butonu (büyük ve belirgin)
        refresh_btn = tk.Button(left_frame, text="🔄 Güncelle", 
                               command=self.load_videos,
                               bg=self.colors['accent'], fg='#ffffff',
                               font=("Arial", 12, "bold"),
                               relief=tk.FLAT, padx=15, pady=10,
                               cursor='hand2')
        refresh_btn.pack(pady=10)
        
        list_container = tk.Frame(left_frame, bg=self.colors['secondary'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_container, bg=self.colors['secondary'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.videos_listbox = tk.Listbox(list_container, 
                                         yscrollcommand=scrollbar.set,
                                         bg='#3d3d3d', fg='#ffffff',
                                         selectbackground=self.colors['accent'],
                                         font=("Arial", 10),
                                         relief=tk.FLAT)
        self.videos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.videos_listbox.bind('<<ListboxSelect>>', self.on_video_select)
        scrollbar.config(command=self.videos_listbox.yview)
        
        # Sağ - Video player
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
        # Kontrol butonları
        control_frame = tk.Frame(right_frame, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=10)
        
        play_btn = tk.Button(control_frame, text="▶️ Play", 
                            command=self.play_video,
                            bg=self.colors['success'], fg='#ffffff',
                            font=("Arial", 11, "bold"),
                            relief=tk.FLAT, padx=15, pady=8,
                            cursor='hand2')
        play_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(control_frame, text="⏹️ Stop", 
                            command=self.stop_video,
                            bg=self.colors['accent'], fg='#ffffff',
                            font=("Arial", 11, "bold"),
                            relief=tk.FLAT, padx=15, pady=8,
                            cursor='hand2')
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Video preview
        self.video_preview = tk.Label(right_frame, text="Select a video", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.video_preview.pack(fill=tk.BOTH, expand=True)
    
    def load_photos(self):
        """Fotoğrafları yükle"""
        if not hasattr(self, 'photos_listbox') or not self.photos_listbox:
            return
        
        self.photos_listbox.delete(0, tk.END)
        if self.photos_dir.exists():
            # Tüm görüntü formatlarını kontrol et
            photo_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
            photos = []
            for ext in photo_extensions:
                photos.extend(self.photos_dir.glob(ext))
            
            if photos:
                photos = sorted(photos, key=os.path.getmtime, reverse=True)
                for photo_file in photos:
                    # Tarih bilgisi ile göster
                    try:
                        mtime = os.path.getmtime(photo_file)
                        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        self.photos_listbox.insert(tk.END, f"{photo_file.name} ({date_str})")
                    except:
                        self.photos_listbox.insert(tk.END, photo_file.name)
            else:
                self.photos_listbox.insert(tk.END, "No photos found")
        else:
            self.photos_listbox.insert(tk.END, "No photos found")
    
    def load_videos(self):
        """Videoları yükle"""
        if not hasattr(self, 'videos_listbox') or not self.videos_listbox:
            return
        
        self.videos_listbox.delete(0, tk.END)
        if self.videos_dir.exists():
            # Tüm video formatlarını kontrol et
            video_extensions = ['*.mp4', '*.avi', '*.mov', '*.MP4', '*.AVI', '*.MOV']
            videos = []
            for ext in video_extensions:
                videos.extend(self.videos_dir.glob(ext))
            
            if videos:
                videos = sorted(videos, key=os.path.getmtime, reverse=True)
                for video_file in videos:
                    # Tarih ve boyut bilgisi ile göster
                    try:
                        mtime = os.path.getmtime(video_file)
                        size = os.path.getsize(video_file) / (1024 * 1024)  # MB
                        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        self.videos_listbox.insert(tk.END, f"{video_file.name} ({date_str}, {size:.1f}MB)")
                    except:
                        self.videos_listbox.insert(tk.END, video_file.name)
            else:
                self.videos_listbox.insert(tk.END, "No videos found")
        else:
            self.videos_listbox.insert(tk.END, "No videos found")
    
    def on_photo_select(self, event):
        """Fotoğraf seçildiğinde"""
        selection = self.photos_listbox.curselection()
        if selection:
            photo_entry = self.photos_listbox.get(selection[0])
            if photo_entry == "No photos found":
                return
            
            # Dosya adını çıkar (tarih bilgisini kaldır)
            photo_name = photo_entry.split(" (")[0]
            photo_path = self.photos_dir / photo_name
            
            if photo_path.exists():
                try:
                    img = Image.open(photo_path)
                    # Resize to fit
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(image=img)
                    self.photo_preview.config(image=img_tk, text='')
                    self.photo_preview.image = img_tk
                except Exception as e:
                    self.photo_preview.config(text=f"Error loading image: {e}")
            else:
                self.photo_preview.config(text="File not found")
    
    def on_video_select(self, event):
        """Video seçildiğinde"""
        selection = self.videos_listbox.curselection()
        if selection:
            video_entry = self.videos_listbox.get(selection[0])
            if video_entry == "No videos found":
                return
            
            # Dosya adını çıkar (tarih bilgisini kaldır)
            video_name = video_entry.split(" (")[0]
            self.selected_video = self.videos_dir / video_name
    
    def play_video(self):
        """Video oynat"""
        if not hasattr(self, 'selected_video') or not self.selected_video or not self.selected_video.exists():
            messagebox.showwarning("Warning", "Please select a video", parent=self.parent)
            return
        
        if self.video_cap:
            self.video_cap.release()
        
        self.video_cap = cv2.VideoCapture(str(self.selected_video))
        if not self.video_cap.isOpened():
            messagebox.showerror("Error", "Failed to open video", parent=self.parent)
            return
        
        self.playing = True
        
        def play():
            while self.playing and self.video_cap:
                ret, frame = self.video_cap.read()
                if not ret:
                    self.playing = False
                    break
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (900, 600))
                img = Image.fromarray(frame_resized)
                img_tk = ImageTk.PhotoImage(image=img)
                
                self.video_preview.config(image=img_tk, text='')
                self.video_preview.image = img_tk
                
                time.sleep(0.033)  # ~30 FPS
            
            if self.video_cap:
                self.video_cap.release()
                self.video_cap = None
        
        threading.Thread(target=play, daemon=True).start()
    
    def stop_video(self):
        """Video durdur"""
        self.playing = False
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self.video_preview.config(image='', text="Select a video")


class GalleryWindow:
    """Modern Gallery/Guid penceresi"""
    
    def __init__(self, parent, photos_dir, videos_dir, colors):
        self.window = tk.Toplevel(parent)
        self.window.title("🖼️ Gallery - Fire Detection Records")
        self.window.geometry("1200x800")
        self.window.configure(bg=colors['bg'])
        
        self.photos_dir = photos_dir
        self.videos_dir = videos_dir
        self.colors = colors
        self.selected_video = None
        self.video_cap = None
        self.playing = False
        
        # Notebook (tabs) - modern
        style = ttk.Style()
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['secondary'], foreground=self.colors['fg'], padding=15)
        style.map('TNotebook.Tab', background=[('selected', self.colors['accent'])])
        
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Photos tab
        photos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(photos_frame, text="📷 Photos")
        self.setup_photos_tab(photos_frame)
        
        # Videos tab
        videos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(videos_frame, text="🎥 Fire Event Videos")
        self.setup_videos_tab(videos_frame)
        
        # Başlangıçta dosyaları yükle
        self.load_photos()
        self.load_videos()
    
    def setup_photos_tab(self, parent):
        """Fotoğraflar sekmesi"""
        # Sol - Liste
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="📷 Fire Detection Photos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        # Refresh butonu (büyük ve belirgin)
        refresh_btn = tk.Button(left_frame, text="🔄 Güncelle", 
                               command=self.load_photos,
                               bg=self.colors['accent'], fg='#ffffff',
                               font=("Arial", 12, "bold"),
                               relief=tk.FLAT, padx=15, pady=10,
                               cursor='hand2')
        refresh_btn.pack(pady=10)
        
        list_container = tk.Frame(left_frame, bg=self.colors['secondary'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_container, bg=self.colors['secondary'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.photos_listbox = tk.Listbox(list_container, 
                                        yscrollcommand=scrollbar.set,
                                        bg='#3d3d3d', fg='#ffffff',
                                        selectbackground=self.colors['accent'],
                                        font=("Arial", 10),
                                        relief=tk.FLAT)
        self.photos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.photos_listbox.bind('<<ListboxSelect>>', self.on_photo_select)
        scrollbar.config(command=self.photos_listbox.yview)
        
        # Sağ - Preview
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
        self.photo_preview = tk.Label(right_frame, text="Select a photo", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.photo_preview.pack(fill=tk.BOTH, expand=True)
    
    def setup_videos_tab(self, parent):
        """Videolar sekmesi"""
        # Sol - Liste
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="🎥 Fire Event Videos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        # Refresh butonu (büyük ve belirgin)
        refresh_btn = tk.Button(left_frame, text="🔄 Güncelle", 
                               command=self.load_videos,
                               bg=self.colors['accent'], fg='#ffffff',
                               font=("Arial", 12, "bold"),
                               relief=tk.FLAT, padx=15, pady=10,
                               cursor='hand2')
        refresh_btn.pack(pady=10)
        
        list_container = tk.Frame(left_frame, bg=self.colors['secondary'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_container, bg=self.colors['secondary'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.videos_listbox = tk.Listbox(list_container, 
                                         yscrollcommand=scrollbar.set,
                                         bg='#3d3d3d', fg='#ffffff',
                                         selectbackground=self.colors['accent'],
                                         font=("Arial", 10),
                                         relief=tk.FLAT)
        self.videos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.videos_listbox.bind('<<ListboxSelect>>', self.on_video_select)
        scrollbar.config(command=self.videos_listbox.yview)
        
        # Sağ - Video player
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
        # Kontrol butonları
        control_frame = tk.Frame(right_frame, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=10)
        
        play_btn = tk.Button(control_frame, text="▶️ Play", 
                            command=self.play_video,
                            bg=self.colors['success'], fg='#ffffff',
                            font=("Arial", 11, "bold"),
                            relief=tk.FLAT, padx=15, pady=8,
                            cursor='hand2')
        play_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(control_frame, text="⏹️ Stop", 
                            command=self.stop_video,
                            bg=self.colors['accent'], fg='#ffffff',
                            font=("Arial", 11, "bold"),
                            relief=tk.FLAT, padx=15, pady=8,
                            cursor='hand2')
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Video preview
        self.video_preview = tk.Label(right_frame, text="Select a video", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.video_preview.pack(fill=tk.BOTH, expand=True)
    
    def load_photos(self):
        """Fotoğrafları yükle"""
        if not hasattr(self, 'photos_listbox') or not self.photos_listbox:
            return
        
        self.photos_listbox.delete(0, tk.END)
        if self.photos_dir.exists():
            # Tüm görüntü formatlarını kontrol et
            photo_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
            photos = []
            for ext in photo_extensions:
                photos.extend(self.photos_dir.glob(ext))
            
            if photos:
                photos = sorted(photos, key=os.path.getmtime, reverse=True)
                for photo_file in photos:
                    # Tarih bilgisi ile göster
                    try:
                        mtime = os.path.getmtime(photo_file)
                        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        self.photos_listbox.insert(tk.END, f"{photo_file.name} ({date_str})")
                    except:
                        self.photos_listbox.insert(tk.END, photo_file.name)
            else:
                self.photos_listbox.insert(tk.END, "No photos found")
        else:
            self.photos_listbox.insert(tk.END, "No photos found")
    
    def load_videos(self):
        """Videoları yükle"""
        if not hasattr(self, 'videos_listbox') or not self.videos_listbox:
            return
        
        self.videos_listbox.delete(0, tk.END)
        if self.videos_dir.exists():
            # Tüm video formatlarını kontrol et
            video_extensions = ['*.mp4', '*.avi', '*.mov', '*.MP4', '*.AVI', '*.MOV']
            videos = []
            for ext in video_extensions:
                videos.extend(self.videos_dir.glob(ext))
            
            if videos:
                videos = sorted(videos, key=os.path.getmtime, reverse=True)
                for video_file in videos:
                    # Tarih ve boyut bilgisi ile göster
                    try:
                        mtime = os.path.getmtime(video_file)
                        size = os.path.getsize(video_file) / (1024 * 1024)  # MB
                        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                        self.videos_listbox.insert(tk.END, f"{video_file.name} ({date_str}, {size:.1f}MB)")
                    except:
                        self.videos_listbox.insert(tk.END, video_file.name)
            else:
                self.videos_listbox.insert(tk.END, "No videos found")
        else:
            self.videos_listbox.insert(tk.END, "No videos found")
    
    def on_photo_select(self, event):
        """Fotoğraf seçildiğinde"""
        selection = self.photos_listbox.curselection()
        if selection:
            photo_entry = self.photos_listbox.get(selection[0])
            if photo_entry == "No photos found":
                return
            
            # Dosya adını çıkar (tarih bilgisini kaldır)
            photo_name = photo_entry.split(" (")[0]
            photo_path = self.photos_dir / photo_name
            
            if photo_path.exists():
                try:
                    img = Image.open(photo_path)
                    # Resize to fit
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(image=img)
                    self.photo_preview.config(image=img_tk, text='')
                    self.photo_preview.image = img_tk
                except Exception as e:
                    self.photo_preview.config(text=f"Error loading image: {e}")
            else:
                self.photo_preview.config(text="File not found")
    
    def on_video_select(self, event):
        """Video seçildiğinde"""
        selection = self.videos_listbox.curselection()
        if selection:
            video_entry = self.videos_listbox.get(selection[0])
            if video_entry == "No videos found":
                return
            
            # Dosya adını çıkar (tarih bilgisini kaldır)
            video_name = video_entry.split(" (")[0]
            self.selected_video = self.videos_dir / video_name
    
    def play_video(self):
        """Video oynat"""
        if not hasattr(self, 'selected_video') or not self.selected_video or not self.selected_video.exists():
            messagebox.showwarning("Warning", "Please select a video", parent=self.window)
            return
        
        if self.video_cap:
            self.video_cap.release()
        
        self.video_cap = cv2.VideoCapture(str(self.selected_video))
        if not self.video_cap.isOpened():
            messagebox.showerror("Error", "Failed to open video", parent=self.window)
            return
        
        self.playing = True
        
        def play():
            while self.playing and self.video_cap:
                ret, frame = self.video_cap.read()
                if not ret:
                    self.playing = False
                    break
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (900, 600))
                img = Image.fromarray(frame_resized)
                img_tk = ImageTk.PhotoImage(image=img)
                
                self.video_preview.config(image=img_tk, text='')
                self.video_preview.image = img_tk
                
                time.sleep(0.033)  # ~30 FPS
            
            if self.video_cap:
                self.video_cap.release()
                self.video_cap = None
        
        threading.Thread(target=play, daemon=True).start()
    
    def stop_video(self):
        """Video durdur"""
        self.playing = False
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self.video_preview.config(image='', text="Select a video")


def main():
    """Ana fonksiyon"""
    root = tk.Tk()
    app = FireDetectionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
