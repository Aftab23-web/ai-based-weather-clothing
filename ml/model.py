import joblib 
import pandas as pd 

model = joblib.load("ml/outfit_model.pkl")

def predict_outfit(temp, humidity, weather):
    weather_code = pd.Series([weather]).astype('category').cat.codes[0]
    input_data = pd.DataFrame([{
        "temp": temp,
        "humidity": humidity,
        "weather_code": weather_code
    }])
    return model.predict(input_data)[0]
# Example usage:
prediction = predict_outfit(25, 60, 'sunny')
print("Predicted outfit label:", prediction)

