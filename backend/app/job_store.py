import json, time, uuid
from .redis_client import client

def create_job(url:str,page_limit:int,user_id:str)->str:
    job_id=str(uuid.uuid4())
    client.hset(f"webforge:job:{job_id}",mapping={"status":"queued","url":url,"page_limit":str(page_limit),"user_id":user_id,"created_at":str(time.time())})
    client.expire(f"webforge:job:{job_id}",86400)
    return job_id

def update_job(job_id:str,status:str,result=None,error=""):
    mapping={"status":status,"updated_at":str(time.time())}
    if result is not None: mapping["result"]=json.dumps(result)
    if error: mapping["error"]=error
    client.hset(f"webforge:job:{job_id}",mapping=mapping)

def get_job(job_id:str,user_id:str):
    value=client.hgetall(f"webforge:job:{job_id}")
    if not value or value.get("user_id") != user_id:return None
    if value.get("result"):
        try:value["result"]=json.loads(value["result"])
        except json.JSONDecodeError:value["result"]=None
    return value
