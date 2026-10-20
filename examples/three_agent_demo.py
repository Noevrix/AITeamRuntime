import asyncio
from pathlib import Path
from ai_team.cli import run_demo
from ai_team.protocol.task import uid

if __name__ == "__main__":
    print(asyncio.run(run_demo(Path("runs") / uid(), "mock")))
