import g4f

try:
    response = g4f.ChatCompletion.create(
        model=g4f.models.gpt_4o,
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("SUCCESS: ", response)
except Exception as e:
    print("ERROR: ", e)
