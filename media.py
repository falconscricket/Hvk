import os
import json
import aiofiles
from config import MEDIA_ASSETS_PATH

class MediaManager:
    def __init__(self, path: str = MEDIA_ASSETS_PATH):
        self.path = path
        self.assets: dict[str, str] = {}

    async def load_assets(self):
        if os.path.exists(self.path):
            async with aiofiles.open(self.path, mode='r') as f:
                content = await f.read()
                if content:
                    self.assets = json.loads(content)

    async def set_media(self, event_key: str, file_id: str):
        self.assets[event_key.upper()] = file_id
        async with aiofiles.open(self.path, mode='w') as f:
            await f.write(json.dumps(self.assets, indent=4))

    def get_media(self, event_key: str) -> str | None:
        return self.assets.get(event_key.upper())

media_manager = MediaManager()
