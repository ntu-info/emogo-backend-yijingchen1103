from typing import Optional, List
from fastapi import FastAPI
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

# ==== 1. 設定 MongoDB 連線 ====

MONGODB_URI = "mongodb+srv://yjchen_db_user:Onv5Qwuw7ATFGuo6@cluster0.qybxanc.mongodb.net/"
DB_NAME = "emogo_data"   # 你在 Compass 裡建立的 database 名稱

app = FastAPI()


@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(MONGODB_URI)
    app.mongodb = app.mongodb_client[DB_NAME]


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()


# ==== 2. 定義資料模型（Pydantic）====

class Vlog(BaseModel):
    user_id: str
    video_title: Optional[str] = None
    video_url: Optional[str] = None   # 影片檔名或 URL，先用文字即可
    note: Optional[str] = None        # 其他想記錄的資訊


class Sentiment(BaseModel):
    user_id: str
    text: str                  # 原始文字
    emotion: str               # 例如 "happy", "sad"
    score: float               # 情緒分數
    created_at: Optional[str] = None  # 時間戳記（字串就好）


class GPS(BaseModel):
    user_id: str
    lat: float
    lon: float
    created_at: Optional[str] = None


# MongoDB 文件轉換 helper：把 _id 轉成字串 id
def to_client_doc(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


# ==== 3. 基本測試用首頁 ====

@app.get("/")
async def root():
    return {"message": "EmoGo backend is running"}


# ==== 4. vlogs API ====

@app.post("/vlogs")
async def create_vlog(vlog: Vlog):
    result = await app.mongodb["vlogs"].insert_one(vlog.dict())
    return {"inserted_id": str(result.inserted_id)}


@app.get("/vlogs")
async def list_vlogs():
    docs = await app.mongodb["vlogs"].find().to_list(1000)
    return [to_client_doc(d) for d in docs]


# ==== 5. sentiments API ====

@app.post("/sentiments")
async def create_sentiment(sent: Sentiment):
    result = await app.mongodb["sentiments"].insert_one(sent.dict())
    return {"inserted_id": str(result.inserted_id)}


@app.get("/sentiments")
async def list_sentiments():
    docs = await app.mongodb["sentiments"].find().to_list(1000)
    return [to_client_doc(d) for d in docs]


# ==== 6. gps API ====

@app.post("/gps")
async def create_gps(gps: GPS):
    result = await app.mongodb["gps"].insert_one(gps.dict())
    return {"inserted_id": str(result.inserted_id)}


@app.get("/gps")
async def list_gps():
    docs = await app.mongodb["gps"].find().to_list(1000)
    return [to_client_doc(d) for d in docs]
