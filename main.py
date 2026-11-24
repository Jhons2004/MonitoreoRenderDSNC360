import os, secrets, asyncio, json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from pathlib import Path
security=HTTPBasic()
def auth(c:HTTPBasicCredentials=Depends(security)):
    password=os.getenv("ADMIN_PASSWORD","")
    if not password or not secrets.compare_digest(c.username.encode(),b"admin") or not secrets.compare_digest(c.password.encode(),password.encode()):
        raise HTTPException(401,"Unauthorized",headers={"WWW-Authenticate":"Basic"})
async def get(client,url,key,params=None):
    r=await client.get(url,headers={"Authorization":"Bearer "+key},params=params)
    r.raise_for_status()
    return r.json()
async def render(client,i):
    key=os.getenv(f"RENDER_{i}_API_KEY")
    row={"provider":"Render","account":i,"status":"not_configured","resources":[]}
    if not key:return row
    try:
        owners=await get(client,"https://api.render.com/v1/owners",key,{"limit":100})
        owner_ids=[o["owner"]["id"] for o in owners]
        expected=os.getenv(f"RENDER_{i}_WORKSPACE_ID")
        if expected not in owner_ids:raise ValueError("Workspace not authorized")
        cursor=None
        seen=set()
        while True:
            params={"ownerId":expected,"limit":100}
            if cursor:params["cursor"]=cursor
            page=await get(client,"https://api.render.com/v1/services",key,params)
            for item in page:
                s=item["service"]
                row["resources"].append({"name":s["name"],"state":s.get("suspended"),"reason":s.get("suspenders",[]),"plan":s.get("serviceDetails",{}).get("plan")})
            if len(page)<100:break
            cursor=page[-1].get("cursor")
            if not cursor or cursor in seen:raise ValueError("Pagination incomplete")
            seen.add(cursor)
        row["status"]="connected"
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        row["status"]="error"
    return row
async def neon(client,i):
    key=os.getenv(f"NEON_{i}_API_KEY")
    org=os.getenv(f"NEON_{i}_ORG_ID")
    row={"provider":"Neon","account":i,"status":"not_configured","resources":[]}
    if not key or not org:return row
    try:
        cursor=None
        seen=set()
        while True:
            params={"org_id":org,"limit":100}
            if cursor:params["cursor"]=cursor
            page=await get(client,"https://console.neon.tech/api/v2/projects",key,params)
            for p in page["projects"]:
                row["resources"].append({"name":p["name"],"active_seconds":p.get("active_time"),"compute_seconds":p.get("compute_time_seconds"),"storage_bytes":p.get("synthetic_storage_size"),"transfer_bytes":p.get("data_transfer_bytes"),"reset_at":p.get("quota_reset_at")})
            cursor=page.get("pagination",{}).get("cursor")
            if not cursor:break
            if cursor in seen:raise ValueError("Pagination incomplete")
            seen.add(cursor)
        row["status"]="connected"
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        row["status"]="error"
    return row
cache={"collected_at":None,"accounts":[]}
lock=asyncio.Lock()
async def collect():
    async with lock:
        async with httpx.AsyncClient(timeout=20) as client:
            rows=await asyncio.gather(*(render(client,i) for i in range(1,5)),*(neon(client,i) for i in range(1,5)))
        cache.update(collected_at=datetime.now(timezone.utc).isoformat(),accounts=rows)
        return cache
async def loop():
    while True:
        try:await collect()
        except Exception:pass
        await asyncio.sleep(300)
@asynccontextmanager
async def lifespan(app):
    task=asyncio.create_task(loop())
    yield
    task.cancel()
    await asyncio.gather(task,return_exceptions=True)
app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
@app.get("/healthz")
def health():return {"status":"ok"}
@app.get("/api/monitor")
async def monitor(_=Depends(auth)):return cache
@app.get("/",response_class=HTMLResponse)
def dashboard(_=Depends(auth)):return Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
