import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import os

# =============== MACHINE LEARNING PIPELINE ===============

data_dir = r"d:\Modal_Analysis\Model_Beam_Modal_Analysis"

# 1. Load all Modes and combine them into one large dataset
all_data = []

print("Loading data for all modes...")
# Assuming you have modes 1 through 6
for mode in range(1, 7):
    file_path = os.path.join(data_dir, f"Mode{mode}.txt")
    if os.path.exists(file_path):
        # Read the file
        df = pd.read_csv(file_path, sep='\t')
        df.columns = df.columns.str.strip()
        
        # Rename columns standardly
        df.rename(columns={
            'Node Number': 'Node',
            'X Location (m)': 'X',
            'Y Location (m)': 'Y',
            'Z Location (m)': 'Z',
            'Total Deformation (m)': 'Deformation'
        }, inplace=True)
        
        # **NEW**: Add a feature to tell the AI which mode this is!
        df['Mode'] = mode
        all_data.append(df)
        print(f" - Loaded Mode {mode}")

# Combine all dataframes into one mega-dataframe
final_df = pd.concat(all_data, ignore_index=True)
print(f"\nTotal rows in dataset: {len(final_df)}")

# 2. Define Features (Inputs) and Targets (Outputs)
# Now the ML model learns: (X, Y, Z, Mode) --> Deformation
features = final_df[['X', 'Y', 'Z', 'Mode']]
target = final_df['Deformation']

# 3. Split the data
X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

# 4. Initialize and Train the Machine Learning Model
print("\nTraining the Multi-Mode Machine Learning model...")
model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
print("Training Complete!")

# 5. Evaluate the ML Model
predictions = model.predict(X_test)
mse = mean_squared_error(y_test, predictions)
print(f"Mean Squared Error (MSE) on Test Data: {mse:.8f}")
r2 = r2_score(y_test, predictions)
print(f"Accuracy (R-Squared Score): {r2 * 100:.2f}%")

# 6. Test a fast prediction for different Modes!
print(f"\n--- INFERENCE TEST ---")
sample_coord_mode1 = pd.DataFrame({'X': [0.001], 'Y': [0.0], 'Z': [0.019], 'Mode': [1]})
sample_coord_mode2 = pd.DataFrame({'X': [0.001], 'Y': [0.0], 'Z': [0.019], 'Mode': [2]})

pred_m1 = model.predict(sample_coord_mode1)[0]
pred_m2 = model.predict(sample_coord_mode2)[0]

print(f"Node at X=0.001, Y=0, Z=0.019 -> Predicted Mode 1 Deformation: {pred_m1:.6f} m")
print(f"Node at X=0.001, Y=0, Z=0.019 -> Predicted Mode 2 Deformation: {pred_m2:.6f} m")
