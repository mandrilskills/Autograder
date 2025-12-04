# compiler_runner.py
import subprocess, tempfile, os, time

def compile_c_code(code_text: str, timeout=15) -> dict:
    temp_dir = tempfile.mkdtemp(prefix="autograde_")
    src = os.path.join(temp_dir, "submission.c")
    bin_path = os.path.join(temp_dir, "submission_bin")

    with open(src, "w") as f:
        f.write(code_text)

    try:
        proc = subprocess.run(
            ["gcc", src, "-o", bin_path, "-std=c11", "-O2", "-Wall"],
            text=True,
            capture_output=True,
            timeout=timeout
        )
        ok = proc.returncode == 0
        return {
            "status": "success" if ok else "error",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "binary": bin_path if ok else None,
            "temp_dir": temp_dir,
            "returncode": proc.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "stderr": "Compilation timeout", "binary": None, "temp_dir": temp_dir}
    except Exception as e:
        return {"status": "error", "stderr": str(e), "binary": None, "temp_dir": temp_dir}


def run_binary(binary_path: str, input_data="", timeout=3) -> dict:
    try:
        start = time.time()
        proc = subprocess.run(
            [binary_path],
            input=input_data.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        return {
            "ok": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout.decode(),
            "stderr": proc.stderr.decode(),
            "time": time.time() - start
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
