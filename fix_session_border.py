import sys

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

old_stat_frame_code = '''            # Stats Card
            stat_frame = QFrame()
            stat_frame.setStyleSheet("background: white; border: 1px solid #22c55e; border-radius: 8px;")'''

new_stat_frame_code = '''            # Stats Card
            stat_frame = QFrame()
            stat_frame.setObjectName("stat_frame")
            stat_frame.setStyleSheet("QFrame#stat_frame { background: white; border: 1px solid #22c55e; border-radius: 8px; }")'''

if old_stat_frame_code in content:
    content = content.replace(old_stat_frame_code, new_stat_frame_code)
    with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed border issue successfully.")
else:
    print("Could not find the target code block.")
