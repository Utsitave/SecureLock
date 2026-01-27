import sys
import asyncio

if sys.platform.lower().startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8011,
        env_file=r"C:\Users\Madziaaa\Desktop\ARIUS\apkadodrzwi\SecureLock\backend\.env",
        loop="asyncio",
        reload=False,
    )