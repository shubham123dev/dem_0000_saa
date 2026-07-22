import asyncio
import traceback
from app.adapters.user.provider import get_user_directory

async def test():
    try:
        directory = get_user_directory()
        print("Directory type:", type(directory))
        user = await directory.get_by_email("test@gmail.com")
        print("User result:", user)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
