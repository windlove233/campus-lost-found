# Chinese-CLIP 本地检索

在项目目录打开 PowerShell，用中文描述搜索照片。

```powershell
.\.venv\Scripts\python.exe .\chinese_clip_search.py --query "一个黑色双肩包" --images ".\物品照片"
```

把 `--images` 改成你的照片目录。程序会在指定目录及其子目录中检索，按余弦相似度列出前三张照片的路径。照片直接放在项目目录中时，可用 `--images . --no-recursive` 只扫描当前这一层。默认自动选择 CUDA 或 CPU，可用 `--device cuda` 要求使用 NVIDIA 显卡。

## 首次安装

在 Windows x64 上准备 Python 3.13 和支持 CUDA 12.8 的 NVIDIA 驱动，运行以下命令安装依赖并下载模型。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-chinese-clip.ps1
```

模型使用 [OFA-Sys Chinese-CLIP ViT-B/16](https://huggingface.co/OFA-Sys/chinese-clip-vit-base-patch16)，权重约 753 MB。依赖存放在 `.venv`，模型存放在 `models/chinese-clip-vit-base-patch16`。安装完成后，检索可离线运行。
