import os
from io import BytesIO
from PIL import Image
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
from rembg import remove
from PIL import Image

app = FastAPI()

class DownloadImageRequest(BaseModel):
    img_url: str

class ChangeBackgroundRequest(BaseModel):
    foreground_img: UploadFile
    background_img: UploadFile

def download_image(img_url):
    response = requests.get(img_url)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Image could not be downloaded")
    img = Image.open(BytesIO(response.content))
    return img

def save_image(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if img.mode == 'RGBA':
        img = img.convert('RGB')
        path = os.path.splittext(path)[0] + '.png'
    img.save(path)

def remove_background(img, alpha_matting=True, alpha_matting_foreground_threshold=50):
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    subject = remove(img_byte_arr,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=alpha_matting_foreground_threshold)
    img_no_bg = Image.open(BytesIO(subject))
    img_no_bg = img_no_bg.convert('RGB')
    img_byte_arr = BytesIO()
    img_no_bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return StreamingResponse(img_byte_arr, media_type='image/png')


def change_background(foreground_img, background_img):
    # Remove background from the foreground image
    img_byte_arr = BytesIO()
    foreground_img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    subject = remove(img_byte_arr)
    foreground_no_bg = Image.open(BytesIO(subject))

    # Resize background to match the foreground size
    background_img = background_img.resize(foreground_no_bg.size)

    # Combine images
    combined = Image.alpha_composite(background_img.convert('RGBA'), foreground_no_bg)

    img_byte_arr = BytesIO()
    combined.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

@app.post("/download_image/")
async def api_download_image(request: DownloadImageRequest):
	img = download_image(request.img_url)
	img_byte_arr = BytesIO()
	img.save(img_byte_arr, format='PNG')
	img_byte_arr.seek(0)
	return StreamingResponse(img_byte_arr, media_type="image/png")
@app.post("/save_image/")
async def api_save_image(file: UploadFile, path: str):
	img = Image.open(file.file)
	save_image(img, path)
	return {"detail": "Image saved successfully."}

@app.post("/remove_background/")
async def api_remove_background(file: UploadFile):
	img = Image.open(file.file)
	return remove_background(img)

@app.post("/change_background/")
async def api_change_background(foreground_img: UploadFile = File(...), background_img: UploadFile = File(...)):
    foreground_img = Image.open(foreground_img.file)
    background_img = Image.open(background_img.file)
    img_byte_arr = change_background(foreground_img, background_img)
    return StreamingResponse(img_byte_arr, media_type="image/jpeg")

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)