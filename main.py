import os
from typing import Optional

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

# ==== 0. 檔案上傳資料夾設定 ====

UPLOAD_DIR = "videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==== 1. 設定 MongoDB 連線 ====

MONGODB_URI = "mongodb+srv://yjchen_db_user:Onv5Qwuw7ATFGuo6@cluster0.qybxanc.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "emogo_data"

app = FastAPI()

# 讓 /videos/ 底下的檔案可以被直接下載
app.mount("/videos", StaticFiles(directory=UPLOAD_DIR), name="videos")


@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(MONGODB_URI)
    app.mongodb = app.mongodb_client[DB_NAME]


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()


# ==== 2. 定義資料模型 ====


class Vlog(BaseModel):
    user_id: str
    video_title: Optional[str] = None
    video_url: Optional[str] = None   # e.g. "/videos/xxx.mp4"
    note: Optional[str] = None


class Sentiment(BaseModel):
    user_id: str
    text: str
    emotion: str
    score: float
    created_at: Optional[str] = None


class GPS(BaseModel):
    user_id: str
    lat: float
    lon: float
    created_at: Optional[str] = None


def to_client_doc(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


# ==== 3. 基本測試首頁 ====


@app.get("/")
async def root():
    return {"message": "EmoGo backend is running"}


# ==== 4. vlogs JSON API (保留原本的) ====


@app.post("/vlogs")
async def create_vlog(vlog: Vlog):
    result = await app.mongodb["vlogs"].insert_one(vlog.dict())
    return {"inserted_id": str(result.inserted_id)}


@app.get("/vlogs")
async def list_vlogs():
    docs = await app.mongodb["vlogs"].find().to_list(1000)
    return [to_client_doc(d) for d in docs]


# ==== 5. sentiments JSON API ====


@app.post("/sentiments")
async def create_sentiment(sent: Sentiment):
    result = await app.mongodb["sentiments"].insert_one(sent.dict())
    return {"inserted_id": str(result.inserted_id)}


@app.get("/sentiments")
async def list_sentiments():
    docs = await app.mongodb["sentiments"].find().to_list(1000)
    return [to_client_doc(d) for d in docs]


# ==== 6. gps JSON API ====


@app.post("/gps")
async def create_gps(gps: GPS):
    result = await app.mongodb["gps"].insert_one(gps.dict())
    return {"inserted_id": str(result.inserted_id)}


@app.get("/gps")
async def list_gps():
    docs = await app.mongodb["gps"].find().to_list(1000)
    return [to_client_doc(d) for d in docs]


# ==== 7. 新增：影片上傳 API ====

@app.post("/upload-video")
async def upload_video(
    user_id: str,
    video_title: Optional[str] = None,
    note: Optional[str] = None,
    file: UploadFile = File(...)
):
    # 1. 把檔案存到 videos/ 資料夾
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 2. 在 MongoDB 的 vlogs collection 新增一筆 metadata
    video_url = f"/videos/{file.filename}"  # 之後下載就是這個 URL
    vlog_doc = {
        "user_id": user_id,
        "video_title": video_title or file.filename,
        "video_url": video_url,
        "note": note,
    }
    result = await app.mongodb["vlogs"].insert_one(vlog_doc)

    return {
        "message": "video uploaded",
        "inserted_id": str(result.inserted_id),
        "download_url": video_url,
    }


# ==== 8. 新增：export-data HTML 頁面 ====

@app.get("/export-data", response_class=HTMLResponse)
async def export_data():
    vlogs = await app.mongodb["vlogs"].find().to_list(1000)

    items_html = ""
    for vlog in vlogs:
        file_url = vlog.get("video_url")
        title = vlog.get("video_title") or file_url
        if file_url:
            items_html += f'<li><a href="{file_url}" download>{title}</a></li>\n'

    html = f"""
    <html>
      <head>
        <title>EmoGo Export Data</title>
      </head>
      <body>
        <h1>EmoGo Video Export</h1>
        <p>Click the links below to download uploaded videos.</p>
        <ul>
          {items_html or "<li>No videos uploaded yet.</li>"}
        </ul>
        <hr>
        <p>Raw JSON endpoints:</p>
        <ul>
          <li><a href="/vlogs">/vlogs</a></li>
          <li><a href="/sentiments">/sentiments</a></li>
          <li><a href="/gps">/gps</a></li>
        </ul>
      </body>
    </html>
    """
    return html
