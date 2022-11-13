from typing import List, BinaryIO

import aiohttp
from PIL import Image
from fastapi import UploadFile, HTTPException


def check_image_is_in_formats(image_file: BinaryIO, formats: List[str]):
    image = Image.open(image_file)
    return image.format.lower() in formats


async def upload_binary_file_to_imgur(file: UploadFile, imgur_client_id: str):
    headers = {"Authorization": f"Client-ID {imgur_client_id}"}
    await file.seek(0)
    contents = await file.read()
    data = {"image": contents,
            "type": "file"}
    async with aiohttp.ClientSession(headers=headers) as sess:
        async with sess.post("https://api.imgur.com/3/upload", data=data) as resp:
            response = await resp.json()
    if response["status"] != 200:
        raise HTTPException(response["status"])
    return response["data"]
