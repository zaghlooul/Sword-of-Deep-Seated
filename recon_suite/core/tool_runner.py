"""
SwordSuite — Tool Runner
QThread wrapper around QProcess for non-blocking tool execution.
"""
from __future__ import annotations

import shutil
from typing import List, Optional

from PyQt6.QtCore import QObject, QProcess, pyqtSignal, QThread


# ---------------------------------------------------------------------------
# Tool availability detection
# ---------------------------------------------------------------------------
TOOL_PATHS: dict[str, Optional[str]] = {}

def detect_tools() -> dict[str, Optional[str]]:
    """Return dict of tool_name -> full path (or None if not found)."""
    global TOOL_PATHS
    candidates = {
        "dorks-eye":   ["dorks-eye", "dorkseye"],
        "katana":      ["katana"],
        "paramspider": ["paramspider"],
        "sqlmap":      ["sqlmap", "sqlmap.py"],
    }
    for name, tries in candidates.items():
        found = None
        for t in tries:
            found = shutil.which(t)
            if found:
                break
        TOOL_PATHS[name] = found
    return TOOL_PATHS

detect_tools()


# ---------------------------------------------------------------------------
# ProcessRunner — QThread that wraps QProcess
# ---------------------------------------------------------------------------
class ProcessRunner(QObject):
    """
    Runs an external command via QProcess.
    Emits line-by-line stdout/stderr and a finished signal.
    """
    stdout_line  = pyqtSignal(str)   # one decoded stdout line
    stderr_line  = pyqtSignal(str)   # one decoded stderr line
    started_sig  = pyqtSignal()
    finished_sig = pyqtSignal(int)   # exit code
    error_sig    = pyqtSignal(str)   # human-readable error

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._cmd: str = ""
        self._args: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, cmd: str, args: List[str], env: Optional[dict] = None) -> None:
        """Start the process."""
        self._cmd  = cmd
        self._args = args

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.started.connect(self.started_sig)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)

        if env:
            pe = self._proc.processEnvironment()
            for k, v in env.items():
                pe.insert(k, v)
            self._proc.setProcessEnvironment(pe)

        self._proc.start(cmd, args)

    def kill(self) -> None:
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()

    def terminate(self) -> None:
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.terminate()

    @property
    def is_running(self) -> bool:
        return (
            self._proc is not None
            and self._proc.state() != QProcess.ProcessState.NotRunning
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _on_stdout(self) -> None:
        if not self._proc:
            return
        data = self._proc.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self.stdout_line.emit(line)

    def _on_stderr(self) -> None:
        if not self._proc:
            return
        data = self._proc.readAllStandardError().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self.stderr_line.emit(line)

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        # Flush any remaining output
        if self._proc:
            remaining = self._proc.readAllStandardOutput().data().decode("utf-8", errors="replace")
            for line in remaining.splitlines():
                if line.strip():
                    self.stdout_line.emit(line)
        self.finished_sig.emit(exit_code)

    def _on_error(self, error) -> None:
        msgs = {
            QProcess.ProcessError.FailedToStart: (
                f"Failed to start '{self._cmd}'. Is it installed and on PATH?"
            ),
            QProcess.ProcessError.Crashed: "Process crashed.",
            QProcess.ProcessError.Timedout: "Process timed out.",
            QProcess.ProcessError.WriteError: "Write error.",
            QProcess.ProcessError.ReadError:  "Read error.",
        }
        self.error_sig.emit(msgs.get(error, f"Unknown process error: {error}"))


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------
def build_katana_cmd(
    urls: List[str],
    depth: int      = 3,
    concurrency: int = 10,
    rate_limit: int  = 150,
    js_crawl: bool   = True,
    headless: bool   = False,
    form_extract: bool = True,
    known_files: bool  = True,
    output_file: str   = "",
    extra_headers: Optional[dict] = None,
    cookies: str       = "",
    passive: bool      = False,
) -> tuple[str, List[str]]:
    cmd = TOOL_PATHS.get("katana") or "katana"
    args: List[str] = []

    # Multiple URLs: write to temp list file or repeat -u
    for url in urls:
        args += ["-u", url]

    args += ["-d", str(depth)]
    args += ["-c", str(concurrency)]
    args += ["-rl", str(rate_limit)]

    if js_crawl:
        args.append("-jc")
    if headless:
        args += ["-hl", "-headless"]
    if form_extract:
        args.append("-form-extraction")
    if known_files:
        args += ["-kf", "all"]
    if passive:
        args.append("-ps")
    if output_file:
        args += ["-o", output_file]
    if cookies:
        args += ["-H", f"Cookie: {cookies}"]
    if extra_headers:
        for k, v in extra_headers.items():
            args += ["-H", f"{k}: {v}"]

    args += ["-silent", "-nc"]
    return cmd, args


def build_paramspider_cmd(
    domain: str,
    exclude: str       = "png,jpg,gif,jpeg,swf,woff,svg,pdf,css",
    placeholder: str   = "FUZZ",
    subs: bool         = False,
    workers: int       = 0,
    output_file: str   = "",
) -> tuple[str, List[str]]:
    cmd = TOOL_PATHS.get("paramspider") or "paramspider"
    args: List[str] = ["-d", domain]

    if exclude:
        args += ["-e", exclude]
    if placeholder and placeholder != "FUZZ":
        args += ["-p", placeholder]
    if subs:
        args.append("-s")
    if workers > 0:
        args += ["--workers", str(workers)]
    if output_file:
        args += ["-o", output_file]

    return cmd, args


def build_sqlmap_cmd(
    url: str,
    method: str           = "GET",
    data: str             = "",
    cookie: str           = "",
    user_agent: str       = "",
    random_agent: bool    = True,
    level: int            = 1,
    risk: int             = 1,
    techniques: List[str] = None,
    dbms: str             = "",
    proxy: str            = "",
    tor: bool             = False,
    tamper: List[str]     = None,
    get_dbs: bool         = False,
    get_tables: bool      = False,
    dump: bool            = False,
    os_shell: bool        = False,
    sql_shell: bool       = False,
    batch: bool           = True,
    threads: int          = 5,
    extra_args: str       = "",
) -> tuple[str, List[str]]:
    cmd = TOOL_PATHS.get("sqlmap") or "sqlmap"
    args: List[str] = ["-u", url]

    if method.upper() == "POST":
        args += ["--method=POST"]
    if data:
        args += ["--data", data]
    if cookie:
        args += ["--cookie", cookie]
    if random_agent:
        args.append("--random-agent")
    elif user_agent:
        args += ["--user-agent", user_agent]

    args += [f"--level={level}", f"--risk={risk}", f"--threads={threads}"]

    if techniques:
        args += [f"--technique={''.join(techniques)}"]
    if dbms:
        args += [f"--dbms={dbms}"]
    if proxy:
        args += [f"--proxy={proxy}"]
    if tor:
        args.append("--tor")
    if tamper:
        args += [f"--tamper={','.join(tamper)}"]

    if get_dbs:
        args.append("--dbs")
    if get_tables:
        args.append("--tables")
    if dump:
        args.append("--dump")
    if os_shell:
        args.append("--os-shell")
    if sql_shell:
        args.append("--sql-shell")
    if batch:
        args.append("--batch")

    if extra_args.strip():
        import shlex
        args += shlex.split(extra_args)

    return cmd, args
