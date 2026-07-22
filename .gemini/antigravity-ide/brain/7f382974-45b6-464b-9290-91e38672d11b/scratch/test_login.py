import asyncio
import traceback
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("http://127.0.0.1:8043/auth/login", json={"email": "test@gmail.com"})
            print("STATUS:", res.status_code)
            print("RESPONSE:", res.text)
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
