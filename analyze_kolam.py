import pandas as pd
import numpy as np

file_path = r"kolam_data\Kolam CSV files\Kolam CSV files\kolam19.csv"

df = pd.read_csv(file_path)

print("Dataset shape:", df.shape)

result=[]

#400 Kolams
for kolam_number in range(1,401):
    x=df[f"x-kolam {kolam_number}"].dropna().astype(float).values
    y=df[f"y-kolam {kolam_number}"].dropna().astype(float).values

    #distance between consecutive points
    dx=np.diff(x)
    dy=np.diff(y)

    distance=np.sqrt(dx**2+dy**2)

    path_length=distance.sum()

    #distance between first and last point 
    start_end_distance=np.sqrt(
        (x[-1]-x[0])**2+(y[-1]-y[0])**2
    )
    #Bounding box
    width=x.max()-x.min()
    height=y.max()-y.min()

    result.append({
        "Kolam":kolam_number,
        "point":len(x),
        "path_length":path_length,
        "start_end_distance": start_end_distance,
        "width": width,
        "height": height
    })
result_df=pd.DataFrame(result)

print("\nFIRST 10 KOLAMS")
print(result_df.head(10).to_string(index=False))

print("\nSUMMARY")
print(result_df.describe())

# Save results
result_df.to_csv("kolam19_analysis.csv", index=False)

print("\nSaved analysis to:")
print("kolam19_analysis.csv")
