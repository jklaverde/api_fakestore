import pandas as pd, glob

frames = [pd.read_csv(f) for f in sorted(glob.glob("scraped_data/*.csv"))]
df = pd.concat(frames, ignore_index=True)

# Show price changes for product 1
print(df[df["id"] == 1][["scraped_at", "price", "title"]])