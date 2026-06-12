import asyncio
import builder

async def test():
    print("Testing analyze_project...")
    plan = await builder.analyze_project("A premium health clinic website with booking and testimonials")
    print("PLAN:", plan)

    print("\nTesting generate_project_files...")
    # Force html for quickness
    plan["stack"] = "html"
    files = await builder.generate_project_files(plan, "A premium health clinic website with booking and testimonials")
    print("\nFILES generated:", list(files.keys()))
    
if __name__ == "__main__":
    asyncio.run(test())
