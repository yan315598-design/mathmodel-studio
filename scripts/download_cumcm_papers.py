"""下载国赛赛题、官方展廊论文和公开 GitHub 论文，生成可追溯语料清单。

本脚本仅用于 skill 维护期。原始资料应保存在外部缓存目录，skill 内只保留
来源清单和蒸馏结果，避免把大体积论文随 skill 分发。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


OFFICIAL_LIST_PAGES = {
    2023: "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2023qgdxssxjmjslwzs/",
    2024: "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2024qgdxssxjmjslwzs/",
    2025: "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2025qgdxssxjmjslwzs/",
}
GITHUB_REPOS = {
    "legacy_misclassified_2023": "zhanwen/MathModel",
    "paper_2025": "Jackyleo-Zhao/cumcm-2025",
    "problems": "CosmicLinks/cumcm-problems",
}
GITHUB_DEFAULT_BRANCHES = {
    "zhanwen/MathModel": "master",
    "Jackyleo-Zhao/cumcm-2025": "main",
    "CosmicLinks/cumcm-problems": "main",
}
USER_AGENT = "mathmodel-studio-cumcm-distiller/1.0"


@dataclass(frozen=True)
class OfficialPaper:
    """保存官方展廊论文的页面信息。"""

    year: int
    title: str
    code: str
    url: str


def build_session() -> requests.Session:
    """创建带退避重试的 HTTP 会话。"""
    retry = Retry(
        total=6,
        connect=6,
        read=6,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
    )
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=12, pool_maxsize=12))
    return session


def sha256_file(path: Path) -> str:
    """计算文件 SHA-256，供来源清单校验。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_code(title: str) -> str:
    """从官方标题中提取 A/B/C 等论文编号。"""
    match = re.search(r"[（(]([A-F]\d+)[）)]", title) or re.search(r"([A-F]\d+)", title)
    return match.group(1) if match else "UNKNOWN"


def detect_chrome(explicit: str | None) -> str | None:
    """寻找 Playwright 可复用的本机 Chrome。"""
    candidates = [
        explicit,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


async def collect_official_papers(years: set[int], chrome: str | None) -> list[OfficialPaper]:
    """用浏览器渲染官方列表页并收集论文详情链接。"""
    from playwright.async_api import async_playwright

    papers: list[OfficialPaper] = []
    async with async_playwright() as playwright:
        launch_args = {"headless": True}
        if chrome:
            launch_args["executable_path"] = chrome
        browser = await playwright.chromium.launch(**launch_args)
        try:
            for year in sorted(years):
                url = OFFICIAL_LIST_PAGES.get(year)
                if not url:
                    continue
                page = await browser.new_page(viewport={"width": 1600, "height": 1200})
                await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                await page.wait_for_timeout(4_000)
                items = await page.eval_on_selector_all(
                    "a[href]",
                    """els => els.map(a => ({
                        text: (a.innerText || a.textContent || '').trim(),
                        href: a.href
                    })).filter(x =>
                        x.href.includes('/zx/a/') &&
                        x.text.includes('全国大学生数学建模竞赛') &&
                        x.text.includes('题论文展示')
                    )""",
                )
                dedup = {item["href"]: item["text"] for item in items}
                papers.extend(
                    OfficialPaper(year, title, extract_code(title), href)
                    for href, title in sorted(dedup.items())
                )
                await page.close()
        finally:
            await browser.close()
    return sorted(papers, key=lambda item: (item.year, item.code, item.url))


def extract_official_images(html: str, base_url: str) -> tuple[str, list[str]]:
    """从论文详情页提取标题和按页排列的图片地址。"""
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".detail-tit")
    title = " ".join(title_node.get_text(" ", strip=True).split()) if title_node else "UNKNOWN"
    urls: list[str] = []
    for image in soup.select("div.detail-content img[src]"):
        source = urljoin(base_url, image.get("src", "").strip())
        if source and source not in urls:
            urls.append(source)
    return title, urls


def fetch_bytes(url: str, timeout: int = 90) -> bytes:
    """下载单个二进制资源并校验非空。"""
    with build_session() as session:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        if not response.content:
            raise ValueError(f"下载内容为空: {url}")
        return response.content


def save_images_as_pdf(blobs: Iterable[bytes], output: Path) -> int:
    """把官方逐页图片按原顺序重建成 PDF。"""
    from PIL import Image

    pages = []
    for blob in blobs:
        with Image.open(io.BytesIO(blob)) as image:
            pages.append(image.convert("RGB"))
    if not pages:
        raise ValueError("未发现可写入的论文页面")
    output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(output, save_all=True, append_images=pages[1:])
    return len(pages)


def download_official_paper(paper: OfficialPaper, output_root: Path, force: bool) -> dict:
    """下载一篇官方展廊论文并返回可追溯记录。"""
    output = output_root / "papers" / "official" / str(paper.year) / f"{paper.year}-{paper.code}.pdf"
    if output.is_file() and output.stat().st_size > 0 and not force:
        return {**asdict(paper), "source": "official_exhibition", "local_path": str(output),
                "bytes": output.stat().st_size, "sha256": sha256_file(output), "status": "skipped"}
    with build_session() as session:
        response = session.get(paper.url, timeout=90)
        response.raise_for_status()
        page_title, image_urls = extract_official_images(response.text, paper.url)
    if not image_urls:
        raise ValueError(f"官方详情页没有论文图片: {paper.url}")
    with ThreadPoolExecutor(max_workers=min(8, len(image_urls))) as pool:
        future_by_index = {pool.submit(fetch_bytes, url): index for index, url in enumerate(image_urls)}
        page_blobs: dict[int, bytes] = {}
        for future in as_completed(future_by_index):
            page_blobs[future_by_index[future]] = future.result()
    pages = save_images_as_pdf([page_blobs[index] for index in range(len(image_urls))], output)
    return {**asdict(paper), "title": page_title, "source": "official_exhibition",
            "local_path": str(output), "bytes": output.stat().st_size,
            "sha256": sha256_file(output), "pages": pages, "status": "downloaded"}


def github_json(url: str) -> dict:
    """读取 GitHub API JSON，并对临时断线自动重试。"""
    last_error: Exception | None = None
    for attempt in range(1, 7):
        try:
            with build_session() as session:
                session.headers["Accept"] = "application/vnd.github+json"
                response = session.get(url, timeout=90)
                response.raise_for_status()
                return response.json()
        except Exception as exc:  # 网络偶发 EOF 时继续退避
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"GitHub API 连续失败: {url}: {last_error}")


def github_tree(repo: str, cache_dir: Path) -> tuple[str, list[dict]]:
    """优先读取缓存，再获取仓库完整文件树。"""
    branch = GITHUB_DEFAULT_BRANCHES[repo]
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{repo.replace('/', '__')}-{branch}.json"
    if cache_path.is_file():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        payload = github_json(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1")
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    if payload.get("truncated"):
        raise RuntimeError(f"GitHub 文件树被截断: {repo}")
    return branch, payload["tree"]


def raw_github_url(repo: str, branch: str, path: str) -> str:
    """构造保留目录层级的 GitHub 原始文件地址。"""
    return f"https://raw.githubusercontent.com/{repo}/{quote(branch, safe='')}/{quote(path, safe='/')}"


def download_stream(url: str, output: Path, expected_size: int | None, force: bool) -> dict:
    """流式下载文件，支持续传式跳过和临时文件保护。"""
    if output.is_file() and output.stat().st_size > 0 and not force:
        if expected_size is None or output.stat().st_size == expected_size:
            return {"local_path": str(output), "bytes": output.stat().st_size,
                    "sha256": sha256_file(output), "status": "skipped"}
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, 7):
        try:
            with build_session() as session, session.get(url, stream=True, timeout=(30, 180)) as response:
                response.raise_for_status()
                with partial.open("wb") as handle:
                    for chunk in response.iter_content(1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            if expected_size is not None and partial.stat().st_size != expected_size:
                raise ValueError(f"文件大小不符: {partial.stat().st_size} != {expected_size}")
            partial.replace(output)
            return {"local_path": str(output), "bytes": output.stat().st_size,
                    "sha256": sha256_file(output), "status": "downloaded"}
        except Exception as exc:
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"文件连续下载失败: {url}: {last_error}")


def select_github_files(problem_years: set[int], cache_dir: Path, include_legacy: bool) -> list[dict]:
    """从三个公开仓库选择论文、代码和历年赛题文件。"""
    selected: list[dict] = []
    if include_legacy:
        repo = GITHUB_REPOS["legacy_misclassified_2023"]
        branch, tree = github_tree(repo, cache_dir)
        for item in tree:
            path = item.get("path", "")
            if item.get("type") == "blob" and path.startswith("国赛论文/2023年优秀论文/") and path.lower().endswith(".pdf"):
                selected.append({"repo": repo, "branch": branch, "path": path, "size": item.get("size"),
                                 "kind": "excluded_non_cumcm_huawei_graduate_2023",
                                 "relative": Path("quarantine/huawei_graduate_2023") / Path(path).relative_to("国赛论文/2023年优秀论文")})

    repo = GITHUB_REPOS["paper_2025"]
    branch, tree = github_tree(repo, cache_dir)
    for item in tree:
        path = item.get("path", "")
        if item.get("type") == "blob" and (path == "paper/paper.pdf" or path.startswith("src/") and path.endswith(".py")):
            selected.append({"repo": repo, "branch": branch, "path": path, "size": item.get("size"),
                             "kind": "paper_2025", "relative": Path("papers/github_2025") / path})

    repo = GITHUB_REPOS["problems"]
    branch, tree = github_tree(repo, cache_dir)
    prefixes = tuple(f"cumcm{year}/" for year in sorted(problem_years))
    for item in tree:
        path = item.get("path", "")
        if item.get("type") == "blob" and path.startswith(prefixes) and path.lower().endswith(".pdf"):
            selected.append({"repo": repo, "branch": branch, "path": path, "size": item.get("size"),
                             "kind": "problem", "relative": Path("problems") / path})
    return selected


def download_github_item(item: dict, output_root: Path, force: bool) -> dict:
    """下载一个 GitHub 语料文件并补充来源字段。"""
    url = raw_github_url(item["repo"], item["branch"], item["path"])
    result = download_stream(url, output_root / item["relative"], item.get("size"), force)
    return {**result, "source": "github", "repo": item["repo"], "branch": item["branch"],
            "source_path": item["path"], "url": url, "kind": item["kind"]}


def write_reports(output_root: Path, records: list[dict], failures: list[dict]) -> None:
    """写入 JSON 来源清单和简短下载报告。"""
    manifest_path = output_root / "download_manifest.json"
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        merged = {item.get("local_path", ""): item for item in previous.get("records", [])}
        merged.update({item.get("local_path", ""): item for item in records})
        records = list(merged.values())
        failures = previous.get("failures", []) + failures
    payload = {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "records": records,
        "failures": failures,
    }
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    counts: dict[str, int] = {}
    for record in records:
        key = record.get("source", "unknown") + ":" + record.get("kind", "paper")
        counts[key] = counts.get(key, 0) + 1
    lines = ["# CUMCM 语料下载报告", "", f"- 成功或续传跳过：{len(records)}", f"- 失败：{len(failures)}", ""]
    lines.extend(f"- {key}: {value}" for key, value in sorted(counts.items()))
    if failures:
        lines.extend(["", "## 失败记录", ""])
        lines.extend(f"- {item.get('source', 'unknown')}: {item.get('error', '')}" for item in failures)
    (output_root / "DOWNLOAD_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_years(value: str) -> set[int]:
    """解析逗号分隔年份或起止年份。"""
    years: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if "-" in part:
            start, end = (int(item) for item in part.split("-", 1))
            years.update(range(start, end + 1))
        elif part:
            years.add(int(part))
    return years


def main() -> int:
    """执行下载并以失败数作为退出状态。"""
    parser = argparse.ArgumentParser(description="下载并校验 CUMCM 深度蒸馏语料")
    parser.add_argument("--output-dir", type=Path, required=True, help="原始语料外部缓存目录")
    parser.add_argument("--official-years", default="2023-2025")
    parser.add_argument("--problem-years", default="2020-2025")
    parser.add_argument("--sources", default="official,github", help="official,github 的逗号组合")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--chrome", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--include-legacy-non-cumcm", action="store_true",
                        help="仅用于复核旧数据；下载后仍不会进入 CUMCM 蒸馏")
    args = parser.parse_args()

    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    sources = {item.strip() for item in args.sources.split(",") if item.strip()}
    records: list[dict] = []
    failures: list[dict] = []

    if "official" in sources:
        official = asyncio.run(collect_official_papers(parse_years(args.official_years), detect_chrome(args.chrome)))
        print(f"官方展廊发现 {len(official)} 篇")
        for index, paper in enumerate(official, 1):
            try:
                record = download_official_paper(paper, output_root, args.force)
                record["kind"] = "paper"
                records.append(record)
                print(f"[{index}/{len(official)}] {record['status']} {paper.year}-{paper.code}")
            except Exception as exc:
                failures.append({"source": "official", "paper": asdict(paper), "error": str(exc)})
                print(f"[{index}/{len(official)}] failed {paper.year}-{paper.code}: {exc}")

    if "github" in sources:
        items = select_github_files(
            parse_years(args.problem_years), output_root / "_github_cache", args.include_legacy_non_cumcm
        )
        print(f"GitHub 清单发现 {len(items)} 个文件")
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 12))) as pool:
            future_map = {pool.submit(download_github_item, item, output_root, args.force): item for item in items}
            completed = 0
            for future in as_completed(future_map):
                completed += 1
                item = future_map[future]
                try:
                    record = future.result()
                    records.append(record)
                    print(f"[{completed}/{len(items)}] {record['status']} {item['path']}")
                except Exception as exc:
                    failures.append({"source": "github", "item": item, "error": str(exc)})
                    print(f"[{completed}/{len(items)}] failed {item['path']}: {exc}")

    records.sort(key=lambda item: item.get("local_path", ""))
    write_reports(output_root, records, failures)
    print(f"完成：成功或跳过 {len(records)}，失败 {len(failures)}，清单 {output_root / 'download_manifest.json'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
