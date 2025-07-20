# ml/train_model.py

import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import joblib
import os

# ✅ Updated training data to match app.py 'outfits' keys
data = [
    {"temp": 5, "humidity": 80, "weather": "Rain", "outfit": "rainy"},
    {"temp": 30, "humidity": 40, "weather": "Clear", "outfit": "hot"},
    {"temp": 12, "humidity": 60, "weather": "Clouds", "outfit": "mild"},
    {"temp": -2, "humidity": 70, "weather": "Snow", "outfit": "cold"},
    {"temp": 22, "humidity": 50, "weather": "Clear", "outfit": "mild"},
    {"temp": 35, "humidity": 30, "weather": "Clear", "outfit": "hot"},
    {"temp": 8, "humidity": 85, "weather": "Rain", "outfit": "rainy"},
    {"temp": -5, "humidity": 75, "weather": "Snow", "outfit": "cold"}
]

df = pd.DataFrame(data)

# Encode weather to numeric
df['weather_code'] = df['weather'].astype('category').cat.codes
X = df[['temp', 'humidity', 'weather_code']]
y = df['outfit']

model = DecisionTreeClassifier()
model.fit(X, y)

os.makedirs('ml', exist_ok=True)
joblib.dump(model, 'ml/outfit_model.pkl')

print("✅ Model trained and saved to ml/outfit_model.pkl")
