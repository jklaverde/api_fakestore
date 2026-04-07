import pandas as pd, glob

print ("*****************************")
print (" ")
print('This snipped code shows the changes per product on the different csv files (per scrapped file)')
print (" ")
print ("*****************************")


frames = [pd.read_csv(f) for f in sorted(glob.glob("scraped_data/*.csv"))]
df = pd.concat(frames, ignore_index=True)

# Show price changes for product 1
print(df[df["id"] == 1][["scraped_at", "price", "title"]])

for product_id in range(20):
    print(df[df["id"] == product_id][["scraped_at", "price", "title", "rating_count"]])
    print ("------------------------")

