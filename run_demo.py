import asyncio
from veriform.orchestrator.orchestrator import run_single_page

async def main():
    target_url = "https://myaccount.bajajhousingfinance.in/#/tracker/tracker-home"
    print(f"Running VeriForm against {target_url} ...")
    result = await run_single_page(target_url)
    print("Execution Finished!")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
