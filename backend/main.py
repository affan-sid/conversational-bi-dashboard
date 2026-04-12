from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Conversational BI API running"}