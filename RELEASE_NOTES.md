# SRT-to-WAV-Renamer v1.3

将字幕首句提取为文件名，批量重命名/复制音频，一键生成 GPT-SoVITS 数据集列表。

Turn the first subtitle line into a filename, batch-rename/copy your audio, and get a ready-to-use GPT-SoVITS dataset list.

## 亮点 / Highlights

- 🎵 支持 `wav` / `mp3` / `flac` / `m4a` / `ogg` 多种音频格式（`-A` 可自定义优先级），输出保留原格式
- ⚡ 复制多线程加速（`-j`，默认 4 线程），大数据集明显提速
- 🌐 字幕编码自动回退（`utf-8` 优先，兼容 `GBK`/`UTF-16`/BOM），修复 UTF-8 字幕乱码
- 📝 正确解析 `.srt` / `.ass` / `.vtt`（不再误取文件头）
- 🛡️ 修复 12 项 bug：预览模式零副作用、交互默认项、同批重名防覆盖、`.list` 重跑去重、超长文件名截断、失败逐文件记录等
- 🐍 零第三方依赖，Python 3.6+（3.6.8 / 3.7.9 / 3.8 / 3.13 全套测试通过）

## 快速开始 / Quick start

```bash
git clone https://github.com/beimohai/SRT-to-WAV-Renamer.git
cd SRT-to-WAV-Renamer
python renamer.py -d   # 先预览
python renamer.py      # 实际执行
```

把 `.srt`/`.ass`/`.vtt` 和音频放进 `input/` 即可；完整参数见 [README](README.md)，全部变更见 [CHANGELOG.md](CHANGELOG.md)。

## 致谢 / Credits

作者：[北漠海](https://space.bilibili.com/1065768987) · 视频教程：[bilibili](https://www.bilibili.com/video/BV1tb8MzhEdN) · 反馈：[Issues](https://github.com/beimohai/SRT-to-WAV-Renamer/issues)

MIT License · _世界因开源更精彩_
