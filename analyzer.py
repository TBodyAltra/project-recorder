"""
Analyzer: Extract key frames from video, analyze with Vision AI,
combine with transcription to produce project brief.
"""

import subprocess
import os
import json
import time
from pathlib import Path
from openai import OpenAI


def extract_key_frames(video_path, output_dir, interval_seconds=10, max_frames=20):
    """
    Extract key frames from video at regular intervals.

    Args:
        video_path: Input video file
        output_dir: Where to save frames
        interval_seconds: Extract one frame every N seconds
        max_frames: Maximum number of frames to extract

    Returns:
        List of frame image paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get video duration
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json',
           '-show_format', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = float(json.loads(result.stdout)['format']['duration'])

    # Calculate timestamps
    timestamps = []
    current = interval_seconds
    while current < duration and len(timestamps) < max_frames:
        timestamps.append(current)
        current += interval_seconds

    frame_paths = []
    for i, ts in enumerate(timestamps):
        output_path = output_dir / f"frame_{i:03d}.jpg"
        cmd = [
            'ffmpeg', '-ss', str(ts), '-i', video_path,
            '-vframes', '1', '-q:v', '2',
            '-y', str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)
        if output_path.exists():
            frame_paths.append(str(output_path))

    print(f"Extracted {len(frame_paths)} frames from {duration:.0f}s video")
    return frame_paths


def describe_frame(image_path, client, detail="high"):
    """
    Use Vision AI to describe a single frame.
    """
    with open(image_path, 'rb') as f:
        image_data = f.read()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image_bytes": image_data,
                        "detail": detail
                    },
                    {
                        "type": "text",
                        "text": (
                            "描述这张截图的详细内容，包括：\n"
                            "1. 界面上显示的内容（代码、配置、终端输出等）\n"
                            "2. 任何可见的路径、文件名、URL\n"
                            "3. 命令行参数、环境变量等可复制内容\n"
                            "4. 错误信息或状态指示\n"
                            "请用中文回答，尽量详细。"
                        )
                    }
                ]
            }
        ],
        max_tokens=500
    )
    return response.choices[0].message.content


def generate_project_brief(transcription, frame_descriptions, project_name=None):
    """
    Combine transcription and visual analysis into a structured project brief.

    Args:
        transcription: Whisper output dict with 'text' and 'segments'
        frame_descriptions: List of (timestamp, description) tuples
        project_name: Optional project name override

    Returns:
        Markdown-formatted project brief string
    """
    # Build context for LLM
    context_parts = []

    # Transcription summary
    full_text = transcription.get('text', '')
    if full_text:
        context_parts.append(f"## 语音转写内容\n\n{full_text}\n")

    # Frame descriptions
    if frame_descriptions:
        frames_md = "\n\n".join([
            f"### 帧 @{ts}s\n\n{desc}"
            for ts, desc in frame_descriptions
        ])
        context_parts.append(f"## 截图分析\n\n{frames_md}\n")

    context = "\n\n".join(context_parts)

    # Use OpenAI to generate structured brief
    client = OpenAI()

    prompt = f"""你是一个资深技术顾问，需要根据以下录制内容生成一份项目初始化文档。

请分析以下录音转写和截图分析，提取所有技术细节，生成结构化的项目brief。

---
{context}
---

请生成以下格式的文档（.md格式）：

```markdown
# 项目名称
（从内容中推断，如果无法确定则写"未命名项目"）

## 项目背景
（项目的业务背景、目标、解决的问题）

## 环境与依赖
- 操作系统/平台
- 编程语言及版本
- 关键依赖库/框架
- 硬件要求（如有）

## 基础设施
- 登录凭证（不要包含真实密码，用占位符）
- 容器/环境信息
- 关键路径

## 核心脚本说明
（按顺序列出视频中涉及的所有脚本/命令）
- 脚本路径：
- 功能：
- 关键参数：
- 预期输出：

## 关键配置
- 环境变量
- 配置文件路径
- 配置项说明

## 预期交付物
（视频中提到的预期结果、输出文件、验证方式）

## 约束与注意事项
（任何限制条件、已知问题、注意点）

## 项目初始化步骤
（根据视频内容还原的操作步骤，按顺序列出）
```

请只输出上述格式的文档内容，不要有其他解释。"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )

    brief = response.choices[0].message.content

    # Extract markdown code block if present
    if brief.startswith("```markdown"):
        lines = brief.split('\n')
        brief = '\n'.join(lines[1:-1])  # Remove ```markdown and ```

    return brief


class ProjectAnalyzer:
    def __init__(self, openai_api_key=None):
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()

    def analyze_recording(self, video_path, transcription, output_dir=None, frame_interval=10):
        """
        Full pipeline: extract frames → analyze → generate brief.

        Returns:
            Tuple of (brief_md, frame_descriptions)
        """
        if output_dir is None:
            output_dir = Path(video_path).parent / "frames"

        # Extract key frames
        print("Extracting key frames...")
        frames = extract_key_frames(video_path, output_dir, interval_seconds=frame_interval)

        # Analyze each frame
        print(f"Analyzing {len(frames)} frames with Vision AI...")
        frame_descriptions = []
        for i, frame_path in enumerate(frames):
            print(f"  Analyzing frame {i+1}/{len(frames)}...")
            # Extract timestamp from filename
            ts = int(Path(frame_path).stem.split('_')[1]) if '_' in Path(frame_path).stem else i * frame_interval
            try:
                desc = describe_frame(frame_path, self.client)
                frame_descriptions.append((ts, desc))
            except Exception as e:
                print(f"  Error analyzing frame {i+1}: {e}")
                frame_descriptions.append((ts, f"[分析失败]"))

        # Generate brief
        print("Generating project brief...")
        brief = generate_project_brief(transcription, frame_descriptions)

        return brief, frame_descriptions


if __name__ == "__main__":
    print("Analyzer module ready.")
