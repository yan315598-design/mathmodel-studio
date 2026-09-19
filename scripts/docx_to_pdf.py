"""docx_to_pdf.py — docx 终稿转 PDF (v2.9.0 新增)

docx 终稿通道的呈现环节: 人在 Word 改完呈现层后, 用本脚本出 PDF 供逐页视觉
验收与 cn_spec §10 终审 20 条复查 (协议见 references/docx_final_channel.md)。

转换路径 (按序尝试, 前者成功即返回):
1. Windows 主路径: pywin32 直调 Word COM — Documents.Open 只读 →
   SaveAs(FileFormat=17 即 wdFormatPDF) → Quit; try/finally 保证 Quit,
   防 Word 进程残留 (挂起 COM 服务器会拖垮后续转换)。
2. pywin32 不可用时的 Windows 备选: PowerShell 一行 COM (路径含单引号会失败,
   属已知限制, 建议装 pywin32)。
3. 跨平台兜底: soffice --headless --convert-to pdf --outdir <dir> <file>。

每条路径都先输出到目标旁的**一次性空临时目录**, 确认本次新产物有效后才
os.replace 原子落到目标 (同卷保证原子性)——目录初始为空, 旧 PDF 不可能被
误当新转换成功 (复审 P1-6); 某路径声称成功但无产物时继续降级下一条 (P2-9)。

输出: 同名 .pdf 写到 docx 所在目录 (或 --out 指定路径); 打印页数 (pymupdf 读,
pymupdf 缺失只打提示不影响退出码)。

转换前检测 (v3.1.0): body 直接子层存在尾部带 "(N)" 的 oMathPara 段落 = 未经
呈现层后处理 (编号未右顶格; 字体正斜由 decision_log 政策决定, 不在此检测) →
打印醒目警告并**继续转换** (不阻断;
重导出 export_final_docx.py --presentation 默认开, 或单独跑
docx_presentation_postprocess.py --docx)。

用法:
    python scripts/docx_to_pdf.py submission/cumcm_final_20260916_1240.docx
    python scripts/docx_to_pdf.py final.docx --out out/final.pdf

退出码: 0 转换成功; 1 存在可用转换器但全部转换失败 (或产物落盘失败);
2 用法或环境错误 (docx 不存在 / 无任何可用转换器)。
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WD_FORMAT_PDF = 17  # Word COM SaveAs FileFormat 常量

INSTALL_HINT = ("无可用转换器: 请安装 Microsoft Word 或 LibreOffice 后重试 "
               "(soffice 需在 PATH, 或安装 pywin32 后用 Word COM 主路径)")


def convert_with_word_com(docx_path: Path, pdf_path: Path) -> None:
    """pywin32 直调 Word COM; 异常向上抛由调用方决定是否走兜底。"""
    import win32com.client  # pywin32
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone, 防弹窗卡住无头转换
        doc = word.Documents.Open(str(docx_path), ReadOnly=True)
        try:
            doc.SaveAs2(str(pdf_path), FileFormat=WD_FORMAT_PDF)
        finally:
            doc.Close(False)  # 只读打开, 不保存任何呈现层改动
    finally:
        if word is not None:
            word.Quit()  # COM 服务器必须显式退出, 防残留 WINWORD 进程


def convert_with_powershell(docx_path: Path, pdf_path: Path) -> None:
    """PowerShell 单行 COM 兜底 (pywin32 缺失时的 Windows 备选)。

    路径以单引号注入 PS 字符串, 含单引号的路径会语法错误 (已知限制)。
    """
    ps = (f"$w=New-Object -ComObject Word.Application; "
          f"$w.Visible=$false; "
          f"$d=$w.Documents.Open('{docx_path}', $false, $true); "
          f"$d.SaveAs('{pdf_path}', {WD_FORMAT_PDF}); "
          f"$d.Close($false); $w.Quit()")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"PowerShell COM 退出码 {r.returncode}: "
                           f"{(r.stderr or r.stdout).strip()[:300]}")


def convert_with_soffice(docx_path: Path, pdf_path: Path) -> None:
    """soffice 无头转换; 输出固定为 <outdir>/<stem>.pdf, 与目标名不同则改名。"""
    soffice = shutil.which("soffice")
    if soffice is None:
        raise FileNotFoundError("soffice 不在 PATH")
    r = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf",
         "--outdir", str(pdf_path.parent), str(docx_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    produced = pdf_path.parent / (docx_path.stem + ".pdf")
    if r.returncode != 0 or not produced.is_file():
        raise RuntimeError(f"soffice 退出码 {r.returncode}: "
                           f"{(r.stderr or r.stdout).strip()[:300]}")
    if produced.resolve() != pdf_path.resolve():
        produced.replace(pdf_path)


def warn_unpostprocessed(docx_path: Path) -> None:
    """转换前检测未经呈现层后处理的 docx → 醒目警告, 不阻断转换 (v3.1.0)。

    判据: body 直接子层存在尾部带 "(N)" 的 oMathPara 段落——呈现层后处理
    (docx_presentation_postprocess Step B) 会把这些段落移入表格, body 直接
    子层应为 0。检测器属 docx_presentation_postprocess (stdlib 实现); 该模块
    缺失或 docx 损坏时静默跳过本检查, 不影响转换主链。
    """
    try:
        from docx_presentation_postprocess import find_unprocessed_equation_numbers
        pending = find_unprocessed_equation_numbers(docx_path)
    except Exception:
        return
    if not pending:
        return
    shown = ", ".join(f"({n})" for n in pending[:8]) + ("…" if len(pending) > 8 else "")
    print(f"[WARN] 检测到 {len(pending)} 个编号 display 公式未经呈现层后处理 "
          f"(编号未右顶格; 字体正斜按 decision_log 政策判定, 不在此检测): {shown}")
    print("[WARN] 建议: python scripts/export_final_docx.py 重导出 (--presentation "
          "默认开), 或 python scripts/docx_presentation_postprocess.py --docx 该文件; "
          "本次继续转换")


def available_converters() -> list:
    """探测本机可用的转换器清单 [(名称, 函数)]; 空列表 = 一个都不可用 (exit 2)。"""
    converters = []
    try:
        import win32com.client  # noqa: F401
        converters.append(("Word COM", convert_with_word_com))
    except ImportError:
        pass
    if sys.platform == "win32" and shutil.which("powershell"):
        converters.append(("PowerShell COM", convert_with_powershell))
    if shutil.which("soffice"):
        converters.append(("soffice", convert_with_soffice))
    return converters


def try_converters(converters: list, docx_path: Path, pdf_path: Path) -> tuple:
    """依次尝试转换器, 每条先落到目标旁一次性空临时目录再原子替换。

    返回 (exit_code, 成功转换器名): (0, name) 成功; (1, None) 全部失败。
    临时目录用 tempfile.mkdtemp **独占创建** (v3.1.0 修: 原实现 PID+毫秒命名 +
    exist_ok=True, 两个同 PID 复用/同毫秒并发的进程会共用同一目录, 一方的
    rmtree 会把另一方正在写的产物删掉); mkdtemp 名字唯一且已存在即失败, 因此
    只会清自己的目录。旧 PDF 不可能混入 (目录空), 也不残留垃圾 (P1-6)。
    目标父目录缺失时先建出来 (--out 指向尚不存在的子目录); 建目录/建临时目录
    失败按本函数约定记为错误并降级下一条, 不抛未捕获异常。
    """
    errors = []
    for name, fn in converters:
        try:
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_dir = Path(tempfile.mkdtemp(prefix=".docx2pdf_tmp_",
                                            dir=pdf_path.parent))
        except OSError as e:
            errors.append(f"{name}: 无法创建临时目录 ({e})")
            print(f"[WARN] {name} 临时目录创建失败: {e}")
            continue
        try:
            tmp_out = tmp_dir / pdf_path.name
            try:
                fn(docx_path, tmp_out)
            except Exception as e:  # 单条失败降级下一条, 不中断 (P2-9)
                errors.append(f"{name}: {e}")
                print(f"[WARN] {name} 转换失败: {e}")
                continue
            if not tmp_out.is_file() or tmp_out.stat().st_size == 0:
                errors.append(f"{name}: 未产生有效输出")
                print(f"[WARN] {name} 声称成功但未产生有效 PDF, 降级下一条")
                continue
            os.replace(tmp_out, pdf_path)  # 同卷 (临时目录在目标旁) 原子替换
            return 0, name
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)   # 只清本次自己的目录
    detail = "; ".join(errors[:3])
    print(f"[FAIL] 全部转换路径失败{': ' + detail if detail else ''}")
    return 1, None


def report_page_count(pdf_path: Path) -> None:
    """pymupdf 读页数; 缺失/失败只提示, 不影响转换结果。"""
    try:
        import fitz  # pymupdf
    except ImportError:
        print("[WARN] pymupdf 不可用, 跳过页数统计 (pip install pymupdf 可补)")
        return
    try:
        with fitz.open(pdf_path) as pdf:
            print(f"[OK] 共 {pdf.page_count} 页")
    except Exception as e:  # 页数统计属附加信息, 任何失败降级为提示
        print(f"[WARN] 页数统计失败: {e}")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="docx 终稿转 PDF (Word COM 主路径, soffice 兜底) (v2.9.0)")
    parser.add_argument("docx", type=Path, help="待转换的 docx 文件")
    parser.add_argument("--out", type=Path, default=None,
                        help="输出 PDF 路径 (默认 docx 同目录同名 .pdf)")
    args = parser.parse_args(argv)

    docx_path = args.docx.resolve()
    if not docx_path.is_file():
        print(f"[FAIL] docx 不存在: {docx_path}")
        return 2
    pdf_path = (args.out.resolve() if args.out is not None
                else docx_path.with_suffix(".pdf"))

    warn_unpostprocessed(docx_path)

    converters = available_converters()
    if not converters:
        print(f"[FAIL] {INSTALL_HINT}")
        return 2

    rc, name = try_converters(converters, docx_path, pdf_path)
    if rc != 0:
        return rc
    print(f"[OK] 已转换 PDF ({name}): {pdf_path.resolve()} "
          f"({pdf_path.stat().st_size} 字节)")
    report_page_count(pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
