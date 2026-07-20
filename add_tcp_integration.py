import sys

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

# 1. Define HardwareSignals and import run_rfid_server_in_thread
HARDWARE_IMPORTS = """from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.hardware.rfid_tcp import run_rfid_server_in_thread
from PySide6.QtCore import QObject, Signal

class HardwareSignals(QObject):
    rfid_scanned = Signal(str, str)  # ip_address, rfid_code

global_hw_signals = HardwareSignals()
"""
if "global_hw_signals = HardwareSignals()" not in content:
    content = content.replace(
        "from pmql.infrastructure.hardware.mock_hardware import MockBarrierController",
        HARDWARE_IMPORTS
    )

# 2. Start TCP server in launch()
TCP_START_CODE = """        _HAS_QTA = False

    # Start background TCP Server for RFID
    def on_rfid_read(ip, rfid_code):
        global_hw_signals.rfid_scanned.emit(ip, rfid_code)
    
    # Run on default port 9001 (can be taken from settings in the future)
    run_rfid_server_in_thread(9001, on_rfid_read)
"""
if "run_rfid_server_in_thread(" not in content:
    content = content.replace(
        "        _HAS_QTA = False",
        TCP_START_CODE
    )

# 3. Hook the signal in operations_page
HOOK_CODE = """            box.addLayout(sub_toolbar)
            
            # --- TCP RFID Hook ---
            def handle_rfid_scan(ip_addr: str, rfid_code: str):
                # Put the RFID code into the first lane's UID input
                for i in range(grid.count()):
                    item = grid.itemAt(i)
                    if item and item.widget():
                        w = item.widget()
                        # Find the first QLineEdit with placeholder "Ma the (UID)"
                        from PySide6.QtWidgets import QLineEdit
                        for le in w.findChildren(QLineEdit):
                            if "UID" in le.placeholderText():
                                le.setText(rfid_code)
                                # Automatically click the "Vao" or "Ra" button depending on direction?
                                # For MVP, we just fill the text and let operator click, or 
                                # trigger entry automatically if it's IN lane, exit if OUT lane.
                                # Let's just fill it for now.
                                return
                                
            # Connect the signal
            global_hw_signals.rfid_scanned.connect(handle_rfid_scan)
"""

if "# --- TCP RFID Hook ---" not in content:
    content = content.replace(
        "            box.addLayout(sub_toolbar)",
        HOOK_CODE
    )

with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("TCP integration added to app.py")
