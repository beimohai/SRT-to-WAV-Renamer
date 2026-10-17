# SRT-to-WAV-Renamer

<div align="center">

[中文](README_zh-CN.md) | English

</div>

## Project overview

SRT-to-WAV-Renamer is a command-line tool that extracts the first dialogue line from subtitle files (`.srt` / `.ass` / `.vtt`), uses it as the new filename for the matching WAV audio, and batch-renames, copies/moves files while generating the `.list` dataset file required by [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)-style TTS training pipelines.

Typical scenario: when building a TTS dataset, hundreds of files like `000001.wav` tell you nothing about their content. This tool renames them all to `首句对白文本.wav` and produces a ready-to-use dataset list.

Author on Bilibili: [北漠海](https://space.bilibili.com/1065768987) | Video tutorial: [click here](https://www.bilibili.com/video/BV1tb8MzhEdN)

The project has not undergone exhaustive testing. If you find a bug, contact the author on Bilibili, join QQ group 588526922, or open an [Issue](https://github.com/beimohai/SRT-to-WAV-Renamer/issues) / [Pull request](https://github.com/beimohai/SRT-to-WAV-Renamer/pulls) (I may not review them promptly).

## Features

- **Multi-encoding subtitles**: tries encodings in a configurable order (`utf-8, gbk, utf-16` by default); BOM is detected and stripped automatically;
- **Multi-format subtitles**: `.srt`, `.ass`, `.vtt` — ASS takes the text field of the first `Dialogue:` line, VTT takes the first cue, both correctly skip file headers; HTML/style tags are removed;
- **Multi-format audio**: matches `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg` by default (configurable via `-A/--audio`, matched by priority order); the output file keeps its original format;
- **Fast concurrent copying**: `-j/--jobs` copies files with multiple threads (default 4), much faster on large datasets; `move` stays sequential for safety;
- **Preview mode**: `--dry-run` creates no directories and touches no files, it only shows what would happen — including conflicts;
- **Copy or move**: matched WAV files can be copied (default) or moved;
- **Unmatched file handling**: skip, move to an `unsigned` folder, or delete files that failed to match;
- **Conflict strategies**: auto-suffix (`_1`, `_2`, …), overwrite, or skip — plus an interactive prompt where just pressing <kbd>Enter</kbd> picks the suffix default;
- **Subdirectory structure preserved**: the folder layout of the WAV input is reproduced in the output directory;
- **Dataset list generation**: each output subdirectory gets a `<dirname>.list` file with the format:

    ```text
    {absolute path}|{speaker}|{language}|{text}
    ```
    for example:
    ```text
    D:\Document\私のオナニーを見てください！.wav|Ayachi Neinei|JP|私のオナニーを見てください！
    ```
    The list is directly usable as a GPT-SoVITS training list. Re-running the tool never appends duplicate lines.

- **Idempotent and safe**: same-batch subtitles sharing the same first line are skipped instead of silently overwriting each other; long filenames are truncated to stay within filesystem limits; `.WAV` uppercase extensions are matched too;
- **Zero dependencies**: pure Python standard library, works on Windows / macOS / Linux (Python 3.6+, verified on 3.6.8, 3.7.9, 3.8, and 3.13).

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/beimohai/SRT-to-WAV-Renamer.git
    cd SRT-to-WAV-Renamer
    ```
    or download the ZIP archive;
2. No third-party packages are required. Python 3.6 or newer is the only requirement (3.6.8 / 3.7.9 / 3.8 / 3.13 are verified by the test suite; 3.5 and earlier lack f-string support):

    ```bash
    python renamer.py --help
    ```

## Quick start

```bash
python renamer.py [-w audio input dir] [-s subtitle dir] [-o output dir] [-n speaker] [-l language] [-a copy|move] [-e skip|move|delete] [-c suffix|overwrite|skip] [-i] [-d] [-E encodings] [-t subs] [-A audio] [-j jobs] [--min_len N]
```

## Parameters

| Flag | Long name | Description | Default |
| ---- | ---------------- | ---------------------------------------------------------------- | -------- |
| `-w` | `--wav_input` | Input audio root directory | `input` |
| `-s` | `--srt_input` | Subtitle root directory | same as audio directory |
| `-o` | `--output` | Output root directory | `output` |
| `-n` | `--speaker` | Speaker name | output subdirectory name |
| `-l` | `--language` | Language code, e.g. `JP`, `EN`, `ZH` | `JP` |
| `-a` | `--wav_action` | What to do with matched audio files: copy `copy`, move `move` | `copy` |
| `-e` | `--extra_action` | What to do with **unmatched audio and subtitles**: skip `skip`, move to `output/unsigned` `move`, delete `delete` | `skip` |
| `-c` | `--conflict` | Conflict strategy: auto-suffix `_1` `suffix`, overwrite `overwrite`, skip `skip` | `skip` |
| `-i` | `--interactive` | Resolve conflicts interactively (press <kbd>Enter</kbd> to accept the suffix default) | off |
| `-d` | `--dry_run` | Preview mode: no directories created, no files touched | off |
| `-E` | `--encodings` | Comma-separated encoding trial order for subtitle files | `utf-8,gbk,utf-16` |
| `-t` | `--subs` | Comma-separated subtitle extensions | `srt,ass,vtt` |
| `-A` | `--audio` | Comma-separated audio extensions to match, in priority order; output keeps the original format | `wav,mp3,flac,m4a,ogg` |
| `-j` | `--jobs` | Number of copy threads (`1` = sequential; applies to `copy` only) | `4` |
| | `--min_len` | Minimum filename length in characters; shorter results are skipped | `1` |

## Example

```bash
# Basic usage - run in the current directory with default parameters
python renamer.py

Input directory structure:
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

Output directory structure:
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

Note that the output keeps each file's original format (`.mp3` stays `.mp3`, etc.), and each subdirectory gets a `<dirname>.list` dataset file.

## Notes

- `-e delete` deletes **both** unmatched audio and unmatched subtitle files. Always run with `-d` (preview) first;
- Subtitles are matched to audio by filename (`000001.srt` ↔ `000001.wav`, case-insensitive); when several same-named audio files exist, the extension listed first in `-A/--audio` wins (default `wav` before `mp3`); if audio lives in speaker subdirectories, the same structure is reproduced under the output directory;
- If two subtitle files share the same first dialogue line and target the same output name, the second one is skipped with a warning (reported as `同名重复`) instead of overwriting;
- Running the same command twice is safe: existing files are handled by the conflict strategy and `.list` files never receive duplicate entries;
- Filenames are sanitized: `\ / * ? : " < > |` become `_`, control characters are removed, and overly long text is truncated to fit filesystem limits (max 120 characters / 180 bytes).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full list of changes.

## Sponsorship and support

If you like this project, you can support me here. Thank you!

![WeChat Pay and Alipay payment codes](assets/community/support.png)

- [Report a problem](https://github.com/beimohai/SRT-to-WAV-Renamer/issues)
- [Author on GitHub](https://github.com/beimohai)
- [Author on Bilibili](https://space.bilibili.com/1065768987)

## License

This project is open source under the [MIT License](https://github.com/beimohai/SRT-to-WAV-Renamer/blob/main/LICENSE).

_Open source makes the world more wonderful._
