from pandas import read_csv
import pandas as pd
import matplotlib.pyplot as plt
file_path=r"kolam_data\Kolam CSV files\Kolam CSV files\kolam19.csv"
df=read_csv(file_path)

# Image kolam19-26 corresponds to CSV kolam 27

kolam_number=27

x=df[f"x-kolam {kolam_number}"]
y=df[f"y-kolam {kolam_number}"]

# remove missing values

valid=x.notna() & y.notna()

x=x[valid].astype(float)
y=y[valid].astype(float)


print("Number of points:", len(x))
print("Starting point:", (x.iloc[0], y.iloc[0]))
print("Ending point:", (x.iloc[-1], y.iloc[-1]))

#plot

plt.figure(figsize=(8,8))

plt.plot(x, y, linewidth=1)

plt.axis("equal")
plt.title(f"Kolam {kolam_number}")
plt.xlabel("X")
plt.ylabel("Y")
plt.grid(True)

plt.show()