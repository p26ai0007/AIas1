# First activate the env:
.venv\Scripts\activate

# Install the required libraries
pip install -r requirements.txt

# Run the cmd with the appropriate path as per the example, if not able to run please connect with me
# Test data must has example_id,context,statement,flag columns or only context,statement,flag
# Context should be seperated by ";"
python reasoning_agent.py data\processed\ruletaker_fol_test.csv

# Single entailment can be check by using (Context should be seperated by ";"):
from fol_engine import solve_fol

context = "∀x (Employee(x) → HasAccess(x)) ; Employee(alice)"
statement = "HasAccess(alice)"

result = solve_fol(context, statement, is_three_valued=True)
print(f"Prediction: {result}")

# data_preparation.ipynb is for creating the processed data, that converts natural language to Fol form.

# running reasoning_agent.ipynb file will create the submission.csv again using "ruletaker_fol_ood_test.csv, counterbench_fol_train.csv, folio_fol_validation.csv", and results are:
==========================================
 Processing: ruletaker_fol_test (375 samples) 
==========================================
Accuracy         : 279 / 375 (74.40%)
Total Time       : 0.171 s (Avg: 0.46 ms/row)

Prediction Distribution:
predicted_label
False    322
True      53

==========================================
 Processing: counterbench_fol_train (1200 samples) 
==========================================
Accuracy         : 680 / 1200 (56.67%)
Total Time       : 0.366 s (Avg: 0.31 ms/row)

Prediction Distribution:
predicted_label
False    1025
True      175

==========================================
 Processing: folio_fol_validation (203 samples) 
==========================================
Accuracy         : 122 / 203 (60.10%)
Total Time       : 44.391 s (Avg: 218.67 ms/row)

Prediction Distribution:
predicted_label
Uncertain    125
True          50
False         28

==========================================
 SUBMISSION GENERATED 
==========================================
Total Rows Saved : 1778
File Saved       : submission.csv