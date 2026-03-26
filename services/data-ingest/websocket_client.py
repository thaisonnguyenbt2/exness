import os
import json
import asyncio
import websockets
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class FinnhubWSClient:
    def __init__(self, symbol="OANDA:XAU_USD", callback: Callable = None, error_callback: Callable = None):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY environment variable is not set")
            
        self.url = f"wss://ws.finnhub.io?token={self.api_key}"
        self.symbol = symbol
        self.callback = callback
        self.error_callback = error_callback
        self.ws = None
        self.is_running = False

    async def connect(self):
        self.is_running = True
        
        while self.is_running:
            try:
                logger.info(f"Connecting to Finnhub WS for {self.symbol}")
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
                    
                    # Subscribe
                    subscribe_msg = {"type": "subscribe", "symbol": self.symbol}
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info(f"Subscribed to {self.symbol}")
                    
                    # Listen for messages
                    async for message in ws:
                        if not self.is_running:
                            break
                            
                        data = json.loads(message)
                        if data.get("type") == "trade":
                            for trade in data["data"]:
                                if self.callback:
                                    # Finnhub trade -> p: price, v: volume, t: timestamp (ms)
                                    await self.callback(trade['p'], trade['v'], trade['t'])
                        elif data.get("type") == "ping":
                            pass # Finnhub ping

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Finnhub WS connection closed, trying to reconnect...")
            except Exception as e:
                logger.error(f"Finnhub WS error: {e}")
                if self.error_callback:
                    await self.error_callback(e)
            
            if self.is_running:
                await asyncio.sleep(5) # Delay before reconnect
                
    async def stop(self):
        self.is_running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info("Finnhub WS stopped")
