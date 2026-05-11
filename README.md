# Project Recorder - 项目录制助手

将屏幕演示+口头解说转换为结构化项目brief文档。

## 功能

1. **多屏幕/窗口录制** - 支持选择主屏幕、第二屏幕或特定窗口
2. **音频录制** - 录制系统音频+麦克风解说
3. **一键生成文档** - 自动转写+画面分析+AI综合=项目brief

## 使用流程

```
1. 选择录制来源（屏幕/窗口）
2. 点击「⏺ 开始录制」
3. 边操作边口头解说
4. 点击「⏹ 停止」
5. 点击「📄 一键生成项目Brief」
6. 查看生成的 .md 文档
```

## 安装

### 1. 安装 FFmpeg（必需）

**方式A：choco（推荐）**
```powershell
choco install ffmpeg
```

**方式B：手动下载**
1. 下载 https://www.gyan.dev/ffmpeg/builds/
2. 解压到 `C:\ffmpeg\bin\`
3. 将 `C:\ffmpeg\bin` 加入系统 PATH

### 2. 安装 Python 依赖

```powershell
cd project-recorder
pip install -r requirements.txt
```

### 3. 安装虚拟音频驱动（可选，如需录制系统音频）

推荐：[VB-Audio Virtual Cable](https://vb-audio.com/Cable/)

录制时选择音频设备为 "CABLE Input" 或 "virtual-audio-capturer"。

### 4. 运行

```powershell
python main.py
```

## 依赖环境

- Windows 10/11
- Python 3.10+
- FFmpeg
- OpenAI API Key（用于Vision分析，填入环境变量 `OPENAI_API_KEY`）

## 输出格式

生成的 `project-brief.md` 包含：

- 项目背景
- 环境与依赖
- 基础设施（登录、容器）
- 核心脚本说明
- 关键配置
- 预期交付物
- 约束与注意事项
- 项目初始化步骤

## 注意事项

- 录制时保持麦克风开启，确保语音清晰
- 画面中避免包含真实密码（用占位符代替）
- 视频较长时，分析时间相应增加
