import os
from fastapi import UploadFile, HTTPException
import aiofiles
import aiohttp
import logging

logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        os.makedirs(self.base_directory, exist_ok=True)

    async def save_file(self, file: UploadFile, file_path: str) -> None:
        try:
            full_path = os.path.join(self.base_directory, file_path)
            directory = os.path.dirname(full_path)
            os.makedirs(directory, exist_ok=True)

            async with aiofiles.open(full_path, 'wb') as out_file:
                while content := await file.read(1024):
                    await out_file.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    async def get_file(self, container_id: str, file_name: str) -> bytes:
        logger.info(f"Attempting to get file: container_id={container_id}, file_name={file_name}")

        user_directory = os.path.join(self.base_directory)
        file_base_name = os.path.splitext(file_name)[0]
        full_path = os.path.join(user_directory, f"{file_base_name}_analysis.txt")

        logger.debug(f"Full file path: {full_path}")


        if not os.path.exists(full_path):
            logger.warning(f"File not found: {full_path}")
            raise HTTPException(status_code=404, detail="File not found")

        try:
            logger.debug(f"Opening file: {full_path}")
            async with aiofiles.open(full_path, 'rb') as file:
                logger.debug(f"Reading file: {full_path}")
                return await file.read()
        except Exception as e:
            logger.error(f"Error reading file: {full_path}, {str(e)}")
            raise HTTPException(status_code=500, detail=f"Could not read file: {str(e)}")



FILE_MANAGER = FileManager(base_directory="static/containers")