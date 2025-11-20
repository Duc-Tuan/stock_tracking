from fastapi import Response
import requests
from src.utils.options import TOKEN_VPS, API_VPS

headers={"token": TOKEN_VPS}

def getVps(url: str, params):
    res = requests.get(f"{API_VPS}/{url}", params=params, headers=headers)
    return res.json()

def postVps(url: str, payload):
    res = requests.post(f"{API_VPS}/{url}", json=payload, headers=headers)
    return res.json()