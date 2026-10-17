# SRT-to-WAV-Renamer

<div align="center">

中文 | [English](README.md)

</div>

## 项目简介

SRT-to-WAV-Renamer 是一个命令行工具：从字幕文件（`.srt` / `.ass` / `.vtt`）中提取首句对白，将其作为对应 WAV 音频的新文件名，批量完成重命名、复制/移动，并为 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 等 TTS 训练项目在每个输出子目录生成数据集列表 `.list`。

典型场景：制作 TTS 语音训练数据集时，成百上千个 `000001.wav` 看不出内容，本工具把它们一键改成「首句对白文本.wav」，并生成可直接训练的数据集列表。

作者 B 站主页：[北漠海](https://space.bilibili.com/1065768987) | 视频教程：[click here](https://www.bilibili.com/video/BV1tb8MzhEdN)

项目尚未经过完整测试，如果发现 bug，欢迎 B 站私信作者或加 QQ 群 588526922 反馈，也欢迎直接提 [Issues](https://github.com/beimohai/SRT-to-WAV-Renamer/issues) 和 [Pull requests](https://github.com/beimohai/SRT-to-WAV-Renamer/pulls)（我可能无法及时查看）。

## 功能特性

- **多编码兼容**：按用户指定顺序尝试字幕编码（默认 `utf-8, gbk, utf-16`，UTF-8 优先避免乱码），自动识别并去除 BOM；
- **多格式字幕**：支持 `.srt`、`.ass`、`.vtt`——ASS 取第一条 `Dialogue:` 行的文本字段，VTT 取第一个 cue，均自动跳过文件头；同时清除 HTML/样式标签；
- **多格式音频**：默认可匹配 `.wav`、`.mp3`、`.flac`、`.m4a`、`.ogg`（可用 `-A/--audio` 自定义后缀及优先级），输出保留原始音频格式；
- **多线程加速**：`-j/--jobs` 指定复制并发线程数（默认 4），大数据集复制显著提速；`move` 保持串行以保证安全；
- **预览模式**：`--dry-run` 不创建任何目录、不改动任何文件，只显示将要执行的操作（包括冲突结果）；
- **文件复制/移动**：重命名后可选择复制（默认）或移动音频；
- **未匹配文件处理**：跳过、移动到 `unsigned` 文件夹，或直接删除未命中音频或字幕；
- **冲突策略**：自动添加后缀（`_1`、`_2`…）、覆盖或跳过，支持交互式选择——交互时直接回车即采用提示中的后缀默认项；
- **保留子目录结构**：在输出目录下重现 WAV 输入的子文件夹结构；
- **自动生成/追加列表**：在每个输出子目录生成 `<目录名>.list`，记录格式：

    ```text
    {文件绝对路径}|{说话人}|{说话语言}|{说话内容}
    ```
    例如：
    ```text
    D:\Document\私のオナニーを見てください！.wav|Ayachi Neinei|JP|私のオナニーを見てください！
    ```
    这个列表可直接用于 GPT-SoVITS 等项目的数据集训练；重复运行不会向 `.list` 追加重复条目；

- **安全且幂等**：同一批处理中首句相同的字幕会跳过提示，不会静默互相覆盖；超长文件名自动截断以符合文件系统限制；`.WAV` 等大写扩展名也能正确匹配；
- **零第三方依赖**：仅使用 Python 标准库，支持 Windows / macOS / Linux（Python 3.6 及以上，已在 3.6.8、3.7.9、3.8、3.13 上通过全套测试）。

## 安装方法

1. 克隆仓库：

    ```bash
    git clone https://github.com/beimohai/SRT-to-WAV-Renamer.git
    cd SRT-to-WAV-Renamer
    ```
    或直接下载 ZIP 压缩包；
2. 无需安装任何第三方依赖，仅要求 Python 3.6 及以上（已在 3.6.8、3.7.9、3.8、3.13 上通过全套测试；3.5 及更早版本不支持 f-string）：

    ```bash
    python renamer.py --help
    ```

## 快速开始

```bash
python renamer.py [-w 输入音频目录] [-s 输入字幕目录] [-o 输出目录] [-n 说话人] [-l 说话语言] [-a 匹配成功后的操作] [-e 未匹配文件操作] [-c 冲突处理策略] [-i] [-d] [-E 编码顺序] [-t 字幕后缀] [-A 音频后缀] [-j 线程数] [--min_len 最短文件名]
```

## 参数说明

| 参数   | 参数全称             | 说明                                                               | 默认值      |
| ---- | ---------------- | ---------------------------------------------------------------- | -------- |
| `-w` | `--wav_input`    | 输入音频根目录                                                        | `input`  |
| `-s` | `--srt_input`    | 输入字幕根目录                                                           | 同音频目录 |
| `-o` | `--output`       | 输出根目录                                                             | `output` |
| `-n` | `--speaker`      | 说话人                                                                | 输出子目录名   |
| `-l` | `--language`     | 说话语言，如 `JP`, `EN`, `ZH` 等                                        | `JP`     |
| `-a` | `--wav_action`   | 匹配成功后的操作：复制 `copy`, 移动 `move`                               | `copy`   |
| `-e` | `--extra_action` | **未匹配的音频和字幕**的处理：跳过 `skip`, 移动到 `output/unsigned` 文件夹 `move`, 删除 `delete` | `skip`   |
| `-c` | `--conflict`     | 冲突处理策略：添加后缀“\_1” `suffix`, 覆盖 `overwrite`, 跳过 `skip`             | `skip`   |
| `-i` | `--interactive`  | 开启交互冲突处理（回车即采用后缀默认项）                                             | 否        |
| `-d` | `--dry_run`      | 预览模式，不创建目录、不实际操作文件                                               | 否        |
| `-E` | `--encodings`    | 字幕文件编码尝试顺序（逗号分隔）                                                  | `utf-8,gbk,utf-16` |
| `-t` | `--subs`         | 支持的字幕后缀（逗号分隔）                                                      | `srt,ass,vtt` |
| `-A` | `--audio`        | 可匹配的音频后缀及优先级（逗号分隔），输出保留原始格式                                  | `wav,mp3,flac,m4a,ogg` |
| `-j` | `--jobs`         | 复制并发线程数（`1` 为串行，仅对 `copy` 生效）                                    | `4`      |
|      | `--min_len`      | 文件名最少字符数，低于则跳过                                                     | `1`      |

## 示例代码

```bash
# 基础用法 - 在当前目录操作，使用默认参数
python renamer.py

输入目录结构：
input/
├── Akagi Yuina/
│   ├── 000001.wav
│   ├── 000002.mp3
│   └── 000005.flac
├── Niisato Azu/
│   ├── 000003.wav
│   └── 000004.m4a
├── 000001.srt
├── 000002.srt
├── 000003.ass
├── 000004.vtt
└── 000005.srt

执行后输出目录结构：
output/
├── Akagi Yuina/
│   ├── 浅間のいたずら　鬼の押出し.wav
│   ├── 魔法　うちもみんなみたいに使ってみようと思って.mp3
│   └── 心の奥にある　あなたのお花咲かせる場所.flac
├── Akagi Yuina.list
└── Niisato Azu/
	├── あんたと一緒に歩くとか無理.wav
	└── おばあちゃんになって　魔女になったって無意味.m4a
```

注意：输出文件保留各自原始格式（`.mp3` 仍是 `.mp3` 等），且每个子目录会生成一个 `<目录名>.list` 数据集列表文件。

## 注意事项

- `-e delete` 会同时删除**未匹配的音频和未匹配的字幕文件**，执行前请务必先用 `-d` 预览确认；
- 字幕与音频按文件名匹配（`000001.srt` ↔ `000001.wav`，不区分大小写）；若同一主文件名存在多种格式，按 `-A/--audio` 中列在前面的后缀优先（默认 `wav` 优先于 `mp3`）；若音频位于说话人子目录中，输出目录会重现相同结构；
- 若两个字幕的首句对白相同、指向同一输出文件名，第二个会被跳过并提示（摘要中显示为 `同名重复`），不会静默覆盖；
- 重复运行同一命令是安全的：已存在文件按冲突策略处理，`.list` 不会产生重复条目；
- 文件名会做净化处理：`\ / * ? : " < > |` 替换为 `_`，控制字符被移除，过长文本截断以符合文件系统限制（最多 120 字符 / 180 字节）。

## 更新日志

完整变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## 赞助与支持

如果你喜欢我的项目，你可以在这里对我表达支持，谢谢！

![微信与支付宝收款码](assets/community/support.png)

- [问题反馈](https://github.com/beimohai/SRT-to-WAV-Renamer/issues)
- [作者 GitHub](https://github.com/beimohai)
- [作者 B 站主页](https://space.bilibili.com/1065768987)

## 开源协议

本项目基于 [MIT License](https://github.com/beimohai/SRT-to-WAV-Renamer/blob/main/LICENSE) 开源

_世界因开源更精彩_
