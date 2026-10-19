# Original UCI coding

Use these original codes, not the zero-based codes found in some repackaged
Kaggle files. Every key is required by the API; send null for a missing value.
API numeric bounds are input sanity checks, not clinical cutoffs.

| Key | Meaning | Values or unit |
|---|---|---|
| age | Age | Years |
| sex | Source sex category | 0 female, 1 male |
| cp | Chest pain | 1 typical angina, 2 atypical angina, 3 non-anginal, 4 asymptomatic |
| trestbps | Resting blood pressure | mm Hg |
| chol | Serum cholesterol | mg/dl |
| fbs | Fasting blood sugar above 120 mg/dl | 0 false, 1 true |
| restecg | Resting ECG | 0 normal, 1 ST-T abnormality, 2 probable/definite LV hypertrophy |
| thalach | Maximum heart rate achieved | Beats per minute |
| exang | Exercise induced angina | 0 no, 1 yes |
| oldpeak | Exercise induced ST depression relative to rest | Numeric source measurement |
| slope | Peak exercise ST slope | 1 upsloping, 2 flat, 3 downsloping |
| ca | Major vessels colored by fluoroscopy | 0, 1, 2, 3 |
| thal | Thal source category | 3 normal, 6 fixed defect, 7 reversible defect |
| target | Binary training label only | 0 absent, 1 present; never send as input |

Source: UCI Heart Disease dataset, DOI 10.24432/C52P4X,
https://archive.ics.uci.edu/dataset/45/heart+disease. CC BY 4.0.
