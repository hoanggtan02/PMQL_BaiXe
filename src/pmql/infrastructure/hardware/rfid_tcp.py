import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class RfidTcpServer:
    def __init__(self, port: int, on_rfid_read: Callable[[str, str], None]):
        """
        port: TCP port to listen on
        on_rfid_read: Callback function receiving (ip_address, rfid_code)
        """
        self.port = port
        self.on_rfid_read = on_rfid_read
        self.server = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        ip_addr = addr[0] if addr else "unknown"
        logger.info(f"RFID reader connected from {addr}")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                
                rfid_code = data.decode('utf-8', errors='ignore').strip()
                if rfid_code:
                    logger.info(f"RFID read from {ip_addr}: {rfid_code}")
                    # Notify the main thread via callback
                    try:
                        self.on_rfid_read(ip_addr, rfid_code)
                    except Exception as e:
                        logger.error(f"Error in RFID callback: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"RFID connection error from {addr}: {e}")
        finally:
            logger.info(f"RFID reader disconnected from {addr}")
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        try:
            self.server = await asyncio.start_server(self.handle_client, '0.0.0.0', self.port)
            addrs = ', '.join(str(sock.getsockname()) for sock in self.server.sockets)
            logger.info(f"RFID TCP Server listening on {addrs}")
        except OSError as e:
            logger.error(f"Cannot start RFID TCP Server: {e}")
            self.server = None

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("RFID TCP Server stopped")

def run_rfid_server_in_thread(port: int, on_rfid_read: Callable[[str, str], None]):
    """
    Runs the asyncio TCP server in a background thread.
    Useful for integrating with synchronous frameworks like PySide6.
    """
    import threading

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        server = RfidTcpServer(port, on_rfid_read)
        
        # Start server
        loop.create_task(server.start())
        
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(server.stop())
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="RFIDTcpThread")
    thread.start()
    return thread
