import pandas as pd
import numpy as np

np.random.seed(42)
n = 200

data = pd.DataFrame({
    'time': list(np.random.exponential(scale=125, size=100)) + list(np.random.exponential(scale=85, size=100)),
    'event': list(np.random.binomial(1, 0.65, 100)) + list(np.random.binomial(1, 0.70, 100)),
    'treatment_group': [0]*100 + [1]*100
})

data['time'] = data['time'].round(2)
data.to_csv('test_survival_data.csv', index=False)

# Verify
print(data['treatment_group'].value_counts())
# Should show: 0 = 100, 1 = 100