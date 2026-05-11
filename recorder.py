"""
Screen recorder using FFmpeg + gdigrab (Windows native).
Supports multi-monitor and window capture.
"""

import subprocess
import os
import time
import json
from pathlib import Path


def list_screens():
    """List available screens/displays using Windows QUSER + PowerShell."""
    try:
        # Get screen info via PowerShell
        script = '''
Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
$result = @()
foreach ($s in $screens) {
    $result += @{
        index = $result.Count
        name = $s.DeviceName
        width = $s.Bounds.Width
        height = $s.Bounds.Height
        x = $s.Bounds.X
        y = $s.Bounds.Y
        primary = $s.Primary
    }
}
$result | ConvertTo-Json -Compress
'''
        result = subprocess.run(
            ['powershell', '-Command', script],
            capture_output=True, text=True, encoding='utf-8'
        )
        screens = json.loads(result.stdout)
        # Ensure it's a list
        if isinstance(screens, dict):
            screens = [screens]
        return screens
    except Exception as e:
        print(f"Error listing screens: {e}")
        return [{"index": 0, "name": "Primary", "width": 1920, "height": 1080, "x": 0, "y": 0, "primary": True}]


def list_windows():
    """List available windows for capture."""
    script = '''
Add-Type @"
using System;
using System.Runtime.Interop;
using System.Text;
using System.Collections.Generic;
public class WindowFinder {
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@
$windows = @()
$callback = {
    param($hwnd, $null)
    if ([WindowFinder]::IsWindowVisible($hwnd)) {
        $len = [WindowFinder]::GetWindowTextLength($hwnd)
        if ($len -gt 0) {
            $sb = New-Object System.Text.StringBuilder($len + 1)
            [void][WindowFinder]::GetWindowText($hwnd, $sb, $sb.Capacity)
            $title = $sb.ToString()
            if ($title.Length -gt 0) {
                $script:windows += @{
                    hwnd = $hwnd
                    title = $title
                }
            }
        }
    }
    return $true
}
[WindowFinder]::EnumWindows($callback, [IntPtr]::Zero)
$windows | ConvertTo-Json -Compress
'''
    try:
        result = subprocess.run(
            ['powershell', '-Command', script],
            capture_output=True, text=True, encoding='utf-8'
        )
        windows = json.loads(result.stdout)
        if isinstance(windows, dict):
            windows = [windows]
        return windows
    except Exception as e:
        print(f"Error listing windows: {e}")
        return []


class ScreenRecorder:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else Path.home() / "Recordings"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.process = None
        self.output_file = None
        self.state = "idle"  # idle, recording, stopped

    def get_ffmpeg_path(self):
        """Find ffmpeg in common locations."""
        # Check bin/ subfolder
        local_bin = Path(__file__).parent / "bin" / "ffmpeg.exe"
        if local_bin.exists():
            return str(local_bin)

        # Check PATH
        result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'ffmpeg'

        raise FileNotFoundError("FFmpeg not found. Please install FFmpeg or place ffmpeg.exe in the bin/ folder.")

    def record_screen(self, screen_index=0, include_audio=True, rate=5):
        """
        Start recording a screen.
        
        Args:
            screen_index: Which screen to record (0=primary, 1+=secondary)
            include_audio: Include system audio
            rate: Video framerate
        """
        if self.state == "recording":
            raise RuntimeError("Already recording")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_file = self.output_dir / f"recording_{timestamp}.mkv"
        ffmpeg = self.get_ffmpeg_path()

        # Build FFmpeg command for Windows gdigrab
        # screen_index maps to display ID (0 = primary, 1 = secondary, etc.)
        # gdigrab uses -i "desktop" for all screens, or -i "title=..." for window
        cmd = [
            ffmpeg,
            '-f', 'gdigrab',
            '-framerate', str(rate),
            '-i', f'display:{screen_index}',
        ]

        # Audio options
        if include_audio:
            cmd += ['-f', 'dshow', '-i', 'audio="virtual-audio-capturer"']

        # Video codec
        cmd += [
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',
            str(self.output_file)
        ]

        print(f"Starting recording: {self.output_file}")
        print(f"Command: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.state = "recording"
        return str(self.output_file)

    def record_window(self, hwnd, include_audio=True, rate=5):
        """Record a specific window by HWND."""
        if self.state == "recording":
            raise RuntimeError("Already recording")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_file = self.output_dir / f"recording_{timestamp}.mkv"
        ffmpeg = self.get_ffmpeg_path()

        cmd = [
            ffmpeg,
            '-f', 'gdigrab',
            '-framerate', str(rate),
            '-i', f'title={hwnd}',
        ]

        if include_audio:
            cmd += ['-f', 'dshow', '-i', 'audio="virtual-audio-capturer"']

        cmd += [
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',
            str(self.output_file)
        ]

        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.state = "recording"
        return str(self.output_file)

    def stop(self):
        """Stop recording."""
        if self.state != "recording":
            return None

        # Send q to gracefully stop ffmpeg
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()

        self.state = "stopped"
        return str(self.output_file)

    def get_output_path(self):
        return str(self.output_file)


if __name__ == "__main__":
    # Test: list screens
    print("=== Available Screens ===")
    for s in list_screens():
        print(f"  [{s['index']}] {s['name']} {s['width']}x{s['height']} @ ({s['x']},{s['y']})" +
              (" (Primary)" if s.get('primary') else ""))

    print("\n=== Available Windows ===")
    for w in list_windows()[:10]:
        print(f"  {w['hwnd']}: {w['title'][:60]}")
