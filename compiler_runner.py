# compiler_runner.py
"""
Compile and run C programs. NOTE: not a secure sandbox.
For production, execute student binaries in isolated containers.
"""

import subprocess
import tempfile
import os
import time
import shutil
import logging

logger = logging.getLogger(__name__)


def compile_c_code(code_text: str, timeout: int = 15) -> dict:
    tmpdir = tempfile.mkdtemp(prefix="autograde_")
    src = os.path.join(tmpdir, "submission.c")
    bin_path = os.path.join(tmpdir, "submission_bin")
    with open(src, "w") as f:
        f.write(code_text)
    try:
        proc = subprocess.run(
            ["gcc", src, "-o", bin_path, "-std=c11", "-O2", "-Wall"],
            capture_output=True, text=True, cwd=tmpdir, timeout=timeout
        )
        ok = proc.returncode == 0 and os.path.exists(bin_path)
        return {
            "status": "success" if ok else "error",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "binary": bin_path if ok else None,
            "temp_dir": tmpdir,
            "returncode": proc.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "stderr": "Compilation timed out", "binary": None, "temp_dir": tmpdir, "returncode": -1}
    except Exception as e:
        logger.exception("Compilation exception")
        # cleanup on exception
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass
        return {"status": "error", "stderr": str(e), "binary": None, "temp_dir": None, "returncode": -1}


def run_binary(binary_path: str, input_data: str = "", timeout: int = 3) -> dict:
    if not binary_path or not os.path.exists(binary_path):
        return {"ok": False, "error": "binary missing"}
    try:
        start = time.time()
        proc = subprocess.run([binary_path], input=input_data.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        elapsed = time.time() - start
        return {"ok": True, "returncode": proc.returncode, "stdout": proc.stdout.decode(errors="ignore"), "stderr": proc.stderr.decode(errors="ignore"), "time": elapsed}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "execution timed out"}
    except Exception as e:
        logger.exception("run_binary exception")
        return {"ok": False, "error": str(e)}
