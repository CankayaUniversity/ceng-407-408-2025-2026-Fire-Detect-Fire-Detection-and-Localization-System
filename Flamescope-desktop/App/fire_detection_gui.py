"""
Fire Detection System - Modern GUI Application
Camera selection, monitoring, fire detection and recording
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
    """Camera management"""
    
    def __init__(self):
        self.cameras = {}
        self.detectors = {}
        self.fire_events = {}  
        
    def add_camera(self, camera_id, rtsp_url):
        """Add camera"""
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
            'buffer_size': 150  
        }
        
    
    def remove_camera(self, camera_id):
        """Remove camera"""
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
        
        
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#ff4444',
            'secondary': '#2d2d2d',
            'success': '#44ff44',
            'warning': '#ffaa44'
        }
        
        
        self.base_dir = Path("recordings")
        self.base_dir.mkdir(exist_ok=True)
        self.photos_dir = self.base_dir / "photos"
        self.photos_dir.mkdir(exist_ok=True)
        self.fire_videos_dir = self.base_dir / "fire_events"
        self.fire_videos_dir.mkdir(exist_ok=True)
        
        
        self.settings_file = Path("camera_settings.json")
        
        
        self.camera_manager = CameraManager()
        
        
        self.selected_camera = None
        self.viewing_thread = None
        self.display_thread = None
        self.detection_threads = {}
        self.frame_queue = queue.Queue(maxsize=2)  
        
        
        self.setup_modern_gui()
        
        
        self.load_camera_settings()
        
        
        self.start_all_detections()
        
    def setup_modern_gui(self):
        """Modern GUI oluştur"""
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])
        style.configure('TButton', padding=10)
        style.map('TButton', background=[('active', self.colors['accent'])])
        
        
        self.main_container = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.show_main_menu()
    
    def show_main_menu(self):
        """Show main menu screen"""
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        menu_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        menu_container.pack(fill=tk.BOTH, expand=True)
        
        title_frame = tk.Frame(menu_container, bg=self.colors['bg'])
        title_frame.pack(pady=50)
        
        title_label = tk.Label(title_frame, text="🔥 Fire Detection System", 
                              font=("Arial", 32, "bold"),
                              bg=self.colors['bg'], fg=self.colors['accent'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Fire Detection and Monitoring System",
                                 font=("Arial", 16),
                                 bg=self.colors['bg'], fg=self.colors['fg'])
        subtitle_label.pack(pady=10)
        
        button_container = tk.Frame(menu_container, bg=self.colors['bg'])
        button_container.pack(pady=50)
        
        camera_btn = tk.Button(button_container, text="📹 Camera View",
                               command=self.show_camera_view,
                               bg=self.colors['accent'], fg='#ffffff',
                               font=("Arial", 18, "bold"),
                               relief=tk.FLAT, padx=40, pady=25,
                               cursor='hand2', width=25)
        camera_btn.pack(pady=20)
        
        gallery_btn = tk.Button(button_container, text="🖼️ Gallery",
                                command=self.show_gallery_view,
                                bg=self.colors['success'], fg='#ffffff',
                                font=("Arial", 18, "bold"),
                                relief=tk.FLAT, padx=40, pady=25,
                                cursor='hand2', width=25)
        gallery_btn.pack(pady=20)
        
        status_frame = tk.Frame(menu_container, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        status_frame.pack(pady=30)
        
        active_detections = sum(1 for t in self.detection_threads.values() if t.is_alive())
        total_cameras = len(self.camera_manager.cameras)
        status_text = f"✅ System Ready - {active_detections}/{total_cameras} cameras monitoring"
        
        self.status_label = tk.Label(status_frame, text=status_text, 
                                     font=("Arial", 12),
                                     bg=self.colors['secondary'], fg=self.colors['success'],
                                     padx=20, pady=15)
        self.status_label.pack()
        
        self.check_detection_threads()
    
    def show_camera_view(self):
        """Show camera view screen"""
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        for camera_id in self.camera_manager.cameras.keys():
            if camera_id not in self.detection_threads:
                self.start_detection(camera_id)
            elif not self.detection_threads[camera_id].is_alive():
                self.start_detection(camera_id)
        
        header_frame = tk.Frame(self.main_container, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        home_btn = tk.Button(header_frame, text="🏠 Main Menu", 
                            command=self.show_main_menu,
                            bg='#666666', fg='#ffffff',
                            font=("Arial", 12, "bold"),
                            relief=tk.FLAT, padx=20, pady=10,
                            cursor='hand2')
        home_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        main_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        left_panel = tk.Frame(main_container, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel.config(width=250)
        
        title_frame = tk.Frame(left_panel, bg=self.colors['secondary'])
        title_frame.pack(fill=tk.X, pady=10)
        title_label = tk.Label(title_frame, text="📹 Cameras", 
                              font=("Arial", 16, "bold"), 
                              bg=self.colors['secondary'], fg=self.colors['fg'])
        title_label.pack()
        
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
        
        self.update_camera_list()
        
        right_panel = tk.Frame(main_container, bg=self.colors['bg'])
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        video_container = tk.Frame(right_panel, bg=self.colors['accent'], relief=tk.RAISED, bd=3)
        video_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.video_frame = tk.Label(video_container, text="📹 No camera selected\n\nSelect a camera from the list", 
                                    bg='#000000', fg='#888888',
                                    font=("Arial", 14),
                                    justify=tk.CENTER)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        control_frame = tk.Frame(right_panel, bg=self.colors['bg'])
        control_frame.pack(fill=tk.X, pady=5)
        
        gallery_btn = tk.Button(control_frame, text="🖼️ Gallery", 
                               command=self.show_gallery_view,
                               bg=self.colors['success'], fg='#ffffff',
                               font=("Arial", 12, "bold"),
                               relief=tk.FLAT, padx=20, pady=12,
                               cursor='hand2')
        gallery_btn.pack(side=tk.LEFT, padx=5)
        
        status_frame = tk.Frame(right_panel, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(status_frame, text="✅ System Ready", 
                                     font=("Arial", 11),
                                     bg=self.colors['secondary'], fg=self.colors['success'],
                                     padx=10, pady=8)
        self.status_label.pack()
        
    def save_camera_settings(self):
        """Save camera settings to JSON file"""
        try:
            cameras_data = {}
            for camera_id, cam_info in self.camera_manager.cameras.items():
                cameras_data[camera_id] = {
                    'rtsp_url': cam_info['rtsp_url']
                }
            
            with open(self.settings_file, 'w') as f:
                json.dump(cameras_data, f, indent=2)
            print(f"✅ Camera settings saved to {self.settings_file}")
        except Exception as e:
            print(f"❌ Failed to save camera settings: {e}")
    
    def load_camera_settings(self):
        """Load camera settings from JSON file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    cameras_data = json.load(f)
                
                if cameras_data:
                    for camera_id, cam_data in cameras_data.items():
                        self.camera_manager.add_camera(camera_id, cam_data['rtsp_url'])
                    print(f"✅ Loaded {len(cameras_data)} camera(s) from settings")
                    if hasattr(self, 'camera_listbox') and self.camera_listbox:
                        self.update_camera_list()
                    return
            
            self.add_default_cameras()
        except Exception as e:
            print(f"❌ Failed to load camera settings: {e}")
            self.add_default_cameras()
    
    def add_default_cameras(self):
        """Add default cameras"""
        self.camera_manager.add_camera("camera1", "rtsp://192.168.1.192:8554/stream")
        if hasattr(self, 'camera_listbox') and self.camera_listbox:
            self.update_camera_list()
    
    def update_camera_list(self):
        """Update camera list"""
        if hasattr(self, 'camera_listbox') and self.camera_listbox:
            self.camera_listbox.delete(0, tk.END)
            for camera_id in self.camera_manager.cameras.keys():
                self.camera_listbox.insert(tk.END, f"📹 {camera_id}")
    
    def add_camera_dialog(self):
        """Add camera dialog (modern)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Camera")
        dialog.geometry("450x200")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
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
            self.save_camera_settings()  
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
        """Remove selected camera"""
        selection = self.camera_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a camera")
            return
        
        camera_id = self.camera_listbox.get(selection[0]).replace("📹 ", "")
        
        if messagebox.askyesno("Confirm", f"Remove camera '{camera_id}'?"):
            if camera_id in self.camera_manager.cameras:
                self.camera_manager.cameras[camera_id]['viewing'] = False
            
            if camera_id in self.camera_manager.fire_events:
                self.stop_fire_recording(camera_id)
            
            self.camera_manager.remove_camera(camera_id)
            
            if camera_id in self.detection_threads:
                del self.detection_threads[camera_id]
            
            if self.selected_camera == camera_id:
                self.selected_camera = None
                self.video_frame.config(image='', text="📹 No camera selected\n\nSelect a camera from the list")
            
            self.update_camera_list()
            self.save_camera_settings()  
            self.status_label.config(text=f"✅ Camera '{camera_id}' removed", fg=self.colors['success'])
    
    def on_camera_select(self, event):
        """When camera is selected"""
        selection = self.camera_listbox.curselection()
        if selection:
            camera_id = self.camera_listbox.get(selection[0]).replace("📹 ", "")
            self.selected_camera = camera_id
            self.start_viewing(camera_id)
    
    def start_viewing(self, camera_id):
        """Start viewing camera (no delay)"""
        if self.viewing_thread and self.viewing_thread.is_alive():
            if self.selected_camera and self.selected_camera in self.camera_manager.cameras:
                self.camera_manager.cameras[self.selected_camera]['viewing'] = False
            time.sleep(0.1)  
        
        if self.display_thread and self.display_thread.is_alive():
            old_selected = self.selected_camera
            self.selected_camera = None
            time.sleep(0.2)  
            self.selected_camera = camera_id  
        
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
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  
            
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
                
                try:
                    if not self.frame_queue.full():
                        self.frame_queue.put((camera_id, frame), block=False)
                except:
                    pass
                
                time.sleep(0.01)  
            
            cap.release()
            cam_info['viewing'] = False
            print(f"🛑 [{camera_id}] Camera view stopped")
        
        def display_frames():
            while self.selected_camera:
                try:
                    cam_id, frame = self.frame_queue.get(timeout=0.1)
                    if cam_id == self.selected_camera:
                        try:
                            detection = self.camera_manager.detectors[cam_id].detect(frame)
                            if detection['fire_detected']:
                                frame = self.camera_manager.detectors[cam_id].draw_detections(frame, detection)
                            
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            frame_resized = cv2.resize(frame_rgb, (1000, 700), interpolation=cv2.INTER_LINEAR)
                            img = Image.fromarray(frame_resized)
                            img_tk = ImageTk.PhotoImage(image=img)
                            
                            self.root.after(0, lambda img=img_tk: self._update_video_frame_safe(img))
                        except (tk.TclError, AttributeError) as e:
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
        """Start detection for all cameras (always runs in background)"""
        print(f"🚀 Starting detection for {len(self.camera_manager.cameras)} camera(s)...")
        for camera_id in self.camera_manager.cameras.keys():
            print(f"   → Starting detection thread for {camera_id}")
            self.start_detection(camera_id)
        print(f"✅ All detection threads started")
    
    def start_detection(self, camera_id):
        """Start fire detection thread"""
        if camera_id in self.detection_threads:
            if self.detection_threads[camera_id].is_alive():
                return
            else:
                del self.detection_threads[camera_id]
        
        def detect_fire():
            try:
                cam_info = self.camera_manager.cameras[camera_id]
                rtsp_url = cam_info['rtsp_url']
                
                print(f"🔌 [{camera_id}] Connecting to stream: {rtsp_url}")
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
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
                detection_interval = 0.3  
                fire_duration = 0
                max_fire_duration = 120  
                no_fire_duration = 0  
                no_fire_threshold = 10.0  
                frame_count = 0
                
                while camera_id in self.camera_manager.cameras:
                    ret, frame = cap.read()
                    if not ret:
                        time.sleep(0.1)
                        continue
                    
                    frame_count += 1
                    
                    if len(fire_event['frames_buffer']) >= fire_event['buffer_size']:
                        fire_event['frames_buffer'].pop(0)
                    fire_event['frames_buffer'].append((frame.copy(), time.time()))
                    
                    current_time = time.time()
                    if current_time - last_detection_time >= detection_interval:
                        detection = detector.detect(frame)
                        last_detection_time = current_time
                        
                        if frame_count % 50 == 0:
                            bbox_count = len(detection.get('bboxes', []))
                            print(f"🔍 [{camera_id}] Frame {frame_count} - Fire: {detection['fire_detected']}, Confidence: {detection['confidence']:.2f}, BBoxes: {bbox_count}")
                            
                            if not detection['fire_detected'] and detection['confidence'] > 0:
                                print(f"   ⚠️ Fire-like pixels detected but below threshold (confidence: {detection['confidence']:.2f})")
                        
                        if detection['fire_detected']:
                            if not fire_event['active']:
                                fire_event['active'] = True
                                fire_event['start_time'] = datetime.now()
                                fire_duration = 0
                                no_fire_duration = 0
                                self.start_fire_recording(camera_id, fire_event['frames_buffer'])
                                print(f"🔥 FIRE DETECTED in {camera_id}! Confidence: {detection['confidence']:.2f}")
                                try:
                                    if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                                        self.root.after(0, lambda cid=camera_id: self.status_label.config(
                                            text=f"🔥 FIRE DETECTED in {cid}!", 
                                            fg=self.colors['accent']
                                        ))
                                except (tk.TclError, AttributeError):
                                    pass
                            
                            no_fire_duration = 0
                            
                            photo_path = self.save_fire_photo(camera_id, frame, detection)
                            print(f"📸 [{camera_id}] Fire photo saved: {photo_path}")
                            
                            if fire_event['video_writer']:
                                fire_event['video_writer'].write(frame)
                                fire_duration += detection_interval
                                
                                if fire_duration >= max_fire_duration:
                                    self.stop_fire_recording(camera_id)
                        else:
                            if fire_event['active']:
                                if fire_event['video_writer']:
                                    fire_event['video_writer'].write(frame)
                                    fire_duration += detection_interval
                                
                                no_fire_duration += detection_interval
                                
                                if no_fire_duration >= no_fire_threshold:
                                    self.stop_fire_recording(camera_id)
                                    print(f"✅ Fire event ended for {camera_id} (recorded {fire_duration:.1f}s)")
                            elif fire_event['video_writer']:
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
                time.sleep(5)
                if camera_id in self.camera_manager.cameras:
                    print(f"🔄 [{camera_id}] Attempting to restart detection thread...")
                    self.start_detection(camera_id)
        
        thread = threading.Thread(target=detect_fire, daemon=True, name=f"Detection-{camera_id}")
        thread.start()
        self.detection_threads[camera_id] = thread
        print(f"✅ [{camera_id}] Detection thread created and started")
    
    def start_fire_recording(self, camera_id, frames_buffer):
        """Start video recording when fire starts (from buffer) - ALWAYS RUNS IN BACKGROUND"""
        fire_event = self.camera_manager.fire_events[camera_id]
        
        timestamp = fire_event['start_time'].strftime("%Y%m%d_%H%M%S")
        video_file = self.fire_videos_dir / f"{camera_id}_fire_{timestamp}.mp4"
        
        if frames_buffer:
            height, width = frames_buffer[0][0].shape[:2]
        else:
            print(f"⚠️ [{camera_id}] No frames in buffer, cannot start recording")
            return
        
        print(f"🎥 [{camera_id}] Starting fire video recording: {video_file.name}")
        
        
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        
        fps = 30
        
        writer = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))
        
        if not writer.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            video_file = self.fire_videos_dir / f"{camera_id}_fire_{timestamp}.avi"
            writer = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))
            
            if not writer.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                video_file = self.fire_videos_dir / f"{camera_id}_fire_{timestamp}.avi"
                writer = cv2.VideoWriter(str(video_file), fourcc, fps, (width, height))
        
        fire_event['video_writer'] = writer
        fire_event['video_file'] = str(video_file)
        
        buffer_frames_written = 0
        for frame, _ in frames_buffer:
            writer.write(frame)
            buffer_frames_written += 1
        
        print(f"📹 [{camera_id}] Wrote {buffer_frames_written} pre-fire frames to video")
    
    def stop_fire_recording(self, camera_id):
        """Stop video recording when fire ends"""
        fire_event = self.camera_manager.fire_events[camera_id]
        
        if fire_event['video_writer']:
            video_file = fire_event.get('video_file', 'unknown')
            fire_event['video_writer'].release()
            fire_event['video_writer'] = None
            print(f"💾 [{camera_id}] Fire video saved: {video_file}")
        
        fire_event['active'] = False
        fire_event['start_time'] = None
        fire_event['frames_buffer'] = []
        
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
                print(f"⚠️ [{camera_id}] Detection thread missing, starting...")
                self.start_detection(camera_id)
            elif not self.detection_threads[camera_id].is_alive():
                print(f"⚠️ [{camera_id}] Detection thread died, restarting...")
                if camera_id in self.detection_threads:
                    del self.detection_threads[camera_id]
                self.start_detection(camera_id)
        
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                active_detections = sum(1 for t in self.detection_threads.values() if t.is_alive())
                total_cameras = len(self.camera_manager.cameras)
                status_text = f"✅ System Ready - {active_detections}/{total_cameras} cameras monitoring"
                self.status_label.config(text=status_text)
        except (tk.TclError, AttributeError):
            pass
        
        self.root.after(10000, self.check_detection_threads)
    
    def save_fire_photo(self, camera_id, frame, detection):
        """Save fire photo (high quality) - ALWAYS RUNS IN BACKGROUND"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        photo_file = self.photos_dir / f"{camera_id}_fire_{timestamp}.jpg"
        
        frame_with_detection = self.camera_manager.detectors[camera_id].draw_detections(frame, detection)
        
        success = cv2.imwrite(str(photo_file), frame_with_detection, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if success:
            return str(photo_file)
        else:
            print(f"❌ [{camera_id}] Failed to save fire photo: {photo_file}")
            return None
    
    def stop_camera_threads(self, camera_id):
        """Stop camera threads"""
        if camera_id in self.camera_manager.cameras:
            self.camera_manager.cameras[camera_id]['viewing'] = False
        
        if camera_id in self.camera_manager.fire_events:
            self.stop_fire_recording(camera_id)
        
        if camera_id in self.detection_threads:
            
            pass
    
    def show_gallery_view(self):
        """Gallery ekranını göster"""
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        gallery_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        gallery_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        header_frame = tk.Frame(gallery_container, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        home_btn = tk.Button(header_frame, text="🏠 Main Menu", 
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
        
        gallery = GalleryFrame(gallery_container, self.photos_dir, self.fire_videos_dir, self.colors)
    
    def open_gallery(self):
        """Open gallery window (old method - backward compatibility)"""
        self.show_gallery_view()
    
    def on_closing(self):
        """When application closes"""
        self.save_camera_settings()
        
        for camera_id in list(self.camera_manager.cameras.keys()):
            if camera_id in self.camera_manager.cameras:
                self.camera_manager.cameras[camera_id]['viewing'] = False
            if camera_id in self.camera_manager.fire_events:
                self.stop_fire_recording(camera_id)
        
        time.sleep(0.5)
        self.root.destroy()


class GalleryFrame:
    """Modern Gallery frame (in main window)"""
    
    def __init__(self, parent, photos_dir, videos_dir, colors):
        self.parent = parent
        self.photos_dir = photos_dir
        self.videos_dir = videos_dir
        self.colors = colors
        self.selected_video = None
        self.video_cap = None
        self.playing = False
        
        style = ttk.Style()
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['secondary'], foreground=self.colors['fg'], padding=15)
        style.map('TNotebook.Tab', background=[('selected', self.colors['accent'])])
        
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        photos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(photos_frame, text="📷 Photos")
        self.setup_photos_tab(photos_frame)
        
        videos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(videos_frame, text="🎥 Fire Event Videos")
        self.setup_videos_tab(videos_frame)
        
        self.load_photos()
        self.load_videos()
    
    def setup_photos_tab(self, parent):
        """Photos tab"""
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="📷 Fire Detection Photos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        refresh_btn = tk.Button(left_frame, text="🔄 Refresh", 
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
        
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
        self.photo_preview = tk.Label(right_frame, text="Select a photo", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.photo_preview.pack(fill=tk.BOTH, expand=True)
    
    def setup_videos_tab(self, parent):
        """Videos tab"""
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="🎥 Fire Event Videos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        refresh_btn = tk.Button(left_frame, text="🔄 Refresh", 
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
        
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
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
        
        self.video_preview = tk.Label(right_frame, text="Select a video", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.video_preview.pack(fill=tk.BOTH, expand=True)
    
    def load_photos(self):
        """Load photos"""
        if not hasattr(self, 'photos_listbox') or not self.photos_listbox:
            return
        
        self.photos_listbox.delete(0, tk.END)
        if self.photos_dir.exists():
            photo_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
            photos = []
            for ext in photo_extensions:
                photos.extend(self.photos_dir.glob(ext))
            
            if photos:
                photos = sorted(photos, key=os.path.getmtime, reverse=True)
                for photo_file in photos:
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
        """Load videos"""
        if not hasattr(self, 'videos_listbox') or not self.videos_listbox:
            return
        
        self.videos_listbox.delete(0, tk.END)
        if self.videos_dir.exists():
            video_extensions = ['*.mp4', '*.avi', '*.mov', '*.MP4', '*.AVI', '*.MOV']
            videos = []
            for ext in video_extensions:
                videos.extend(self.videos_dir.glob(ext))
            
            if videos:
                videos = sorted(videos, key=os.path.getmtime, reverse=True)
                for video_file in videos:
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
        """When photo is selected"""
        selection = self.photos_listbox.curselection()
        if selection:
            photo_entry = self.photos_listbox.get(selection[0])
            if photo_entry == "No photos found":
                return
            
            photo_name = photo_entry.split(" (")[0]
            photo_path = self.photos_dir / photo_name
            
            if photo_path.exists():
                try:
                    img = Image.open(photo_path)
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(image=img)
                    self.photo_preview.config(image=img_tk, text='')
                    self.photo_preview.image = img_tk
                except Exception as e:
                    self.photo_preview.config(text=f"Error loading image: {e}")
            else:
                self.photo_preview.config(text="File not found")
    
    def on_video_select(self, event):
        """When video is selected"""
        selection = self.videos_listbox.curselection()
        if selection:
            video_entry = self.videos_listbox.get(selection[0])
            if video_entry == "No videos found":
                return
            
            video_name = video_entry.split(" (")[0]
            self.selected_video = self.videos_dir / video_name
    
    def play_video(self):
        """Play video"""
        if not hasattr(self, 'selected_video') or not self.selected_video or not self.selected_video.exists():
            messagebox.showwarning("Warning", "Please select a video", parent=self.parent)
            return
        
        if self.video_cap:
            self.video_cap.release()
        
        backends = [cv2.CAP_FFMPEG, cv2.CAP_ANY]
        self.video_cap = None
        
        for backend in backends:
            self.video_cap = cv2.VideoCapture(str(self.selected_video), backend)
            if self.video_cap.isOpened():
                ret, _ = self.video_cap.read()
                if ret:
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  
                    break
                else:
                    self.video_cap.release()
                    self.video_cap = None
        
        if not self.video_cap or not self.video_cap.isOpened():
            messagebox.showerror("Error", "Failed to open video file.\n\nTry opening with external player to check if file is valid.", parent=self.parent)
            return
        
        fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1.0 / fps if fps > 0 else 0.033
        
        self.playing = True
        
        def play():
            try:
                while self.playing and self.video_cap and self.video_cap.isOpened():
                    ret, frame = self.video_cap.read()
                    if not ret or frame is None:
                        self.playing = False
                        break
                    
                    try:
                        if frame.size == 0:
                            continue
                        
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_resized = cv2.resize(frame_rgb, (900, 600), interpolation=cv2.INTER_LINEAR)
                        img = Image.fromarray(frame_resized)
                        img_tk = ImageTk.PhotoImage(image=img)
                        
                        self.parent.after(0, lambda img=img_tk: self._update_video_preview_safe(img))
                        
                        time.sleep(frame_delay)
                    except cv2.error as e:
                        print(f"OpenCV error in video playback: {e}")
                        continue
                    except (tk.TclError, AttributeError) as e:
                        print(f"GUI error in video playback: {e}")
                        self.playing = False
                        break
                    except Exception as e:
                        print(f"Unexpected error in video playback: {e}")
                        continue
            except Exception as e:
                print(f"Critical error in video playback thread: {e}")
            finally:
                if self.video_cap:
                    self.video_cap.release()
                    self.video_cap = None
        
        threading.Thread(target=play, daemon=True).start()
    
    def _update_video_preview_safe(self, img_tk):
        """Thread-safe video preview update"""
        try:
            if hasattr(self, 'video_preview') and self.video_preview.winfo_exists():
                self.video_preview.config(image=img_tk, text='')
                self.video_preview.image = img_tk
        except (tk.TclError, AttributeError):
            pass
    
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
        
        style = ttk.Style()
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['secondary'], foreground=self.colors['fg'], padding=15)
        style.map('TNotebook.Tab', background=[('selected', self.colors['accent'])])
        
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        photos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(photos_frame, text="📷 Photos")
        self.setup_photos_tab(photos_frame)
        
        videos_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(videos_frame, text="🎥 Fire Event Videos")
        self.setup_videos_tab(videos_frame)
        
        self.load_photos()
        self.load_videos()
    
    def setup_photos_tab(self, parent):
        """Photos tab"""
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="📷 Fire Detection Photos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        refresh_btn = tk.Button(left_frame, text="🔄 Refresh", 
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
        
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
        self.photo_preview = tk.Label(right_frame, text="Select a photo", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.photo_preview.pack(fill=tk.BOTH, expand=True)
    
    def setup_videos_tab(self, parent):
        """Videos tab"""
        left_frame = tk.Frame(parent, bg=self.colors['secondary'], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        tk.Label(left_frame, text="🎥 Fire Event Videos", 
                font=("Arial", 14, "bold"),
                bg=self.colors['secondary'], fg=self.colors['fg']).pack(pady=10)
        
        refresh_btn = tk.Button(left_frame, text="🔄 Refresh", 
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
        
        right_frame = tk.Frame(parent, bg=self.colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)
        
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
        
        self.video_preview = tk.Label(right_frame, text="Select a video", 
                                     bg='#000000', fg='#888888',
                                     font=("Arial", 12))
        self.video_preview.pack(fill=tk.BOTH, expand=True)
    
    def load_photos(self):
        """Load photos"""
        if not hasattr(self, 'photos_listbox') or not self.photos_listbox:
            return
        
        self.photos_listbox.delete(0, tk.END)
        if self.photos_dir.exists():
            photo_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
            photos = []
            for ext in photo_extensions:
                photos.extend(self.photos_dir.glob(ext))
            
            if photos:
                photos = sorted(photos, key=os.path.getmtime, reverse=True)
                for photo_file in photos:
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
        """Load videos"""
        if not hasattr(self, 'videos_listbox') or not self.videos_listbox:
            return
        
        self.videos_listbox.delete(0, tk.END)
        if self.videos_dir.exists():
            video_extensions = ['*.mp4', '*.avi', '*.mov', '*.MP4', '*.AVI', '*.MOV']
            videos = []
            for ext in video_extensions:
                videos.extend(self.videos_dir.glob(ext))
            
            if videos:
                videos = sorted(videos, key=os.path.getmtime, reverse=True)
                for video_file in videos:
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
        """When photo is selected"""
        selection = self.photos_listbox.curselection()
        if selection:
            photo_entry = self.photos_listbox.get(selection[0])
            if photo_entry == "No photos found":
                return
            
            photo_name = photo_entry.split(" (")[0]
            photo_path = self.photos_dir / photo_name
            
            if photo_path.exists():
                try:
                    img = Image.open(photo_path)
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(image=img)
                    self.photo_preview.config(image=img_tk, text='')
                    self.photo_preview.image = img_tk
                except Exception as e:
                    self.photo_preview.config(text=f"Error loading image: {e}")
            else:
                self.photo_preview.config(text="File not found")
    
    def on_video_select(self, event):
        """When video is selected"""
        selection = self.videos_listbox.curselection()
        if selection:
            video_entry = self.videos_listbox.get(selection[0])
            if video_entry == "No videos found":
                return
            
            video_name = video_entry.split(" (")[0]
            self.selected_video = self.videos_dir / video_name
    
    def play_video(self):
        """Play video"""
        if not hasattr(self, 'selected_video') or not self.selected_video or not self.selected_video.exists():
            messagebox.showwarning("Warning", "Please select a video", parent=self.window)
            return
        
        if self.video_cap:
            self.video_cap.release()
        
        backends = [cv2.CAP_FFMPEG, cv2.CAP_ANY]
        self.video_cap = None
        
        for backend in backends:
            self.video_cap = cv2.VideoCapture(str(self.selected_video), backend)
            if self.video_cap.isOpened():
                ret, _ = self.video_cap.read()
                if ret:
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    break
                else:
                    self.video_cap.release()
                    self.video_cap = None
        
        if not self.video_cap or not self.video_cap.isOpened():
            messagebox.showerror("Error", "Failed to open video file.\n\nTry opening with external player to check if file is valid.", parent=self.window)
            return
        
        fps = self.video_cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1.0 / fps if fps > 0 else 0.033
        
        self.playing = True
        
        def play():
            try:
                while self.playing and self.video_cap and self.video_cap.isOpened():
                    ret, frame = self.video_cap.read()
                    if not ret or frame is None:
                        
                        self.playing = False
                        break
                    
                    try:
                        if frame.size == 0:
                            continue
                        
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_resized = cv2.resize(frame_rgb, (900, 600), interpolation=cv2.INTER_LINEAR)
                        img = Image.fromarray(frame_resized)
                        img_tk = ImageTk.PhotoImage(image=img)
                        
                        self.window.after(0, lambda img=img_tk: self._update_video_preview_safe(img))
                        
                        time.sleep(frame_delay)
                    except cv2.error as e:
                        print(f"OpenCV error in video playback: {e}")
                        continue
                    except (tk.TclError, AttributeError) as e:
                        print(f"GUI error in video playback: {e}")
                        self.playing = False
                        break
                    except Exception as e:
                        print(f"Unexpected error in video playback: {e}")
                        continue
            except Exception as e:
                print(f"Critical error in video playback thread: {e}")
            finally:
                if self.video_cap:
                    self.video_cap.release()
                    self.video_cap = None
        
        threading.Thread(target=play, daemon=True).start()
    
    def _update_video_preview_safe(self, img_tk):
        """Thread-safe video preview update"""
        try:
            if hasattr(self, 'video_preview') and self.video_preview.winfo_exists():
                self.video_preview.config(image=img_tk, text='')
                self.video_preview.image = img_tk
        except (tk.TclError, AttributeError):
            pass
    
    def stop_video(self):
        """Stop video"""
        self.playing = False
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        try:
            if hasattr(self, 'video_preview') and self.video_preview.winfo_exists():
                self.video_preview.config(image='', text="Select a video")
        except (tk.TclError, AttributeError):
            pass


def main():
    """Ana fonksiyon"""
    root = tk.Tk()
    app = FireDetectionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
