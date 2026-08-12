from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import datetime
import os

app = FastAPI(title="SMK Gym Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database for demo
contacts = []

@app.post("/api/contact")
async def handle_contact(request: Request):
    data = await request.json()
    new_entry = {
        "id": len(contacts) + 1,
        "name": data.get("name"),
        "email": data.get("email"),
        "message": data.get("message"),
        "timestamp": datetime.datetime.now().isoformat()
    }
    contacts.append(new_entry)
    print(f"New Lead: {new_entry['name']} - {new_entry['email']}")
    return {"status": "success", "message": "Thanks for reaching out! SMK Gym team will contact you shortly."}

@app.post("/api/bmi")
async def calculate_bmi(request: Request):
    data = await request.json()
    height_cm = float(data.get("height", 0))
    weight_kg = float(data.get("weight", 0))
    
    if height_cm == 0:
        return {"error": "Invalid height"}
        
    height_m = height_cm / 100
    bmi = weight_kg / (height_m * height_m)
    
    category = "Normal"
    if bmi < 18.5: category = "Underweight"
    elif bmi >= 25 and bmi < 30: category = "Overweight"
    elif bmi >= 30: category = "Obese"
        
    return {
        "status": "success",
        "bmi": round(bmi, 2),
        "category": category,
        "message": f"Your BMI is {round(bmi, 2)} ({category}). Join SMK Gym to transform your body!"
    }

if __name__ == "__main__":
    print("Starting SMK Gym Backend on port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
