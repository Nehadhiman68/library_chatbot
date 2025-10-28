import pandas as pd
import os

def merge_books(file1, file2, output):
    """Merge and clean two Excel files containing book data."""
    print(f"🔍 Reading files:\n - {file1}\n - {file2}")

    # Read both Excel files
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)

    # Combine them
    df = pd.concat([df1, df2], ignore_index=True)

    # Try dropping duplicates if column exists
    if "barcode" in df.columns:
        df.drop_duplicates(subset=["barcode"], keep="first", inplace=True)
    else:
        df.drop_duplicates(inplace=True)

    # Clean NaN values
    df.fillna("", inplace=True)

    # Make sure output directory exists
    os.makedirs(os.path.dirname(output), exist_ok=True)

    # Save merged Excel
    df.to_excel(output, index=False)
    print(f"✅ Merged data saved successfully at: {output}")

    return df


if __name__ == "__main__":
    file1 = r"data file\Total books.xlsx"
    file2 = r"data file\Book 22.xlsx"
    output = r"data file\processed_books.xlsx"
    merge_books(file1, file2, output)
