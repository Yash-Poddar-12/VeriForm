import asyncio
import logging
import uuid
from pathlib import Path
from playwright.async_api import async_playwright
from veriform.orchestrator.pipeline import PipelineOrchestrator
from veriform.schemas.mutations import MutationProfile

# Disable noisy logs
logging.getLogger("veriform").setLevel(logging.WARNING)

async def main():
    target_url = "https://myaccount.bajajhousingfinance.in/#/tracker/tracker-home"
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    output_dir = Path("reports")
    
    print("==================================================")
    print("VeriForm Discovery Run")
    print("==================================================")
    print()
    print(f"Target:")
    print(f"{target_url}")
    print()
    print("Launching Browser and Extracting Contracts...")
    print("Please wait while probes execute...\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        orchestrator = PipelineOrchestrator(
            page=page,
            run_id=run_id,
            profile=MutationProfile.LIGHTWEIGHT
        )
        
        artifact = await orchestrator.run(target_url, output_dir)
        await browser.close()

    high_conf = sum(1 for f in artifact.validation_contract.fields if f.synthesized_regex and f.synthesized_regex.confidence >= 0.8)
    
    print(f"Detected Fields: {artifact.metrics.total_fields}")
    print(f"Contracts Synthesized: {artifact.metrics.processed_fields}")
    print(f"High Confidence Fields: {high_conf}")
    print()
    print("Artifacts Generated:")
    print("  * report.html")
    print("  * inferred_schema.json")
    print("  * openapi.json")
    print("  * validation_contract.json")
    print("  * raw_probe_results.json")
    print()
    print("Output Folder:")
    print(f"reports/{run_id}/")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
