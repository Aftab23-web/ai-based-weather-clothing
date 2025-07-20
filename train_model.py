import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import joblib
import os

# Sample training data
data = [
    {"temp": 5, "humidity": 80, "weather": "Rain", "outfit": "Rainwear"},
    {"temp": 30, "humidity": 40, "weather": "Clear", "outfit": "Summer Casual"},
    {"temp": 12, "humidity": 60, "weather": "Clouds", "outfit": "Light Jacket"},
    {"temp": -2, "humidity": 70, "weather": "Snow", "outfit": "Winter Wear"},
    {"temp": 22, "humidity": 50, "weather": "Clear", "outfit": "T-Shirt and Jeans"}
]

df = pd.DataFrame(data)

# Convert weather to numeric
df['weather_code'] = df['weather'].astype('category').cat.codes
X = df[['temp', 'humidity', 'weather_code']]
y = df['outfit']

model = DecisionTreeClassifier()
model.fit(X, y)

# Ensure ml/ folder exists
os.makedirs('ml', exist_ok=True)

joblib.dump(model, 'ml/outfit_model.pkl')
print("✅ Model trained and saved to ml/outfit_model.pkl")
