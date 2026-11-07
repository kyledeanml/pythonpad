#!/usr/bin/env python3
"""
PythonPad - Python Tools Engine
Provides configurable Python interpreter execution, interactive REPL shell,
native AST syntax verification, and Pylint diagnostics.
"""

import os
import sys
import io
import json
import code
import codecs
import signal
import shutil
import builtins
import tempfile
import subprocess
import threading
import time
import ast


class Diagnostic:
    """Represents a single linter diagnostic (error, warning, convention, etc.)."""

    __slots__ = ("line", "column", "severity", "code", "message", "symbol")

    def __init__(self, line=1, column=1, severity="convention", code="", message="", symbol=""):
        self.line = max(1, int(line) if isinstance(line, (int, str)) and str(line).isdigit() else 1)
        self.column = max(1, int(column) if isinstance(column, (int, str)) and str(column).isdigit() else 1)
        self.severity = (severity or "convention").lower()
        self.code = code or ""
        self.message = message or ""
        self.symbol = symbol or ""

    def __repr__(self):
        return f"<Diagnostic [{self.severity.upper()}] L{self.line}:C{self.column} {self.code}: {self.message}>"


class InterpreterManager:
    """Detects and manages system base and custom Python interpreters."""

    _active_interpreter = None
    _version_cache = {}

    @classmethod
    def _resolve_binary(cls, path: str):
        """Resolve a path to an executable Python binary (handling directories gracefully)."""
        if not path:
            return None
        expanded = os.path.abspath(os.path.expanduser(path))
        if os.path.isdir(expanded):
            for sub in ("python", "python3", os.path.join("bin", "python3"), os.path.join("bin", "python")):
                cand = os.path.join(expanded, sub)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return os.path.realpath(cand)
            return None
        if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
            return os.path.realpath(expanded)
        return None

    @classmethod
    def get_default_interpreter(cls) -> str:
        candidates = [
            os.path.expanduser("~/.local/bin/python3"),
            "/usr/local/bin/Python-3.12.16/python",
            shutil.which("python3"),
            sys.executable,
            "/usr/bin/python3",
        ]
        for c in candidates:
            resolved = cls._resolve_binary(c)
            if resolved:
                return resolved
        return sys.executable or "/usr/bin/python3"

    @classmethod
    def get_active_interpreter(cls) -> str:
        resolved = cls._resolve_binary(cls._active_interpreter)
        if resolved:
            return resolved
        return cls.get_default_interpreter()

    @classmethod
    def set_active_interpreter(cls, path: str) -> bool:
        resolved = cls._resolve_binary(path)
        if resolved:
            cls._active_interpreter = resolved
            return True
        return False

    @classmethod
    def get_interpreter_version(cls, path=None) -> str:
        interp = cls._resolve_binary(path) if path else cls.get_active_interpreter()
        if not interp:
            return "Python 3"
        try:
            mtime = os.path.getmtime(interp)
            cache_key = (interp, mtime)
            if cache_key in cls._version_cache:
                return cls._version_cache[cache_key]

            res = subprocess.run(
                [interp, "--version"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=3,
                check=False
            )
            ver = (res.stdout.strip() or res.stderr.strip() or "Python 3").splitlines()[0]
            cls._version_cache[cache_key] = ver
            return ver
        except Exception:
            return "Python 3"

    @classmethod
    def detect_system_interpreters(cls) -> list:
        """Scan standard Linux paths for installed Python interpreters."""
        found = []
        candidates = [
            os.path.expanduser("~/.local/bin/python3"),
            "/usr/local/bin/Python-3.12.16/python",
            "/usr/bin/python3",
            "/usr/bin/python3.12",
            "/usr/bin/python3.11",
            "/usr/bin/python3.10",
            shutil.which("python3"),
            sys.executable,
        ]
        seen = set()
        for path in candidates:
            resolved = cls._resolve_binary(path)
            if resolved and resolved not in seen:
                seen.add(resolved)
                ver = cls.get_interpreter_version(resolved)
                found.append((path if os.path.isfile(os.path.expanduser(path or "")) else resolved, ver))
        return found


class _ShellExitHint:
    """Safe replacement for exit()/quit() inside the in-process interactive shell."""

    def __repr__(self):
        return "Use Ctrl+F6 (or Restart Shell button) to reset the shell, or Ctrl+Q to quit PythonPad."

    def __call__(self, code=None):
        print(self.__repr__())


class _NonBlockingStdin(io.StringIO):
    """Prevents raw sys.stdin.readline() from deadlocking the GTK main thread."""

    def __init__(self, input_handler=None):
        super().__init__()
        self._input_handler = input_handler

    def readline(self, *args, **kwargs):
        if self._input_handler is not None:
            val = self._input_handler("")
            if val is not None:
                return val + "\n"
        raise EOFError(
            "Interactive stdin cannot block the shell without input. "
            "Use the Script Runner (F5) console input bar for interactive scripts."
        )


class InteractiveShellSession:
    """
    Persistent Python interactive REPL session.
    Maintains variables, functions, and state across commands safely.
    """

    def __init__(self, input_handler=None):
        self.input_handler = input_handler
        self.locals = self._create_clean_locals()
        self.console = code.InteractiveConsole(self.locals)
        self.banner = (
            f"PythonPad Interactive Shell\n"
            f"Interpreter: {InterpreterManager.get_active_interpreter()} ({InterpreterManager.get_interpreter_version()})\n"
            f"Type Python expressions below. Use Up/Down arrows for command history.\n"
        )
        self.buffer = []

    def _shell_input(self, prompt=""):
        if prompt:
            sys.stdout.write(str(prompt))
            sys.stdout.flush()
        if self.input_handler is not None:
            res = self.input_handler(str(prompt))
            if res is not None:
                print(res)
                return res
            raise EOFError("Input cancelled")
        raise EOFError("Interactive input() requires a UI input handler or Script Runner (F5).")

    def _create_clean_locals(self):
        exit_hint = _ShellExitHint()
        return {
            '__name__': '__main__',
            '__doc__': 'PythonPad Interactive Shell',
            '__package__': None,
            'exit': exit_hint,
            'quit': exit_hint,
            'input': self._shell_input,
        }

    def restart(self):
        """Reset the shell environment to a clean state."""
        self.locals = self._create_clean_locals()
        self.console = code.InteractiveConsole(self.locals)
        self.buffer.clear()
        return "=== Shell Restarted: Clean Global State ===\n"

    def push_line(self, line: str):
        """
        Push a line to the console safely.
        Catches SystemExit and KeyboardInterrupt so they never crash the main application.
        Returns (output_text, is_continuation_needed).
        """
        out_capture = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        old_stdin = sys.stdin
        old_input = builtins.input
        sys.stdout = out_capture
        sys.stderr = out_capture
        sys.stdin = _NonBlockingStdin(self.input_handler)
        builtins.input = self._shell_input

        more = False
        try:
            more = self.console.push(line)
        except SystemExit as e:
            out_capture.write(f"[SystemExit: {e.code if e.code is not None else 0}]\n")
            self.console.resetbuffer()
            more = False
        except KeyboardInterrupt:
            out_capture.write("\nKeyboardInterrupt\n")
            self.console.resetbuffer()
            more = False
        except BaseException:
            self.console.showtraceback()
            self.console.resetbuffer()
            more = False
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin
            builtins.input = old_input

        output = out_capture.getvalue().replace("\x00", "\ufffd")
        return output, more


class PythonLinter:
    """Runs Pylint or native AST analysis on Python code."""

    @staticmethod
    def is_pylint_available() -> bool:
        """Check whether pylint is installed in PATH."""
        return shutil.which("pylint") is not None

    @classmethod
    def lint(cls, file_path=None, content=""):
        """
        Runs linting on the given file path or text content.
        Returns (diagnostics_list, status_summary_str, is_pylint_used).
        """
        diagnostics = []

        # 1. Native AST syntax check first
        ast_errors = cls._check_ast_syntax(content, file_path)
        if ast_errors:
            return ast_errors, "Syntax error detected in Python code.", False

        # 2. Pylint if available
        if cls.is_pylint_available():
            pylint_diags = cls._run_pylint(file_path, content)
            if pylint_diags is not None:
                diagnostics.extend(pylint_diags)
                summary = cls._format_summary(diagnostics, pylint_used=True)
                return diagnostics, summary, True

        # 3. Fallback: Syntax OK
        summary = "Native Python Syntax OK. (Install 'pylint' for deep code inspection)"
        return diagnostics, summary, False

    @staticmethod
    def _check_ast_syntax(content, file_path=None):
        """Perform native Python AST and compile parse to detect syntax errors."""
        if not content:
            return []
        try:
            filename = file_path or "<buffer>"
            ast.parse(content, filename=filename)
            compile(content, filename, "exec")
            return []
        except SyntaxError as e:
            msg = e.msg or "Syntax error"
            line = e.lineno or 1
            col = e.offset or 1
            return [Diagnostic(
                line=line,
                column=col,
                severity="error",
                code="E0001",
                message=f"SyntaxError: {msg}",
                symbol="syntax-error"
            )]
        except Exception as e:
            return [Diagnostic(
                line=1,
                column=1,
                severity="error",
                code="E0000",
                message=str(e),
                symbol="parse-error"
            )]

    @classmethod
    def _run_pylint(cls, file_path, content):
        """Execute pylint CLI with JSON output format safely."""
        temp_file = None
        target_path = file_path

        if not target_path or not os.path.exists(target_path) or content is not None:
            try:
                fd, temp_file = tempfile.mkstemp(prefix="pythonpad_lint_", suffix=".py")
                with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content if content else "")
                target_path = temp_file
            except Exception as e:
                print(f"Error creating temp file for pylint: {e}")
                return None

        cmd = [
            "pylint",
            "--output-format=json",
            "--reports=n",
            "--score=n",
            "--",
            os.path.abspath(target_path)
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=15,
                check=False
            )
            stdout = proc.stdout.strip()
            if not stdout:
                return []

            raw_data = json.loads(stdout)
            results = []
            for item in raw_data:
                raw_type = item.get("type", "convention").lower()
                severity = "error" if raw_type in ("error", "fatal") else raw_type

                results.append(Diagnostic(
                    line=item.get("line", 1),
                    column=max(1, int(item.get("column", 0)) + 1),
                    severity=severity,
                    code=item.get("message-id", ""),
                    message=item.get("message", ""),
                    symbol=item.get("symbol", "")
                ))
            return results
        except Exception as e:
            print(f"Pylint execution error: {e}")
            return None
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

    @staticmethod
    def _format_summary(diagnostics, pylint_used=True):
        if not diagnostics:
            return "Pylint: Clean! No issues found." if pylint_used else "Python Syntax OK."

        counts = {"error": 0, "warning": 0, "refactor": 0, "convention": 0}
        for d in diagnostics:
            counts[d.severity] = counts.get(d.severity, 0) + 1

        parts = []
        if counts["error"]:
            parts.append(f"{counts['error']} error(s)")
        if counts["warning"]:
            parts.append(f"{counts['warning']} warning(s)")
        if counts["refactor"]:
            parts.append(f"{counts['refactor']} refactor(s)")
        if counts["convention"]:
            parts.append(f"{counts['convention']} convention(s)")

        tool = "Pylint" if pylint_used else "Syntax Checker"
        return f"{tool}: {', '.join(parts)}"


class PythonRunner:
    """Manages asynchronous execution of Python scripts using the system base interpreter."""

    def __init__(self):
        self.process = None
        self._thread = None
        self._lock = threading.Lock()
        self.is_running = False

    def run(self, file_path, on_output, on_finished, script_args=None, custom_interpreter=None):
        """
        Runs the python script in a background thread using the selected interpreter.
        on_output(text: str, is_stderr: bool)
        on_finished(returncode: int)
        """
        with self._lock:
            if self.is_running:
                return False
            if not file_path or not os.path.isfile(file_path):
                on_output(f"Error: File '{file_path}' does not exist on disk. Save the file first.\n", True)
                on_finished(1)
                return False
            self.is_running = True

        abs_file = os.path.abspath(file_path)
        interpreter = custom_interpreter or InterpreterManager.get_active_interpreter()
        args = list(script_args) if script_args else []

        def _worker():
            work_dir = os.path.dirname(abs_file) or "."
            cmd = [interpreter, "-u", abs_file] + args
            rc = -1

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=work_dir,
                    bufsize=0,
                    start_new_session=True
                )
                with self._lock:
                    self.process = proc

                def _stream_reader(pipe, is_err):
                    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
                    fd = pipe.fileno()
                    try:
                        while True:
                            chunk = os.read(fd, 4096)
                            if not chunk:
                                break
                            text = decoder.decode(chunk, final=False).replace("\x00", "\ufffd")
                            if text:
                                on_output(text, is_err)
                        tail = decoder.decode(b"", final=True).replace("\x00", "\ufffd")
                        if tail:
                            on_output(tail, is_err)
                    except Exception:
                        pass
                    finally:
                        try:
                            pipe.close()
                        except Exception:
                            pass

                t_out = threading.Thread(target=_stream_reader, args=(proc.stdout, False), daemon=True)
                t_err = threading.Thread(target=_stream_reader, args=(proc.stderr, True), daemon=True)

                t_out.start()
                t_err.start()

                t_out.join()
                t_err.join()

                rc = proc.wait()
            except Exception as e:
                on_output(f"\nExecution failed: {e}\n", True)
                rc = -1
            finally:
                with self._lock:
                    if self.process and self.process.stdin:
                        try:
                            self.process.stdin.close()
                        except Exception:
                            pass
                    self.process = None
                    self.is_running = False
                on_finished(rc)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        return True

    def send_input(self, line: str) -> bool:
        """Send a line of text to the running process's stdin."""
        with self._lock:
            proc = self.process
        if not proc or proc.poll() is not None or not proc.stdin:
            return False
        try:
            data = (line + "\n").encode("utf-8", errors="replace")
            proc.stdin.write(data)
            proc.stdin.flush()
            return True
        except Exception:
            return False

    def stop(self):
        """Terminate the active running process group cleanly, escalating to SIGKILL if needed."""
        with self._lock:
            proc = self.process
        if not proc or proc.poll() is not None:
            return

        def _kill_tree(p):
            try:
                pgid = os.getpgid(p.pid)
                os.killpg(pgid, signal.SIGTERM)
            except Exception:
                try:
                    p.terminate()
                except Exception:
                    pass

            for _ in range(15):
                if p.poll() is not None:
                    return
                time.sleep(0.05)

            try:
                pgid = os.getpgid(p.pid)
                os.killpg(pgid, signal.SIGKILL)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        threading.Thread(target=_kill_tree, args=(proc,), daemon=True).start()
