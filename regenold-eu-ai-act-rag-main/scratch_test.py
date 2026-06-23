import os

log_path = r"C:\Users\th3un\.gemini\antigravity\brain\0f64dfb9-3e11-40b0-9dcb-21614f8373c0\.system_generated\tasks\task-668.log"

if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for j in range(180, 220):
        print(f"{j+1}: {lines[j].strip()}")
else:
    print("Log file not found.")
