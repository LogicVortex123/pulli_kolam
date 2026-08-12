import pandas as pd
import numpy as np

file_path = r"kolam_data\Kolam CSV files\Kolam CSV files\kolam19.csv"

df = pd.read_csv(file_path)

def symmetry_error(x,y,tranform):
    """
    Compare a kolam with a transformed version of itself.
    Smaller error=more Symmetric.
    """

    points=np.column_stack((x,y))
    transformed=tranform(points)

    #for every transformed points, find the closest 
    # original point
    errors=[]

    for p in transformed:
        dist=np.sqrt(
            (points[:,0]-p[0])**2+
            (points[:,1]-p[1])**2
        )
        errors.append(np.min(dist))

    return np.mean(errors)

results=[]


for kolam_number in range(1, 401):

    x = df[f"x-kolam {kolam_number}"].astype(float).values
    y = df[f"y-kolam {kolam_number}"].astype(float).values

    # Center the Kolam
    x = x - np.mean(x)
    y = y - np.mean(y)

    # Vertical reflection: (x,y) -> (-x,y)
    vertical = lambda p: np.column_stack((-p[:, 0], p[:, 1]))

    # Horizontal reflection: (x,y) -> (x,-y)
    horizontal = lambda p: np.column_stack((p[:, 0], -p[:, 1]))

    # 180 degree rotation
    rotation_180 = lambda p: np.column_stack((-p[:, 0], -p[:, 1]))

    vertical_error = symmetry_error(x, y, vertical)
    horizontal_error = symmetry_error(x, y, horizontal)
    rotation_error = symmetry_error(x, y, rotation_180)

    results.append({
        "kolam": kolam_number,
        "vertical_symmetry": vertical_error,
        "horizontal_symmetry": horizontal_error,
        "rotation_180": rotation_error
    })


results_df = pd.DataFrame(results)


print("\nFIRST 10 KOLAMS")
print(results_df.head(10).to_string(index=False))

print("\nAVERAGE SYMMETRY ERROR")
print(results_df[
    ["vertical_symmetry",
     "horizontal_symmetry",
     "rotation_180"]
].mean())

print("\nMOST VERTICALLY SYMMETRIC")
print(
    results_df
    .sort_values("vertical_symmetry")
    .head(10)
    .to_string(index=False)
)

print("\nMOST HORIZONTALLY SYMMETRIC")
print(
    results_df
    .sort_values("horizontal_symmetry")
    .head(10)
    .to_string(index=False)
)

print("\nMOST 180-DEGREE SYMMETRIC")
print(
    results_df
    .sort_values("rotation_180")
    .head(10)
    .to_string(index=False)
)

results_df.to_csv("kolam19_symmetry.csv", index=False)

print("\nSaved:")
print("kolam19_symmetry.csv")