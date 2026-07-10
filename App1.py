from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import pandas as pd
import numpy as np
import joblib
import math

from io import StringIO
from typing import List
from pydantic import BaseModel, Field


app = FastAPI(
    title="SwiftPrime Premium Customer Identification",
    version="1.0"
)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

MODEL_PATH = "xgboost_swiftprime_model.pkl"
ENCODER_PATH = "label_encoders.pkl"

try:
    model = joblib.load(MODEL_PATH)
    label_encoders = joblib.load(ENCODER_PATH)
    print("Model Loaded Successfully")
except Exception as e:
    model = None
    label_encoders = None
    print(e)


CATEGORICAL_COLS = [
    "Workclass",
    "Education",
    "Marital status",
    "Occupation",
    "Relationship",
    "Race",
    "Sex",
    "Native-country",
    "Age Group",
    "education_group"
]

NUMERIC_COLS = [
    "Age",
    "Education-num",
    "Capital-gain",
    "Capital-loss",
    "Hours-per-week",
    "capital_net",
    "has_capital_activity",
    "log_capital_gain",
    "log_capital_loss",
    "is_married",
    "high_skill_occ",
    "is_self_employed"
]



class CustomerInput(BaseModel):
    Age: int
    Workclass: str
    Education: str

    Education_num: int = Field(alias="Education-num")

    Marital_status: str = Field(alias="Marital status")

    Occupation: str

    Relationship: str

    Race: str

    Sex: str

    Capital_gain: int = Field(alias="Capital-gain")

    Capital_loss: int = Field(alias="Capital-loss")

    Hours_per_week: int = Field(alias="Hours-per-week")

    Native_country: str = Field(alias="Native-country")

    class ConfigDict:
        populate_by_name = True
        
class BatchInput(BaseModel):
    customers: List[CustomerInput]




def handle_missing_values(row):

    # Replace '?' with NaN
    for key, value in row.items():
        if isinstance(value, str) and value.strip() == "?":
            row[key] = np.nan

    # Fill with training-time modes
    if pd.isna(row["Workclass"]):
        row["Workclass"] = "Private"

    if pd.isna(row["Occupation"]):
        row["Occupation"] = "Prof-specialty"

    if pd.isna(row["Native-country"]):
        row["Native-country"] = "United-States"

    return row

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request
        }
    )



def engineer_features(row: dict) -> dict:
    # Convert numeric values
    row["Age"] = int(row["Age"])
    row["Education-num"] = int(row["Education-num"])
    row["Capital-gain"] = int(row["Capital-gain"])
    row["Capital-loss"] = int(row["Capital-loss"])
    row["Hours-per-week"] = int(row["Hours-per-week"])

    row["capital_net"] = row["Capital-gain"] - row["Capital-loss"]
    row["has_capital_activity"] = int(
        row["Capital-gain"] > 0 or row["Capital-loss"] > 0
    )

    row["log_capital_gain"] = np.log1p(row["Capital-gain"])
    row["log_capital_loss"] = np.log1p(row["Capital-loss"])

    row["is_married"] = int(
        row["Marital status"] == "Married-civ-spouse"
    )

    age = row["Age"]

    if age < 25:
        row["Age Group"] = "<25"
    elif age < 35:
        row["Age Group"] = "25-35"
    elif age < 45:
        row["Age Group"] = "35-45"
    elif age < 55:
        row["Age Group"] = "45-55"
    else:
        row["Age Group"] = "55+"

    edu_map = {
        "Preschool": "Dropout",
        "1st-4th": "Dropout",
        "5th-6th": "Dropout",
        "7th-8th": "Dropout",
        "9th": "Dropout",
        "10th": "Dropout",
        "11th": "Dropout",
        "12th": "Dropout",
        "HS-grad": "HS-grad",
        "Some-college": "Some-college",
        "Assoc-voc": "Some-college",
        "Assoc-acdm": "Some-college",
        "Bachelors": "Graduate",
        "Masters": "Post-grad",
        "Prof-school": "Post-grad",
        "Doctorate": "Post-grad",
    }

    row["education_group"] = edu_map.get(
        row["Education"],
        "Other"
    )

    high_skill = [
        "Exec-managerial",
        "Prof-specialty",
        "Tech-support",
        "Protective-serv",
    ]

    row["high_skill_occ"] = int(
        row["Occupation"] in high_skill
    )

    row["is_self_employed"] = int(
        row["Workclass"] in ["Self-emp-inc", "Self-emp-not-inc"]
    )


    return row

def prepare_features(customer_dict: dict):

    row = handle_missing_values(customer_dict.copy())
    row = engineer_features(row)

    features = []

    # Numeric Features
    for col in NUMERIC_COLS:
        features.append(row[col])

    # Encoded categorical features
    for col in CATEGORICAL_COLS:

        value = str(row[col]).strip()

        encoder = label_encoders[col]

        try:
            encoded = encoder.transform([value])[0]
        except ValueError:
            encoded = 0

        features.append(encoded)

    return np.array(features, dtype=float).reshape(1, -1)


def assign_tier(prob):
    if prob >= 0.85:
        return "Diamond"
    elif prob >= 0.70:
        return "Platinum"
    elif prob >= 0.50:
        return "Gold"
    elif prob >= 0.30:
        return "Silver"
    else:
        return "Standard"


@app.post("/predict")
async def predict(customer: CustomerInput):

    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    customer_dict = customer.dict(by_alias=True)
    customer_dict = handle_missing_values(customer_dict)

    X = prepare_features(customer_dict)

    probability = float(model.predict_proba(X)[0][1])

    prediction = ">50K" if probability >= 0.5 else "<=50K"

    tier = assign_tier(probability)

    return {
        "prediction": prediction,
        "probability": round(probability,4),
        "priority_tier": tier,
        "recommended": probability >= 0.5
    }


@app.post("/predict/batch")
async def batch_predict(batch: BatchInput):

    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    results=[]

    for customer in batch.customers:
        
        customer_dict = customer.dict(by_alias=True)
        customer_dict = handle_missing_values(customer_dict)

        X=prepare_features(customer_dict)

        probability=float(model.predict_proba(X)[0][1])

        prediction=">50K" if probability>=0.5 else "<=50K"

        results.append({

            "Age":customer.Age,

            "Occupation":customer_dict["Occupation"],

            "Prediction":prediction,

            "Probability":probability,

            "Priority Tier":assign_tier(probability)

        })

    results=sorted(results,key=lambda x:x["Probability"],reverse=True)

    top20=max(1,math.ceil(len(results)*0.20))

    for i,row in enumerate(results):

        row["Rank"]=i+1

        row["Recommended"]="YES" if i<top20 else "NO"

        row["Probability"]=round(row["Probability"],4)

    return{

        "Total Customers":len(results),

        "Top20 Recommended":top20,

        "Predictions":results

    }




@app.post("/predict/csv")
async def csv_predict(file:UploadFile=File(...)):

    if model is None:
        raise HTTPException(status_code=500,detail="Model not loaded")

    if not file.filename.endswith(".csv"):

        raise HTTPException(
            status_code=400,
            detail="Upload CSV file only."
        )

    df=pd.read_csv(file.file)
    df.replace("?", np.nan, inplace=True)

    df["Workclass"] = df["Workclass"].fillna("Private")
    df["Occupation"] = df["Occupation"].fillna("Prof-specialty")
    df["Native-country"] = df["Native-country"].fillna("United-States")

    probs=[]
    preds=[]
    tiers=[]

    for _,row in df.iterrows():

        customer=row.to_dict()

        X=prepare_features(customer)

        probability=float(model.predict_proba(X)[0][1])

        prediction=">50K" if probability>=0.5 else "<=50K"

        probs.append(probability)

        preds.append(prediction)

        tiers.append(assign_tier(probability))

    df["Probability"]=probs

    df["Prediction"]=preds

    df["Priority Tier"]=tiers

    df=df.sort_values(
        by="Probability",
        ascending=False
    ).reset_index(drop=True)

    top20=max(1,math.ceil(len(df)*0.20))

    df["Rank"]=range(1,len(df)+1)

    df["Recommended"]="NO"

    df.loc[:top20-1,"Recommended"]="YES"

    df["Probability"]=df["Probability"].round(4)

    csv_buffer=StringIO()

    df.to_csv(csv_buffer,index=False)

    return StreamingResponse(

        iter([csv_buffer.getvalue()]),

        media_type="text/csv",

        headers={

            "Content-Disposition":"attachment; filename=predictions.csv"

        }

    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("App1:app", host="127.0.0.1", port=8000, reload=True)
