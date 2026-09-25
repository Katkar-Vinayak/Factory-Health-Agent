import ctypes
import sys
import platform

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ('dwLength', ctypes.c_ulong),
        ('dwMemoryLoad', ctypes.c_ulong),
        ('ullTotalPhys', ctypes.c_ulonglong),
        ('ullAvailPhys', ctypes.c_ulonglong),
        ('ullTotalPageFile', ctypes.c_ulonglong),
        ('ullAvailPageFile', ctypes.c_ulonglong),
        ('ullTotalVirtual', ctypes.c_ulonglong),
        ('ullAvailVirtual', ctypes.c_ulonglong),
        ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
    ]

stat = MEMORYSTATUSEX()
stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))

total_ram_gb = stat.ullTotalPhys / (1024**3)
avail_ram_gb = stat.ullAvailPhys / (1024**3)

print(f"Total RAM: {total_ram_gb:.2f} GB")
print(f"Available RAM: {avail_ram_gb:.2f} GB")
print(f"Python: {sys.version}")

try:
    import torch
    print(f"Torch Version: {torch.__version__}")
    cuda_avail = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_avail}")
    if cuda_avail:
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
        print(f"CUDA VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
except Exception as e:
    print(f"Torch check error: {e}")

try:
    import transformers
    print(f"Transformers Version: {transformers.__version__}")
except Exception as e:
    print(f"Transformers check error: {e}")

try:
    import accelerate
    print(f"Accelerate Version: {accelerate.__version__}")
except Exception as e:
    print(f"Accelerate check error: {e}")

import urllib.request
import json

for repo in ["Qwen/Qwen3-4B", "Qwen/Qwen3-1.7B", "Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-3B-Instruct"]:
    url = f"https://huggingface.co/api/models/{repo}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"{repo}: FOUND")
    except Exception as e:
        print(f"{repo}: NOT FOUND ({e})")

