import os
import re
import sys
import shutil
import argparse
import logging
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

__version__ = '1.3'

# ---------- 美化设置 ----------
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('SRT_Renamer')
USE_COLOR = sys.stderr.isatty()  # 重定向到文件时输出纯文本, 避免 ANSI 乱码

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def color(text, code):
    if not USE_COLOR:
        return text
    return f"{code}{text}{Colors.ENDC}"

def print_header(text):
    logger.info(color("\n" + "="*50, Colors.OKBLUE))
    logger.info(color(text.center(50), Colors.BOLD + Colors.OKBLUE))
    logger.info(color("="*50, Colors.OKBLUE))

def print_info(text):
    logger.info(text)

def print_success(main, note=None):
    if note:
        logger.info(f"{color(main, Colors.OKGREEN)}{note}")
    else:
        logger.info(color(main, Colors.OKGREEN))

def print_warning(text):
    logger.info(color(text, Colors.WARNING))

def print_error(text):
    logger.info(color(text, Colors.FAIL))

# 默认参数
DEFAULT_ENCODINGS = 'utf-8,gbk,utf-16'   # UTF-8 优先, 避免 GBK 误读 UTF-8 产生乱码
DEFAULT_SUBS_EXTS = 'srt,ass,vtt'
DEFAULT_AUDIO_EXTS = 'wav,mp3,flac,m4a,ogg'   # 可匹配的音频后缀, 按此优先级匹配同名音频
# Windows 保留设备名, 作为文件名会导致写入失败
WINDOWS_RESERVED = ({'CON', 'PRN', 'AUX', 'NUL'} |
                    {f'COM{i}' for i in range(1, 10)} |
                    {f'LPT{i}' for i in range(1, 10)})

def robust_file_read(path, encodings):
    for e in encodings:
        # UTF-8 顺便吃掉 BOM, 否则 BOM 会变成文件名里的乱码字符
        codec = 'utf-8-sig' if e.lower().replace('_', '-') in ('utf-8', 'utf8') else e
        try:
            with open(path, encoding=codec) as f:
                return f.read()
        except (UnicodeError, LookupError, OSError) as err:
            print_warning(f"编码 {e} 读取失败({err.__class__.__name__}): {os.path.basename(path)}")
    # 兜底: 尽力读取, 不再抛异常
    with open(path, encoding=(encodings[0] if encodings else 'utf-8'), errors='ignore') as f:
        return f.read()

def _first_text_line(lines, skip_index=False):
    for line in lines:
        t = line.strip()
        if not t:
            continue
        if skip_index and re.fullmatch(r'\d+', t):
            continue
        return t
    return None

def _extract_ass(content):
    # ASS: 首行是 [Script Info] 等头信息, 只取 Dialogue 行的文本字段
    for line in content.splitlines():
        if line.startswith('Dialogue:'):
            parts = line.split(',', 9)   # 前 9 个逗号分隔字段, 之后都是文本
            if len(parts) == 10:
                text = re.sub(r'\{[^}]*\}', '', parts[9])   # 去掉样式覆盖标签
                text = text.replace('\\N', ' ').replace('\\n', ' ').replace('\\h', ' ').strip()
                if text:
                    return text
    return None

def _extract_vtt(content):
    # VTT: 首行是 WEBVTT 头, 跳过头与 NOTE/STYLE 块, 取第一个 cue 的文本行
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if '-->' in lines[i]:
            j = i + 1
            while j < len(lines) and lines[j].strip():
                t = re.sub(r'<[^>]+>', '', lines[j]).strip()   # 去掉 <v 说话人> 等标签
                if t:
                    return t
                j += 1
            i = j
        else:
            i += 1
    return None

def _extract_generic(content):
    # SRT: 去掉时间戳行(兼容 mm:ss.mmm 短格式)、序号行、HTML 标签后取首行
    content = re.sub(r"\d{1,2}:\d{2}:\d{2}[\.,]\d{1,3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[\.,]\d{1,3}", '', content)
    content = re.sub(r"\d{1,2}:\d{2}[\.,]\d{1,3}\s*-->\s*\d{1,2}:\d{2}[\.,]\d{1,3}", '', content)
    content = re.sub(r'<[^>]+>', '', content)
    return _first_text_line(content.splitlines(), skip_index=True)

def extract_text_from_sub(path, encodings):
    content = robust_file_read(path, encodings)
    ext = os.path.splitext(path)[1].lower()
    if ext == '.ass':
        return _extract_ass(content)
    if ext == '.vtt':
        return _extract_vtt(content)
    return _extract_generic(content)

def get_valid_filename(text, max_chars=120, max_bytes=180):
    text = re.sub(r'[\\/*?:"<>|]', '_', text)
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
    text = text.strip().strip('.').strip()
    if not text:
        return ''
    # 长度同时受字符数与字节数限制, 防止超出文件系统文件名上限 (ext4 为 255 字节)
    while len(text) > max_chars or len(text.encode('utf-8')) > max_bytes:
        text = text[:-1]
    if text.split('.', 1)[0].upper() in WINDOWS_RESERVED:
        text = '_' + text
    return text

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def unique_path(path, planned=None):
    # 返回不冲突的路径: 磁盘上已存在或本次运行已占用的名字都算冲突
    planned = planned or set()
    def taken(p):
        return os.path.exists(p) or p.lower() in planned
    if not taken(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    new = f"{base}_{i}{ext}"
    while taken(new):
        i += 1
        new = f"{base}_{i}{ext}"
    return new

def resolve_conflict(dst, strategy, interactive, planned=None):
    planned = planned or set()
    def taken(p):
        return os.path.exists(p) or p.lower() in planned
    if not taken(dst):
        return dst
    if interactive:
        while True:
            choice = input(f"文件已存在 {dst}\n选择操作 [O]verwrite/[S]kip/[U]suffix(默认): ").strip().lower()
            if choice in ('', 'u'):   # 回车即默认加后缀, 与提示一致
                return unique_path(dst, planned)
            if choice == 'o':
                return dst
            if choice == 's':
                return None
            print_warning("无效输入, 请输入 O / S / U")
    if strategy == 'overwrite':
        return dst
    if strategy == 'skip':
        return None
    return unique_path(dst, planned)

def print_summary(total, results):
    success = results['success']
    skipped = sum(len(v) for v in results['skipped'].values())
    failed = sum(len(v) for v in results['failed'].values())
    print_info("\n" + "="*50)
    print_info("处理完成摘要".center(50))
    print_info("="*50)
    print_info(f"总文件数: {total}")
    print_info(color(f"成功: {success}", Colors.OKGREEN))
    print_info(color(f"跳过: {skipped}", Colors.WARNING))
    print_info(color(f"失败: {failed}", Colors.FAIL))
    if failed:
        print_error("\n失败详情：")
        for reason, files in results['failed'].items():
            print_error(f"  {reason} ({len(files)}):")
            for fn in files:
                print_error(f"    - {fn}")

def main(args):
    encodings = [e.strip() for e in args.encodings.split(',') if e.strip()]
    subs_exts = [e.strip().lower().lstrip('.') for e in args.subs.split(',') if e.strip()]
    audio_exts = [e.strip().lower().lstrip('.') for e in args.audio.split(',') if e.strip()]
    jobs = max(1, args.jobs)

    print_header(f'Srt to Wav Renamer v{__version__} 启动')
    print_info(f"项目作者: 北漠海")
    print_info(f"可用编码格式: {','.join(encodings)}")
    print_info(f"可用字幕格式: {','.join(subs_exts)}")
    print_info(f"可用音频格式: {','.join(audio_exts)}")
    print_info(f"冲突策略: {args.conflict}，交互模式: {args.interactive}")
    print_info(f"预览模式: {args.dry_run}")
    print_info(f"音频操作: {args.wav_action}（并发 {jobs}），多余操作: {args.extra_action}\n")

    wav_dir = os.path.abspath(args.wav_input)
    srt_dir = os.path.abspath(args.srt_input) if args.srt_input else wav_dir
    out_dir = os.path.abspath(args.output)
    if not args.dry_run:   # 预览模式不创建任何目录
        ensure_dir(out_dir)
    unsigned_dir = os.path.join(out_dir, 'unsigned')

    # 一次性建立音频索引(小写文件名 -> 路径与相对目录), 不区分大小写且避免每个字幕重复遍历
    audio_index = {}
    for aroot, dirs, afiles in os.walk(wav_dir):
        dirs.sort()
        for af in sorted(afiles):
            if os.path.splitext(af)[1].lower().lstrip('.') in audio_exts:
                key = af.lower()
                if key in audio_index:
                    print_warning(f"音频重名(仅匹配第一个): {os.path.relpath(os.path.join(aroot, af), wav_dir)}")
                    continue
                audio_index[key] = (os.path.join(aroot, af), os.path.relpath(aroot, wav_dir))

    # 收集所有字幕文件(排序保证输出与后缀编号稳定)
    srt_files = []
    for root, dirs, files in os.walk(srt_dir):
        dirs.sort()
        for f in sorted(files):
            ext = f.lower().rsplit('.', 1)[-1]
            if ext in subs_exts:
                srt_files.append(os.path.join(root, f))
    srt_files.sort()
    total = len(srt_files)
    digits = len(str(total))

    results = {'success': 0, 'skipped': defaultdict(list), 'failed': defaultdict(list)}
    metadata = defaultdict(list)
    matched_wavs, matched_subs = set(), set()
    # 本次运行已占用的目标路径(小写); 预览模式下文件不会落盘, 用它模拟冲突
    planned = set()
    # 规划阶段登记的传输任务, 执行阶段统一(可并发)完成
    tasks = []

    for idx, sub_path in enumerate(srt_files, 1):
        prefix = f"[{str(idx).zfill(digits)}/{total}] "
        filename = os.path.basename(sub_path)
        base = os.path.splitext(filename)[0]

        text = extract_text_from_sub(sub_path, encodings)
        if not text:
            results['skipped']['无效内容'].append(filename)
            print_warning(prefix + f"跳过 {filename}: 无效内容")
            continue

        safe = get_valid_filename(text)
        if len(safe) < max(args.min_len, 1):
            results['skipped']['无效内容'].append(filename)
            print_warning(prefix + f"跳过 {filename}: 字幕文本过短或无有效字符")
            continue

        # 找对应音频 (不区分大小写, 按 --audio 顺序优先匹配, 如 000001.srt 可匹配 000001.mp3)
        hit = None; src_ext = None
        for aext in audio_exts:
            cand = audio_index.get(f"{base}.{aext}".lower())
            if cand:
                hit = cand; src_ext = aext; break
        if not hit:
            results['skipped']['缺少音频'].append(filename)
            print_warning(prefix + f"跳过 {filename}: 未找到同名音频 ({'/'.join(audio_exts)})")
            continue
        wav_path, rel = hit

        out_sub = os.path.join(out_dir, rel) if rel and rel != '.' else out_dir
        if not args.dry_run:
            ensure_dir(out_sub)
        # 输出保留原音频格式 (000001.mp3 -> 首句文本.mp3)
        dst = os.path.join(out_sub, f"{safe}.{src_ext}")

        # 本批内首句文本重复: 跳过, 防止 overwrite 策略下静默覆盖与列表重复条目
        if dst.lower() in planned:
            results['skipped']['同名重复'].append(filename)
            print_warning(prefix + f"跳过 {filename}: 本批已生成同名文件 {os.path.basename(dst)}")
            continue

        final = resolve_conflict(dst, args.conflict, args.interactive, planned)
        if not final:
            results['skipped']['冲突跳过'].append(filename)
            print_warning(prefix + f"跳过冲突 {os.path.basename(dst)}")
            continue
        # 目标是已存在目录: 无法覆盖, 提前记为失败 (否则 copy2 会误复制进目录内部)
        if os.path.isdir(final):
            results['failed']['目标是目录'].append(filename)
            print_error(prefix + f"失败 {filename}: 目标路径是已存在目录 {os.path.basename(final)}")
            continue
        planned.add(final.lower())

        # 冲突后缀提示
        suffix_note = None
        if final != dst:
            num = os.path.splitext(os.path.basename(final))[0][len(safe):]
            suffix_note = f"（添加后缀{num}）"

        # 规划阶段只登记任务, 文件操作统一在执行阶段完成 (复制可多线程加速)
        tasks.append({
            'prefix': prefix, 'base': base, 'src_ext': src_ext,
            'src': wav_path, 'dst': final, 'out_sub': out_sub,
            'filename': filename, 'sub': sub_path, 'note': suffix_note,
        })

    # 执行阶段: dry-run 不落盘; move 串行(元数据操作, 并发无收益); copy 按 --jobs 并发
    def _transfer(task):
        if args.wav_action == 'move':
            shutil.move(task['src'], task['dst'])
        else:
            shutil.copy2(task['src'], task['dst'])

    outcomes = []
    if args.dry_run or jobs <= 1 or args.wav_action == 'move':
        for t in tasks:
            try:
                if not args.dry_run:
                    _transfer(t)
                outcomes.append(None)
            except Exception as e:
                outcomes.append(e)
    else:
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            futures = [ex.submit(_transfer, t) for t in tasks]
            for fut in futures:
                try:
                    fut.result()
                    outcomes.append(None)
                except Exception as e:
                    outcomes.append(e)

    # 按规划顺序统一输出日志与统计, 保证输出稳定可复现
    for t, err in zip(tasks, outcomes):
        if err is None:
            print_success(t['prefix'] + f"{t['base']}.{t['src_ext']} -> {os.path.basename(t['dst'])}", t['note'])
            results['success'] += 1
            matched_wavs.add(t['src']); matched_subs.add(t['sub'])
            metadata[t['out_sub']].append(
                f"{os.path.abspath(t['dst'])}|"
                f"{args.speaker or os.path.basename(t['out_sub'])}|"
                f"{args.language}|"
                f"{os.path.splitext(os.path.basename(t['dst']))[0]}"
            )
        else:
            planned.discard(t['dst'].lower())
            results['failed']['复制/移动失败'].append(t['filename'])
            print_error(t['prefix'] + f"失败 {t['filename']}: {err}")

    # 额外文件处理（skip 默认）
    if not args.dry_run and args.extra_action != 'skip':
        for root, _, files in os.walk(wav_dir):
            for wf in files:
                if os.path.splitext(wf)[1].lower().lstrip('.') in audio_exts:
                    full = os.path.join(root, wf)
                    if full not in matched_wavs:
                        try:
                            if args.extra_action == 'move':
                                ensure_dir(unsigned_dir)
                                shutil.move(full, unique_path(os.path.join(unsigned_dir, wf)))
                                print_warning(f"额外移至 unsigned: {wf}")
                            else:
                                os.remove(full)
                                print_warning(f"额外删除: {wf}")
                        except Exception as e:
                            results['failed']['额外处理失败'].append(wf)
                            print_error(f"额外处理失败 {wf}: {e}")
        for root, _, files in os.walk(srt_dir):
            for sf in files:
                if sf.lower().rsplit('.', 1)[-1] in subs_exts:
                    full = os.path.join(root, sf)
                    if full not in matched_subs:
                        try:
                            if args.extra_action == 'move':
                                ensure_dir(unsigned_dir)
                                shutil.move(full, unique_path(os.path.join(unsigned_dir, sf)))
                                print_warning(f"额外移至 unsigned: {sf}")
                            else:
                                os.remove(full)
                                print_warning(f"额外删除: {sf}")
                        except Exception as e:
                            results['failed']['额外处理失败'].append(sf)
                            print_error(f"额外处理失败 {sf}: {e}")

    # 写入 .list 文件 (已存在的条目不重复追加, 重复运行不产生重复行)
    if not args.dry_run:
        for subdir, entries in metadata.items():
            name = os.path.basename(subdir) or os.path.basename(out_dir)
            lp = os.path.join(subdir, f"{name}.list")
            old_paths = set()
            if os.path.exists(lp):
                with open(lp, encoding='utf-8') as lf:
                    old_paths = {ln.split('|', 1)[0].strip() for ln in lf if '|' in ln}
            new_entries = [e for e in entries if e.split('|', 1)[0] not in old_paths]
            if new_entries:
                mode = 'a' if os.path.exists(lp) else 'w'
                with open(lp, mode, encoding='utf-8') as lf:
                    lf.write('\n'.join(new_entries) + '\n')
                print_success(f"已写入列表: {lp}（{len(new_entries)} 条）")
            else:
                print_warning(f"列表已包含全部条目, 跳过: {lp}")

    print_summary(total, results)


if __name__=='__main__':
    p = argparse.ArgumentParser(description='将字幕首句提取为文件名, 批量重命名/复制音频并生成 GPT-SoVITS 列表')
    p.add_argument('-V','--version',     action='version', version=f'SRT-to-WAV-Renamer {__version__}')
    p.add_argument('-w','--wav_input',   default='input',   help='音频根目录')
    p.add_argument('-s','--srt_input',   help='字幕根目录(默认与音频目录相同)')
    p.add_argument('-o','--output',      default='output',  help='输出根目录')
    p.add_argument('-n','--speaker',     default='',        help='说话人(默认取输出子目录名)')
    p.add_argument('-l','--language',    default='JP',      help='语言代码')
    p.add_argument('-a','--wav_action',  choices=['copy','move'], default='copy', help='复制或移动音频')
    p.add_argument('-e','--extra_action', choices=['skip','move','delete'], default='skip', help='未匹配的音频/字幕处理')
    p.add_argument('-c','--conflict',    choices=['suffix','overwrite','skip'], default='skip', help='冲突策略')
    p.add_argument('-i','--interactive', action='store_true', help='交互式冲突解决')
    p.add_argument('-d','--dry_run',     action='store_true', help='预览模式(不创建目录、不改动文件)')
    p.add_argument('-E','--encodings',   default=DEFAULT_ENCODINGS, help='字幕编码尝试顺序')
    p.add_argument('-t','--subs',        default=DEFAULT_SUBS_EXTS, help='支持的字幕后缀, 逗号分隔')
    p.add_argument('-A','--audio',       default=DEFAULT_AUDIO_EXTS, help='可匹配的音频后缀及优先级, 逗号分隔, 输出保留原格式')
    p.add_argument('-j','--jobs',        type=int, default=4, help='复制并发线程数(1=串行, 仅对 copy 生效)')
    p.add_argument('--min_len',          type=int, default=1, help='文件名最少字符数, 低于则跳过')
    args = p.parse_args()
    main(args)
