import asyncio
from dotenv import load_dotenv
load_dotenv()
from bot import main
asyncio.run(main())