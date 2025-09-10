# services/shared/http_client.py
import httpx

http_client = httpx.AsyncClient(timeout=5)