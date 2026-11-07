#!/usr/bin/env python3
"""
RetinaPad - Python Tools Engine
Provides native Python execution, AST syntax verification, and Pylint diagnostics.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import threading
import ast


class Diagnostic:
    """Represents a single linter diagnostic (error, warning, convention, etc.)."""

    def __init__(self, line=1, column=1, severity="convention", code="", message="", symbol=""):
        self.line = max(1, int(line))
        self.column = max(1, int(column))
        self.severity = severity.lower()
        self.code = code or ""
        self.message = message or ""
        self.symbol = symbol or ""

    def __repr__(self):
        return f"<Diagnostic [{self.severity.upper()}] L{self.line}:C{self.column} {self.code}: {self.message}>"


class PythonLinter:
    """Runs Pylint or native AST analysis on Python code."""

    @staticmethod
    def is_pylint_available() -> bool:
        """Check whether pylint is installed and executable in PATH."""
        return shutil.which("pylint") is not None

    @classmethod
    def lint(cls, file_path=None, content=""):
        """
        Runs linting on the given file path or text content.
        Returns (diagnostics_list, status_summary_str, is_pylint_used).
        """
        diagnostics = []
        is_pylint_used = False

        # 1. Native AST syntax check first (ultra-fast)
        ast_errors = cls._check_ast_syntax(content, file_path)
        if ast_errors:
            return ast_errors, "Syntax error detected in Python code.", False

        # 2. If Pylint is available, run comprehensive Pylint analysis
        if cls.is_pylint_available():
            pylint_diags = cls._run_pylint(file_path, content)
            if pylint_diags is not None:
                is_pylint_used = True
                diagnostics.extend(pylint_diags)
                summary = cls._format_summary(diagnostics, pylint_used=True)
                return diagnostics, summary, True

        # 3. Fallback: Syntax OK, notify user how to enable full Pylint
        summary = "Native Python Syntax OK. (Install 'pylint' for deep code inspection)"
        return diagnostics, summary, False

    @staticmethod
    def _check_ast_syntax(content, file_path=None):
        """Perform native Python AST and compile parse to detect syntax mistakes."""
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
        """Execute pylint CLI with JSON output format."""
        temp_file = None
        target_path = file_path

        # If unsaved or unsaved buffer content is provided, write to a temp file
        if not target_path or not os.path.exists(target_path) or content:
            try:
                fd, temp_file = tempfile.mkstemp(prefix="retinapad_lint_", suffix=".py")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
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
            target_path
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                check=False  # Pylint returns bitmask returncodes for warnings/errors
            )
            stdout = proc.stdout.strip()
            if not stdout:
                return []

            raw_data = json.loads(stdout)
            results = []
            for item in raw_data:
                # Severity normalization
                raw_type = item.get("type", "convention").lower()
                severity = "error" if raw_type in ("error", "fatal") else raw_type

                results.append(Diagnostic(
                    line=item.get("line", 1),
                    column=item.get("column", 1),
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
    """Manages asynchronous execution of Python scripts with live output capture."""

    def __init__(self):
        self.process = None
        self._thread = None
        self.is_running = False

    def run(self, file_path, on_output, on_finished):
        """
        Runs the python script in a background thread.
        on_output(text: str, is_stderr: bool)
        on_finished(returncode: int)
        """
        if self.is_running:
            return False

        if not file_path or not os.path.exists(file_path):
            on_output(f"Error: File '{file_path}' does not exist on disk. Save the file first.\n", True)
            on_finished(1)
            return False

        self.is_running = True

        def _worker():
            work_dir = os.path.dirname(os.path.abspath(file_path))
            cmd = [sys.executable, "-u", file_path]

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=work_dir,
                    text=True,
                    bufsize=1
                )

                # Threads to stream stdout and stderr concurrently
                def _stream_reader(stream, is_err):
                    try:
                        for line in iter(stream.readline, ""):
                            on_output(line, is_err)
                    except Exception:
                        pass
                    finally:
                        stream.close()

                t_out = threading.Thread(target=_stream_reader, args=(self.process.stdout, False), daemon=True)
                t_err = threading.Thread(target=_stream_reader, args=(self.process.stderr, True), daemon=True)

                t_out.start()
                t_err.start()

                t_out.join()
                t_err.join()

                rc = self.process.wait()
            except Exception as e:
                on_output(f"\nExecution failed: {e}\n", True)
                rc = -1
            finally:
                self.is_running = False
                self.process = None
                on_finished(rc)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Terminate the active running process."""
        if self.process and self.is_running:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.is_running = False
