import argparse
import os
import time
import pandas as pd
from fol_solver import solve_fol

def process_dataset(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    print(f"\n==========================================")
    print(f" Processing: {dataset_name} ({len(df)} samples) ")
    print(f"==========================================")

    is_three_valued = False
    if "flag" in df.columns:
        unique_flags = set(df["flag"].astype(str).str.strip().unique())
        if "Uncertain" in unique_flags:
            is_three_valued = True

    predictions = []
    start_time = time.time()

    for idx, row in df.iterrows():
        ctx = str(row["context"])
        stmt = str(row["statement"])
        pred = solve_fol(ctx, stmt, is_three_valued=is_three_valued)
        predictions.append(pred)

    elapsed = time.time() - start_time
    df["predicted_label"] = predictions

    if "flag" in df.columns:
        df["flag"] = df["flag"].astype(str).str.strip()
        correct = (df["predicted_label"] == df["flag"]).sum()
        accuracy = (correct / len(df)) * 100
        print(f"Accuracy         : {correct} / {len(df)} ({accuracy:.2f}%)")
        print(
            f"Total Time       : {elapsed:.3f} s (Avg: {(elapsed/len(df))*1000:.2f} ms/row)"
        )
        print("\nPrediction Distribution:")
        print(df["predicted_label"].value_counts().to_string())

    return df

def prepare_submission_df(df: pd.DataFrame) -> pd.DataFrame:
    id_col = None
    for col in df.columns:
        if col.lower() in ["id", "example_id", "sample_id", "index"]:
            id_col = col
            break

    if id_col is not None:
        ids = df[id_col].values
    else:
        ids = list(range(len(df)))

    return pd.DataFrame({"ID": ids, "Prediction": df["predicted_label"].values})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process a logic dataset and generate submission.csv"
    )
    parser.add_argument("csv_path", type=str, help="Path to the CSV dataset file")
    args = parser.parse_args()

    dataset_path = args.csv_path
    dataset_name = os.path.splitext(os.path.basename(dataset_path))[0]

    # Load dataset from positional argument
    df = pd.read_csv(dataset_path)
    df_res = process_dataset(df, dataset_name)

    submission_df = prepare_submission_df(df_res)
    submission_df.to_csv("submission.csv", index=False)

    print("\n==========================================")
    print(" SUBMISSION GENERATED ")
    print("==========================================")
    print(f"Total Rows Saved : {len(submission_df)}")
    print(f"File Saved       : submission.csv")