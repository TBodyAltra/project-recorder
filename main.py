"""
Project Recorder GUI - 屏幕录制转项目文档工具
Requires: Windows, Python 3.10+, FFmpeg
"""

import customtkinter as ctk
import threading
import os
import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from recorder import ScreenRecorder, list_screens, list_windows
from transcriber import Transcriber
from analyzer import ProjectAnalyzer
from config import PRESETS, apply_preset, get_provider_display


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ProjectRecorderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Project Recorder - 项目录制助手")
        self.geometry("750x650")

        self.recorder = None
        self.recording_path = None
        self.transcriber = None
        self.analyzer = None
        self.screens = []
        self.windows = []

        self.capture_mode = ctk.StringVar(value="screen")
        self.selected_screen = ctk.IntVar(value=0)
        self.selected_window = ctk.StringVar(value="")
        self.include_audio = ctk.BooleanVar(value=True)
        self.output_dir = ctk.StringVar(value=str(Path.home() / "Recordings"))
        self.status_message = ctk.StringVar(value="就绪")
        self.is_recording = False
        self.recording_start_time = None

        # API settings
        self.provider_var = ctk.StringVar(value="minimax")
        self.vision_api_key = ctk.StringVar(value=os.environ.get("VISION_API_KEY", ""))
        self.vision_base_url = ctk.StringVar(value=os.environ.get("VISION_BASE_URL", "https://api.minimax.chat/v1"))
        self.vision_model = ctk.StringVar(value=os.environ.get("VISION_MODEL", "MiniMax-VL-01"))
        self.llm_api_key = ctk.StringVar(value=os.environ.get("LLM_API_KEY", ""))
        self.llm_base_url = ctk.StringVar(value=os.environ.get("LLM_BASE_URL", "https://api.minimax.chat/v1"))
        self.llm_model = ctk.StringVar(value=os.environ.get("LLM_MODEL", "MiniMax-Text-01"))
        self.whisper_model = ctk.StringVar(value=os.environ.get("WHISPER_MODEL", "base"))

        self._build_ui()
        self._refresh_sources()
        self._load_config()

    def _build_ui(self):
        # Title
        title_label = ctk.CTkLabel(self, text="🎥 项目录制助手", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(20, 10))

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Tab 1: Main
        self.tab_main = self.tabview.add("录制")
        self._build_main_tab()

        # Tab 2: Settings
        self.tab_settings = self.tabview.add("设置")
        self._build_settings_tab()

        # Status Bar
        status_frame = ctk.CTkFrame(self, corner_radius=0, height=30)
        status_frame.pack(fill="x", side="bottom")
        self.status_label = ctk.CTkLabel(status_frame, textvariable=self.status_message, anchor="w")
        self.status_label.pack(side="left", padx=10)

    def _build_main_tab(self):
        main_frame = ctk.CTkFrame(self.tab_main, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === Capture Source ===
        source_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        source_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(source_frame, text="📺 录制来源", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        radio_frame = ctk.CTkFrame(source_frame, fg_color="transparent")
        radio_frame.pack(fill="x", padx=10)

        ctk.CTkRadioButton(radio_frame, text="屏幕", variable=self.capture_mode, value="screen", command=self._on_capture_mode_change).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(radio_frame, text="窗口", variable=self.capture_mode, value="window", command=self._on_capture_mode_change).pack(side="left")

        self.screen_frame = ctk.CTkFrame(source_frame, fg_color="transparent")
        self.screen_frame.pack(fill="x", padx=10, pady=5)
        self.screen_optionmenu = ctk.CTkOptionMenu(self.screen_frame, variable=self.selected_screen, values=["检测中..."])
        self.screen_optionmenu.pack(side="left", fill="x", expand=True)

        self.window_frame = ctk.CTkFrame(source_frame, fg_color="transparent")
        self.window_optionmenu = ctk.CTkOptionMenu(self.window_frame, variable=self.selected_window, values=["检测中..."])
        self.window_optionmenu.pack(side="left", fill="x", expand=True)
        self.window_frame.pack_forget()

        # === Audio Options ===
        audio_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        audio_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(audio_frame, text="🔊 音频选项", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkCheckBox(audio_frame, text="包含系统音频（需安装虚拟音频驱动如 VB-Audio Cable）", variable=self.include_audio).pack(anchor="w", padx=10, pady=(0, 10))

        # === Output Directory ===
        output_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        output_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(output_frame, text="📁 输出目录", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        dir_frame = ctk.CTkFrame(output_frame, fg_color="transparent")
        dir_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.dir_entry = ctk.CTkEntry(dir_frame, textvariable=self.output_dir)
        self.dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_frame, text="浏览", width=60, command=self._browse_output_dir).pack(side="left", padx=(5, 0))

        # === Recording Controls ===
        control_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        control_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(control_frame, text="🎬 录制控制", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        button_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 10))

        self.record_btn = ctk.CTkButton(button_frame, text="⏺ 开始录制", fg_color="#e74c3c", hover_color="#c0392b",
                                         width=140, height=40, font=ctk.CTkFont(size=16, weight="bold"),
                                         command=self._toggle_recording)
        self.record_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(button_frame, text="⏹ 停止", state="disabled",
                                        width=100, height=40, command=self._stop_recording)
        self.stop_btn.pack(side="left", padx=5)

        self.timer_label = ctk.CTkLabel(button_frame, text="00:00", font=ctk.CTkFont(size=20))
        self.timer_label.pack(side="left", padx=15)

        # === Generate Brief ===
        generate_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        generate_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(generate_frame, text="📄 文档生成", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.generate_btn = ctk.CTkButton(generate_frame, text="📄 一键生成项目Brief",
                                            height=45, font=ctk.CTkFont(size=15, weight="bold"),
                                            command=self._generate_brief)
        self.generate_btn.pack(fill="x", padx=10, pady=(0, 10))

    def _build_settings_tab(self):
        settings_frame = ctk.CTkScrollableFrame(self.tab_settings, corner_radius=15)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === Provider Preset ===
        preset_frame = ctk.CTkFrame(settings_frame, corner_radius=10)
        preset_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(preset_frame, text="🔧 API 提供商预设", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(preset_frame, text="选择预设后自动填入对应配置，也可手动修改", text_color="gray").pack(anchor="w", padx=10)

        preset_btn_frame = ctk.CTkFrame(preset_frame, fg_color="transparent")
        preset_btn_frame.pack(fill="x", padx=10, pady=10)

        providers = list(PRESETS.keys())
        for p in providers:
            ctk.CTkButton(preset_btn_frame, text=p.upper(), width=80,
                          command=lambda x=p: self._apply_preset_gui(x)).pack(side="left", padx=2, pady=5)

        # === Vision API ===
        vision_frame = ctk.CTkFrame(settings_frame, corner_radius=10)
        vision_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(vision_frame, text="👁 Vision API（画面分析）", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(vision_frame, text="API Key").pack(anchor="w", padx=10)
        ctk.CTkEntry(vision_frame, textvariable=self.vision_api_key, show="*", width=400).pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(vision_frame, text="Base URL").pack(anchor="w", padx=10)
        ctk.CTkEntry(vision_frame, textvariable=self.vision_base_url, width=400).pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(vision_frame, text="模型名称").pack(anchor="w", padx=10)
        ctk.CTkEntry(vision_frame, textvariable=self.vision_model, width=400).pack(fill="x", padx=10, pady=(0, 10))

        # === LLM API ===
        llm_frame = ctk.CTkFrame(settings_frame, corner_radius=10)
        llm_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(llm_frame, text="🤖 LLM API（文档生成）", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(llm_frame, text="API Key").pack(anchor="w", padx=10)
        ctk.CTkEntry(llm_frame, textvariable=self.llm_api_key, show="*", width=400).pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(llm_frame, text="Base URL").pack(anchor="w", padx=10)
        ctk.CTkEntry(llm_frame, textvariable=self.llm_base_url, width=400).pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(llm_frame, text="模型名称").pack(anchor="w", padx=10)
        ctk.CTkEntry(llm_frame, textvariable=self.llm_model, width=400).pack(fill="x", padx=10, pady=(0, 10))

        # === Whisper ===
        whisper_frame = ctk.CTkFrame(settings_frame, corner_radius=10)
        whisper_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(whisper_frame, text="🎤 Whisper（本地转写，无需API）", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(whisper_frame, text="模型：tiny / base / small / medium / large（越大越准，越慢）").pack(anchor="w", padx=10)
        ctk.CTkOptionMenu(whisper_frame, variable=self.whisper_model,
                          values=["tiny", "base", "small", "medium", "large"]).pack(anchor="w", padx=10, pady=(5, 10))

        # === Save Button ===
        ctk.CTkButton(settings_frame, text="💾 保存配置到 .env",
                       height=40, font=ctk.CTkFont(size=14, weight="bold"),
                       command=self._save_config).pack(fill="x", padx=5, pady=10)

    def _apply_preset_gui(self, name):
        self.provider_var.set(name)
        p = PRESETS.get(name, {})
        self.vision_base_url.set(p.get("vision_base_url", ""))
        self.vision_model.set(p.get("vision_model", ""))
        self.llm_base_url.set(p.get("llm_base_url", ""))
        self.llm_model.set(p.get("llm_model", ""))
        self.status_message.set(f"已应用预设: {name.upper()}")

    def _load_config(self):
        """Load existing .env if present."""
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, val = line.split("=", 1)
                        key, val = key.strip(), val.strip()
                        if key == "PROVIDER":
                            self.provider_var.set(val)
                            self._apply_preset_gui(val)
                        elif key == "VISION_API_KEY":
                            self.vision_api_key.set(val)
                        elif key == "VISION_BASE_URL":
                            self.vision_base_url.set(val)
                        elif key == "VISION_MODEL":
                            self.vision_model.set(val)
                        elif key == "LLM_API_KEY":
                            self.llm_api_key.set(val)
                        elif key == "LLM_BASE_URL":
                            self.llm_base_url.set(val)
                        elif key == "LLM_MODEL":
                            self.llm_model.set(val)
                        elif key == "WHISPER_MODEL":
                            self.whisper_model.set(val)

    def _save_config(self):
        env_file = Path(__file__).parent / ".env"
        lines = [
            f"# Provider preset: openai / minimax / deepseek / siliconflow / zhipuai\n",
            f"PROVIDER={self.provider_var.get()}\n",
            f"\n",
            f"# Vision API\n",
            f"VISION_API_KEY={self.vision_api_key.get()}\n",
            f"VISION_BASE_URL={self.vision_base_url.get()}\n",
            f"VISION_MODEL={self.vision_model.get()}\n",
            f"\n",
            f"# LLM API\n",
            f"LLM_API_KEY={self.llm_api_key.get()}\n",
            f"LLM_BASE_URL={self.llm_base_url.get()}\n",
            f"LLM_MODEL={self.llm_model.get()}\n",
            f"\n",
            f"# Whisper\n",
            f"WHISPER_MODEL={self.whisper_model.get()}\n",
        ]
        with open(env_file, "w") as f:
            f.writelines(lines)
        self.status_message.set("✅ 配置已保存到 .env，重启后生效")

    def _refresh_sources(self):
        def refresh():
            try:
                self.screens = list_screens()
                screen_names = [f"屏幕 {s['index']}: {s['width']}x{s['height']}" + (" (主)" if s.get('primary') else "")
                               for s in self.screens]
                self.screen_optionmenu.configure(values=screen_names)
                if screen_names:
                    self.selected_screen.set(0)
            except Exception as e:
                print(f"Error refreshing screens: {e}")

            try:
                wins = list_windows()
                self.windows = wins
                win_names = [f"{w['title'][:50]}" for w in wins]
                self.window_optionmenu.configure(values=win_names if win_names else ["无可用窗口"])
                if win_names:
                    self.selected_window.set(win_names[0])
            except Exception as e:
                print(f"Error refreshing windows: {e}")

        threading.Thread(target=refresh, daemon=True).start()

    def _on_capture_mode_change(self):
        if self.capture_mode.get() == "screen":
            self.screen_frame.pack(fill="x", padx=10, pady=5)
            self.window_frame.pack_forget()
        else:
            self.screen_frame.pack_forget()
            self.window_frame.pack(fill="x", padx=10, pady=5)

    def _browse_output_dir(self):
        self.status_message.set("请在输入框中直接输入完整路径")

    def _toggle_recording(self):
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        output_dir = Path(self.output_dir.get())
        output_dir.mkdir(parents=True, exist_ok=True)

        self.recorder = ScreenRecorder(str(output_dir))

        try:
            if self.capture_mode.get() == "screen":
                screen_idx = self.selected_screen.get()
                self.recording_path = self.recorder.record_screen(
                    screen_index=screen_idx,
                    include_audio=self.include_audio.get()
                )
            else:
                selected_title = self.selected_window.get()
                wins = list_windows()
                selected_hwnd = None
                for w in wins:
                    if w['title'][:50] == selected_title:
                        selected_hwnd = w['hwnd']
                        break
                if selected_hwnd:
                    self.recording_path = self.recorder.record_window(
                        hwnd=selected_hwnd,
                        include_audio=self.include_audio.get()
                    )

            self.is_recording = True
            self.recording_start_time = time.time()
            self.record_btn.configure(text="⏺ 录制中...", fg_color="#27ae60")
            self.stop_btn.configure(state="normal")
            self.status_message.set(f"录制中: {self.recording_path}")
            self._update_timer()

        except Exception as e:
            self.status_message.set(f"录制失败: {e}")

    def _stop_recording(self):
        if self.recorder:
            path = self.recorder.stop()
            self.is_recording = False
            self.record_btn.configure(text="⏺ 开始录制", fg_color="#e74c3c")
            self.stop_btn.configure(state="disabled")
            self.timer_label.configure(text="00:00")
            self.status_message.set(f"已保存: {path}")
            self.recording_path = path

    def _update_timer(self):
        if self.is_recording:
            elapsed = int(time.time() - self.recording_start_time)
            mins, secs = divmod(elapsed, 60)
            self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
            self.after(1000, self._update_timer)

    def _generate_brief(self):
        if not self.recording_path or not Path(self.recording_path).exists():
            self.status_message.set("错误: 没有可用的录制文件")
            return

        def process():
            try:
                self.status_message.set("正在转写音频...")
                self.update()

                if not self.transcriber:
                    self.transcriber = Transcriber(self.whisper_model.get())

                transcription = self.transcriber.transcribe(self.recording_path, language="zh")

                self.status_message.set("正在分析画面...")
                self.update()

                if not self.analyzer:
                    self.analyzer = ProjectAnalyzer()

                frames_dir = Path(self.recording_path).parent / "frames"
                brief, frames = self.analyzer.analyze_recording(
                    self.recording_path,
                    transcription,
                    output_dir=frames_dir
                )

                brief_path = Path(self.recording_path).with_suffix(".md")
                with open(brief_path, "w", encoding="utf-8") as f:
                    f.write(brief)

                self.status_message.set(f"✅ Brief已生成: {brief_path}")

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.status_message.set(f"生成失败: {e}")

        threading.Thread(target=process, daemon=True).start()


def check_ffmpeg():
    result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print("WARNING: FFmpeg not found in PATH.")
        print("Please install FFmpeg: choco install ffmpeg")


if __name__ == "__main__":
    check_ffmpeg()
    app = ProjectRecorderApp()
    app.mainloop()
