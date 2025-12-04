# compiler_runner.py
"""
Simple compilation & run helper.
WARNING: This is NOT a secure sandbox. Do not run untrusted student code on production hosts.
For production, run student code inside an isolated container or sandbox.
"""

import subprocess, tempfile, os, shutil, stat, time

def compile_c_code(code_text: str, timeout: int = 15) -> dict:
    tmpdir = tempfile.mkdtemp(prefix="autograde_")
    src = os.path.join(tmpdir, "submission.c")
    bin_path = os.path.join(tmpdir, "submission_bin")
    with open(src, "w") as f:
        f.write(code_text)
    try:
        proc = subprocess.run(["gcc", src, "-o", bin_path, "-std=c11", "-Wall", "-O2"],
                              capture_output=True, text=True, timeout=timeout)
        ok = proc.returncode == 0 and os.path.exists(bin_path)
        if ok:
            os.chmod(bin_path, 0o755)
            return {"status": "success", "stdout": proc.stdout, "stderr": proc.stderr, "binary": bin_path, "temp_dir": tmpdir, "returncode": proc.returncode}
        else:
            return {"status": "error", "stdout": proc.stdout, "stderr": proc.stderr, "binary": None, "temp_dir": tmpdir, "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "error", "stdout": "", "stderr": "Compilation timed out", "binary": None, "temp_dir": tmpdir, "returncode": -1}
    except Exception as e:
        return {"status": "error", "stdout": "", "stderr": str(e), "binary": None, "temp_dir": tmpdir, "returncode": -1}

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
        return {"ok": False, "error": str(e)}
