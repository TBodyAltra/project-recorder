"""
Audio transcription using Whisper (local, offline).
"""

import subprocess
import whisper
import os
from pathlib import Path


class Transcriber:
    def __init__(self, model="base"):
        """
        Initialize Whisper transcriber.
        model: base, small, medium, large - larger = more accurate but slower
        """
        self.model_name = model
        print(f"Loading Whisper model: {model}...")
        self.model = whisper.load_model(model)
        print("Whisper model loaded.")

    def transcribe(self, video_path, language="zh"):
        """
        Transcribe audio from video file.

        Args:
            video_path: Path to video file
            language: Language code (zh=Chinese, en=English, auto=detect)

        Returns:
            dict with 'text', 'segments', 'language'
        """
        print(f"Transcribing: {video_path}")
        result = self.model.transcribe(
            video_path,
            language=language if language != "auto" else None,
            verbose=True
        )
        return result

    def extract_audio(self, video_path, output_path=None):
        """Extract audio track from video using FFmpeg."""
        if output_path is None:
            output_path = Path(video_path).with_suffix(".wav")

        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            '-y', str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)
        return str(output_path)


if __name__ == "__main__":
    # Test
    t = Transcriber("base")
    print("Transcriber ready.")
