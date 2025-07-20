# SRT-to-WAV-Renamer
SRT-to-WAV-Renamer 是一个能够将字幕文件（支持 `.srt`、`.ass`、`.vtt` 等）中的首行文字提取为文件名（去除HTML信息），并对同名的 WAV 音频进行批量重命名、复制/移动和列表生成（用于GPT-SoVITS等项目的list制作）的命令行工具。

作者B站主页：[北漠海](https://space.bilibili.com/1065768987)

本项目诸多功能未进行测试，可能存在诸多bug，欢迎B站私信作者或加QQ群588526922反馈，也欢迎直接 [Pull requests](https://github.com/beimohai/SRT-to-WAV-Renamer/pulls)(但我有可能看不到)。本项目的开发目的后续会出视频介绍。

---
## 核心功能

- **多编码兼容**：按用户指定顺序尝试 `GBK`、`UTF-8`、`UTF-16` 等编码读取字幕；
    
- **多格式字幕**：支持 `.srt`、`.ass`、`.vtt` 等常见字幕后缀；
    
- **预览模式**：`--dry_run` 下仅显示将要执行的操作，不做实际改动；
    
- **文件复制/移动**：重命名后可选择复制或移动音频；
    
- **未匹配文件处理**：跳过、移动到 `unsigned` 文件夹或直接删除未命中音频或字幕；
    
- **冲突策略**：自动添加后缀、覆盖或跳过，支持交互式选择；
    
- **保留子目录结构**：在输出目录下重现 WAV 输入的子文件夹结构；
    
- **自动生成/追加列表**：在每个输出子目录生成 `<目录名>.list`，记录格式：

    ```text
    {文件绝对路径}|{说话人}|{说话语言}|{说话内容}
    ```
    例如：
    ```text
    D:\Document\私のオナニーを見てください！.wav|Ayachi Neinei|JA|私のオナニーを見てください！
    ```
    这个列表支持适配GPT-SoVITS等项目所需要的数据集列表。

## 安装方法

1. 克隆仓库：
    
    ```bash
    git clone https://github.com/beimohai/SRT-to-WAV-Renamer.git
    cd srt-wav-renamer
    ```
    或直接下载ZIP压缩包；
2. 安装依赖：
    
    ```bash
    pip install -r requirements.txt
    ```
    要求Python 3.6及以上。
## 快速开始
使用renamer.py：
```bash
python renamer.py [-w 输入 WAV 目录] [-s 输入字幕目录] [-o 输出 WAV 目录] [-n 说话人] [-l 说话语言] [-a 匹配成功后的 WAV 操作] [-e 未匹配的 WAV 操作] [-c 冲突处理策略] [-i] [-d] [-E gbk/utf-8/utf-16]
```
## 参数说明

| 参数   | 参数全称             | 说明                                                               | 默认值      |
| ---- | ---------------- | ---------------------------------------------------------------- | -------- |
| `-w` | `--wav_input`    | 输入 WAV 目录                                                        | `input`  |
| `-s` | `--srt_input`    | 输入字幕目录                                                           | 同 WAV 目录 |
| `-o` | `--output`       | 输出 WAV 目录                                                        | `output` |
| `-n` | `--speaker`      | 说话人                                                              | 子目录名     |
| `-l` | `--language`     | 说话语言，如 `JP`, `EN`, `ZH` 等                                        | `JP`     |
| `-a` | `--wav_action`   | 匹配成功后的 WAV 操作：复制 `copy`, 移动 `move`                               | `copy`   |
| `-e` | `--extra_action` | 未匹配的 WAV 操作：跳过 `skip`, 移动到output\unsigned文件夹 `move`, 删除 `delete` | `skip`   |
| `-c` | `--conflict`     | 冲突处理策略：添加后缀“\_1“ `suffix`, 覆盖 `overwrite`, 跳过 `skip`             | `skip`   |
| `-i` | `--interactive`  | 开启交互冲突处理                                                         | 否        |
| `-d` | `--dry_run`      | 预览模式，不实际操作文件                                                     | 否        |
| `-E` | `--encodings`    | 字幕文件编码尝试，目前支持 `GBK`、`UTF-8`、`UTF-16`                             | `gbk`    |

## 示例代码

```bash
# 基础用法 - 在当前目录操作，使用默认参数
python renamer.py

输入目录结构：
input/
├── Akagi Yuina/
│   ├── 000001.wav
│   ├── 000002.wav
│   └── 000005.wav
├── Niisato Azu/
│   ├── 000003.wav
│   └── 000004.wav
├── 000001.srt
├── 000002.srt
├── 000003.srt
├── 000005.srt
└── 000006.srt

执行后输出目录结构：
output/
├── Akagi Yuina/
│   ├── 浅間のいたずら　鬼の押出し.wav
│   ├── 魔法　うちもみんなみたいに使ってみようと思って.wav
│   └── 心の奥にある　あなたのお花咲かせる場所.wav
└── Niisato Azu/
	├── あんたと一緒に歩くとか無理.wav
	└── おばあちゃんになって　魔女になったって無意味.wav
```
## 开源协议
本项目基于 [MIT license](https://github.com/beimohai/SRT-to-WAV-Renamer/blob/main/LICENSE) 开源

_世界因开源更精彩_