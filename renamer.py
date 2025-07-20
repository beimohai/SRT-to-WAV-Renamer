import os
import re
import shutil
import argparse
import logging
import unicodedata
from collections import defaultdict

# ---------- 美化设置 ----------
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('SRT_Renamer')

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def color(text, code):
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
encodings_list = ['gbk', 'utf-8', 'utf-16']
default_conflict = 'skip'

def robust_file_read(path):
    for e in encodings_list:
        try:
            with open(path, encoding=e, errors='ignore') as f:
                return f.read()
        except:
            print_warning(f"尝试编码 {e} 失败: {path}")
    with open(path, encoding='utf-8', errors='ignore') as f:
        return f.read()

def extract_text_from_sub(path):
    content = robust_file_read(path)
    content = re.sub(r"\d+:\d+:\d+[\.,]\d+ --> \d+:\d+:\d+[\.,]\d+", '', content)
    content = re.sub(r'^\d+\s*$', '', content, flags=re.M)
    content = re.sub(r'<[^>]+>', '', content)
    for line in content.splitlines():
        t = line.strip()
        if t:
            return t
    return None

def get_valid_filename(text):
    text = re.sub(r'[\\/*?:"<>|]', '_', text)
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
    return text.strip('.')[:180]

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def resolve_conflict(dst, strategy, interactive):
    if not os.path.exists(dst):
        return dst
    if interactive:
        choice = input(f"文件已存在 {dst}\n选择操作 [O]verwrite/[S]kip/[U]suffix(default): ").strip().lower()
        if choice == 'o': return dst
        if choice == 's': return None
    if strategy == 'overwrite': return dst
    if strategy == 'skip': return None
    base, ext = os.path.splitext(dst)
    i = 1
    new = f"{base}_{i}{ext}"
    while os.path.exists(new):
        i += 1
        new = f"{base}_{i}{ext}"
    return new

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
    global encodings_list
    encodings_list = [e.strip() for e in args.encodings.split(',') if e.strip()]
    subs_exts = [e.strip().lower() for e in args.subs.split(',') if e.strip()]

    print_header('Srt Wav Renamer 启动')
    print_info(f"项目作者: 北漠海")
    print_info(f"可用编码格式: {','.join(encodings_list)}")
    print_info(f"可用字幕格式: {','.join(subs_exts)}")
    print_info(f"冲突策略: {args.conflict}，交互模式: {args.interactive}")
    print_info(f"预览模式: {args.dry_run}")
    print_info(f"WAV 操作: {args.wav_action}，多余操作: {args.extra_action}\n")

    wav_dir = os.path.abspath(args.wav_input)
    srt_dir = os.path.abspath(args.srt_input) if args.srt_input else wav_dir
    out_dir = os.path.abspath(args.output)
    ensure_dir(out_dir)
    unsigned_dir = os.path.join(out_dir, 'unsigned')

    # 收集所有字幕文件
    srt_files = []
    for root, _, files in os.walk(srt_dir):
        for f in files:
            if f.lower().rsplit('.',1)[-1] in subs_exts:
                srt_files.append(os.path.join(root, f))
    total = len(srt_files)
    digits = len(str(total))

    results = {
        'success': 0,
        'skipped': defaultdict(list),
        'failed': defaultdict(list)
    }
    metadata = defaultdict(list)
    matched_wavs, matched_subs = set(), set()

    for idx, sub_path in enumerate(srt_files, start=1):
        prefix = f"[{str(idx).zfill(digits)}/{total}] "
        filename = os.path.basename(sub_path)
        base = os.path.splitext(filename)[0]

        text = extract_text_from_sub(sub_path)
        if not text:
            results['skipped']['无效内容'].append(filename)
            print_warning(prefix + f"跳过 {filename}: 无效内容")
            continue

        safe = get_valid_filename(text)

        # 找 WAV
        wav_path = None; rel = None
        for wroot, _, wfiles in os.walk(wav_dir):
            if f"{base}.wav" in wfiles:
                wav_path = os.path.join(wroot, f"{base}.wav")
                rel = os.path.relpath(wroot, wav_dir)
                break
        if not wav_path:
            results['skipped']['缺少 WAV'].append(filename)
            print_warning(prefix + f"跳过 {filename}: 未找到 {base}.wav")
            continue

        out_sub = os.path.join(out_dir, rel) if rel and rel!='.' else out_dir
        ensure_dir(out_sub)
        dst = os.path.join(out_sub, f"{safe}.wav")

        final = dst if args.dry_run else resolve_conflict(dst, args.conflict, args.interactive)
        if not final:
            results['skipped']['冲突跳过'].append(filename)
            print_warning(prefix + f"跳过冲突 {os.path.basename(dst)}")
            continue

        # 后缀提示
        suffix_note = None
        if final != dst and args.conflict == 'suffix':
            new_name = os.path.basename(final)
            raw_suffix = new_name[len(safe):]
            suffix_num = os.path.splitext(raw_suffix)[0]
            suffix_note = f"（添加后缀{suffix_num}）"

        try:
            if not args.dry_run:
                if args.wav_action == 'move':
                    shutil.move(wav_path, final)
                else:
                    shutil.copy2(wav_path, final)
            print_success(prefix + f"{base}.wav -> {os.path.basename(final)}", suffix_note)
            results['success'] += 1
            matched_wavs.add(wav_path); matched_subs.add(sub_path)
            metadata[out_sub].append(
                f"{os.path.abspath(final)}|"
                f"{args.speaker or os.path.basename(out_sub)}|"
                f"{args.language}|"
                f"{os.path.splitext(os.path.basename(final))[0]}"
            )
        except Exception as e:
            results['failed']['复制/移动失败'].append(filename)
            print_error(prefix + f"失败 {filename}: {e}")

    # 额外文件处理（skip 默认）
    if not args.dry_run and args.extra_action!='skip':
        for root,_,files in os.walk(wav_dir):
            for wf in files:
                if wf.lower().endswith('.wav'):
                    full = os.path.join(root, wf)
                    if full not in matched_wavs:
                        if args.extra_action == 'move':
                            ensure_dir(unsigned_dir)
                            shutil.move(full, os.path.join(unsigned_dir, wf))
                            print_warning(f"额外移至 unsigned: {wf}")
                        else:
                            os.remove(full)
                            print_warning(f"额外删除: {wf}")
        for root,_,files in os.walk(srt_dir):
            for sf in files:
                if sf.lower().rsplit('.',1)[-1] in subs_exts:
                    full = os.path.join(root, sf)
                    if full not in matched_subs:
                        if args.extra_action == 'move':
                            ensure_dir(unsigned_dir)
                            shutil.move(full, os.path.join(unsigned_dir, sf))
                            print_warning(f"额外移至 unsigned: {sf}")
                        else:
                            os.remove(full)
                            print_warning(f"额外删除: {sf}")

    # 写入 .list 文件
    if not args.dry_run:
        for subdir, entries in metadata.items():
            name = os.path.basename(subdir) or os.path.basename(out_dir)
            lp = os.path.join(subdir, f"{name}.list")
            mode = 'a' if os.path.exists(lp) else 'w'
            with open(lp, mode, encoding='utf-8') as lf:
                lf.write('\n'.join(entries) + '\n')
            print_success(f"已写入列表: {lp}")

    # 总结
    print_summary(total, results)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-w','--wav_input',    default='input',           help='WAV 根目录')
    p.add_argument('-s','--srt_input',    help='字幕根目录')
    p.add_argument('-o','--output',       default='output',          help='输出根目录')
    p.add_argument('-n','--speaker',      default='',                help='说话人')
    p.add_argument('-l','--language',     default='JP',              help='语言代码')
    p.add_argument('-a','--wav_action',   choices=['copy','move'],   default='copy',   help='复制或移动 WAV')
    p.add_argument('-e','--extra_action', choices=['skip','move','delete'], default='skip', help='额外文件处理')
    p.add_argument('-c','--conflict',     choices=['suffix','overwrite','skip'], default='skip', help='冲突策略')
    p.add_argument('-i','--interactive',  action='store_true',       help='交互式冲突解决')
    p.add_argument('-d','--dry_run',      action='store_true',       help='预览模式')
    p.add_argument('-E','--encodings',    default='gbk,utf-8,utf-16', help='读取字幕文件的编码顺序')
    p.add_argument('-t','--subs',         default='srt,ass,vtt',     help='支持字幕格式列表')
    args = p.parse_args()
    main(args)
