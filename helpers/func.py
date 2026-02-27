import asyncio
import os
import re
import time
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

from utils.engine import (
    THREAD_POOL,
    collect_datastore_paths,
    deduplicate_and_order,
    invoke_search_engine,
    is_record_blacklisted,
    release_event_loop,
    tokenize_output_lines,
)

_CHUNK_CUTOFF: int = 10000
_BIG_CHUNK: int = 2500
_SMALL_CHUNK: int = 1000
_MIN_TOKEN_LEN: int = 3

_ULP_LINE_RE: re.Pattern = re.compile(
    r'^(?:https?://)?(?:www\.)?([^/:]+).*?[:|]([^:]+)[:|](.+)$'
)

_CRED_PATTERN_RAW: Dict[str, str] = {
    "mailpass": r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})([:|])([^\s]+)',
    "userpass": r'([a-zA-Z0-9_-]{4,})([:|])([^\s]+)',
    "num_pass":  r'((?:\+?)\d[\d\s\-\(\)]*?\d)([:|])([^\s]+)',
}

_STRUCT_PATTERN_MAP: Dict[str, re.Pattern] = {
    "domain": re.compile(
        r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
    ),
    "url": re.compile(
        r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.]*)?)?(?:#(?:[\w.])*)?)?'
    ),
}

_CRED_PATTERN_COMPILED: Dict[str, re.Pattern] = {
    k: re.compile(v) for k, v in _CRED_PATTERN_RAW.items()
}

ACCEPTED_FORMAT_KEYS: List[str] = list(_CRED_PATTERN_RAW.keys()) + list(_STRUCT_PATTERN_MAP.keys())

_PHONE_STRIP_RE: re.Pattern = re.compile(r'[\s\-\(\)]')

_COMBO_FINDER_RE: re.Pattern = re.compile(r'\b\S+\s*[:;|,]\s*\S+', re.IGNORECASE)
_LOGIN_CHECK_RE: re.Pattern = re.compile(
    r'^(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|\S+)$'
)

_URL_HINTS: Tuple[str, ...] = ('://', 'http', 'android://', 'ftp', '.com', '.org', '.net', 'www.')
_BAD_USER_MARKERS: Tuple[str, ...] = (
    'http', 'www.', 'file:///', 'android://', 'ftp://', 'vgecah', 'warning', 'stopped', 'found'
)
_BAD_PATH_MARKERS: Tuple[str, ...] = (
    'auth', 'login', 'register', 'checkout', 'app', 'classroom', 'store', 'affiliation'
)
_BLOCKED_TLDS: FrozenSet[str] = frozenset({'com', 'org', 'net', 'edu', 'gov', 'io', 'co'})
_COMBO_DELIMITERS: Tuple[str, ...] = (':', '|', ';', ',')
_COMBO_SPLIT_RE: re.Pattern = re.compile(r'[:|]')
_MIN_COMBO_FIELD: int = 3


def _filter_batch(batch: List[str]) -> List[str]:
    out: List[str] = []
    for ln in batch:
        s = ln.strip()
        if s and not is_record_blacklisted(s):
            out.append(s)
    return out


def _reformat_ulp_line(raw: str) -> str:
    m = _ULP_LINE_RE.match(raw.strip())
    if m:
        return f"{m.group(1).strip()}:{m.group(2).strip()}:{m.group(3).strip()}"
    return raw.strip()


def _reformat_ulp_batch(batch: List[str]) -> List[str]:
    return [_reformat_ulp_line(ln) for ln in batch if ln.strip()]


async def _async_filter(lines: List[str]) -> Tuple[List[str], int]:
    total = len(lines)
    chunk = _BIG_CHUNK if total > _CHUNK_CUTOFF else _SMALL_CHUNK
    gathered: List[str] = []
    loop = asyncio.get_running_loop()
    for i in range(0, total, chunk):
        gathered.extend(await loop.run_in_executor(THREAD_POOL, _filter_batch, lines[i:i + chunk]))
        await release_event_loop(i)
    unique, removed = await deduplicate_and_order(gathered)
    return unique, removed


async def _async_reformat_ulp(lines: List[str]) -> List[str]:
    total = len(lines)
    chunk = _BIG_CHUNK if total > _CHUNK_CUTOFF else _SMALL_CHUNK
    out: List[str] = []
    loop = asyncio.get_running_loop()
    for i in range(0, total, chunk):
        out.extend(await loop.run_in_executor(THREAD_POOL, _reformat_ulp_batch, lines[i:i + chunk]))
        await release_event_loop(i)
    return out


async def run_ulp_search(keyword: str, caller_file: str) -> Tuple[List[str], int, float]:
    t0 = time.perf_counter()
    paths = collect_datastore_paths(caller_file)
    if not paths:
        return [], 0, _ms(t0)
    rg = ["rg", "-i", "--no-heading", "--no-line-number", "--no-filename", "--fixed-strings", keyword] + paths
    code, out, _ = await invoke_search_engine(rg)
    if code not in (0, 1):
        return [], 0, _ms(t0)
    raw = tokenize_output_lines(out)
    if not raw:
        return [], 0, _ms(t0)
    unique, removed = await _async_filter(raw)
    reformatted = await _async_reformat_ulp(unique)
    return reformatted, removed, _ms(t0)


def _extract_cred_batch(batch: List[str], fmt: str) -> Tuple[List[str], int]:
    pattern = _CRED_PATTERN_COMPILED[fmt]
    results: List[str] = []
    tally: int = 0
    seen: set = set()
    for ln in batch:
        s = ln.strip()
        if not s or is_record_blacklisted(s):
            continue
        hits = pattern.findall(s)
        if not hits:
            continue
        tally += len(hits)
        ident, sep, pwd = hits[-1]
        if len(ident) < _MIN_TOKEN_LEN or len(pwd) < _MIN_TOKEN_LEN:
            continue
        key = _PHONE_STRIP_RE.sub('', ident) if fmt == "num_pass" else ident
        fp = key.lower()
        if fp not in seen:
            seen.add(fp)
            results.append(f"{ident}{sep}{pwd}")
    return results, tally


def _extract_struct_batch(batch: List[str], fmt: str) -> List[str]:
    pattern = _STRUCT_PATTERN_MAP[fmt]
    results: List[str] = []
    for ln in batch:
        s = ln.strip()
        if not s or is_record_blacklisted(s):
            continue
        for m in pattern.findall(s):
            results.append("".join(m) if isinstance(m, tuple) else str(m))
    return results


async def _run_extraction_pipeline(lines: List[str], fmt: str) -> Tuple[List[str], int]:
    total = len(lines)
    chunk = _BIG_CHUNK if total > _CHUNK_CUTOFF else _SMALL_CHUNK
    gathered: List[str] = []
    loop = asyncio.get_running_loop()
    if fmt in _CRED_PATTERN_COMPILED:
        for i in range(0, total, chunk):
            batch_res, _ = await loop.run_in_executor(THREAD_POOL, _extract_cred_batch, lines[i:i + chunk], fmt)
            gathered.extend(batch_res)
            await release_event_loop(i)
    else:
        for i in range(0, total, chunk):
            gathered.extend(await loop.run_in_executor(THREAD_POOL, _extract_struct_batch, lines[i:i + chunk], fmt))
            await release_event_loop(i)
    unique, removed = await deduplicate_and_order(gathered)
    return unique, removed


async def run_extract_on_datastore(keyword: str, fmt: str, caller_file: str) -> Tuple[List[str], int, float]:
    t0 = time.perf_counter()
    paths = collect_datastore_paths(caller_file)
    if not paths:
        return [], 0, _ms(t0)
    rg = ["rg", "-i", "--no-heading", "--no-line-number", "--no-filename"]
    if fmt in _CRED_PATTERN_RAW:
        rg += ["-e", _CRED_PATTERN_RAW[fmt]]
    else:
        rg += ["--fixed-strings", keyword]
    rg += paths
    code, out, _ = await invoke_search_engine(rg)
    if code not in (0, 1):
        return [], 0, _ms(t0)
    raw = tokenize_output_lines(out)
    if not raw:
        return [], 0, _ms(t0)
    unique, removed = await _run_extraction_pipeline(raw, fmt)
    return unique, removed, _ms(t0)


async def run_extract_on_lines(source_lines: List[str], fmt: str) -> Tuple[List[str], int, float]:
    t0 = time.perf_counter()
    if not source_lines:
        return [], 0, _ms(t0)
    unique, removed = await _run_extraction_pipeline(source_lines, fmt)
    return unique, removed, _ms(t0)


async def read_lines_from_file(file_path: str) -> List[str]:
    def _read() -> List[str]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            return [ln.rstrip("\n") for ln in fh if ln.strip()]
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(THREAD_POOL, _read)


def _scan_combo_batch(batch: List[str]) -> Tuple[List[str], int]:
    results: List[str] = []
    rejected: int = 0
    for ln in batch:
        s = ln.strip()
        if not s or is_record_blacklisted(s):
            rejected += 1
            continue
        segs = [x for x in _COMBO_SPLIT_RE.split(s) if x]
        if len(segs) < 2:
            rejected += 1
            continue
        user = pwd = ""
        if any(h in s.lower()[:30] for h in _URL_HINTS) or s.count(':') >= 2:
            user = segs[-2].strip()
            pwd = segs[-1].strip()
        else:
            found = _COMBO_FINDER_RE.findall(s)
            if not found:
                rejected += 1
                continue
            cand = found[0].strip()
            ok = False
            for delim in _COMBO_DELIMITERS:
                if delim in cand:
                    parts = cand.split(delim, 1)
                    if len(parts) == 2:
                        user, pwd = parts[0].strip(), parts[1].strip()
                        ok = True
                        break
            if not ok:
                rejected += 1
                continue
        if len(user) < _MIN_COMBO_FIELD or len(pwd) < _MIN_COMBO_FIELD:
            rejected += 1
            continue
        ul = user.lower()
        if ul == 'unknown' or not _LOGIN_CHECK_RE.fullmatch(user):
            rejected += 1
            continue
        tld_hit = '.' in ul and '@' not in ul and any(ul.endswith(f'.{t}') for t in _BLOCKED_TLDS)
        path_hit = '@' not in ul and any(m in ul for m in _BAD_PATH_MARKERS)
        if any(m in ul for m in _BAD_USER_MARKERS) or tld_hit or path_hit:
            rejected += 1
            continue
        clean_user = user.replace(' ', '')
        if len(clean_user) < _MIN_COMBO_FIELD:
            rejected += 1
            continue
        results.append(f"{clean_user}:{pwd}")
    return results, rejected


async def _run_combo_pipeline(lines: List[str]) -> Tuple[List[str], int]:
    total = len(lines)
    chunk = _BIG_CHUNK if total > _CHUNK_CUTOFF else _SMALL_CHUNK
    gathered: List[str] = []
    loop = asyncio.get_running_loop()
    for i in range(0, total, chunk):
        res, _ = await loop.run_in_executor(THREAD_POOL, _scan_combo_batch, lines[i:i + chunk])
        gathered.extend(res)
        await release_event_loop(i)
    unique, removed = await deduplicate_and_order(gathered)
    return unique, removed


async def run_combo_search(keyword: str, caller_file: str) -> Tuple[List[str], int, float]:
    t0 = time.perf_counter()
    paths = collect_datastore_paths(caller_file)
    if not paths:
        return [], 0, _ms(t0)
    rg = ["rg", "-i", "--no-heading", "--no-line-number", "--no-filename", "--fixed-strings", keyword] + paths
    code, out, _ = await invoke_search_engine(rg)
    if code not in (0, 1):
        return [], 0, _ms(t0)
    raw = tokenize_output_lines(out)
    if not raw:
        return [], 0, _ms(t0)
    unique, removed = await _run_combo_pipeline(raw)
    return unique, removed, _ms(t0)


def write_result_file(prefix: str, label: str, lines: List[str]) -> str:
    dl_dir = Path(__file__).resolve().parent.parent / "downloads"
    dl_dir.mkdir(exist_ok=True)
    safe = re.sub(r'[^\w\-.]', '_', label)
    path = str(dl_dir / f"{prefix}_{safe}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def write_ulp_file(keyword: str, lines: List[str]) -> str:
    return write_result_file("ULP", keyword, lines)


def get_file_size_str(path: str) -> str:
    b = os.path.getsize(path)
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.2f} KB"
    return f"{b / (1024 * 1024):.2f} MB"


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)
