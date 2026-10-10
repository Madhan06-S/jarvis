import asyncio
import ai_brain

async def test():
    try:
        print("Calling Gemini...")
        res = await ai_brain.call_ai("You are a helpful assistant.", "Say 'Gemini is fully operational!'", provider="gemini")
        print("RESULT:", res)
    except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()

asyncio.run(test())
