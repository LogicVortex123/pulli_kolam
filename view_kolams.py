import pandas as pd
import matplotlib.pyplot as plt

file_path = r"kolam_data\Kolam CSV files\Kolam CSV files\kolam19.csv"

df = pd.read_csv(file_path)

kolams = [1, 10, 20, 50, 100, 200, 300, 400]

fig, axes = plt.subplots(2, 4, figsize=(16, 8))

for ax, kolam_number in zip(axes.flat, kolams):

    x = df[f"x-kolam {kolam_number}"]
    y = df[f"y-kolam {kolam_number}"]

    valid = x.notna() & y.notna()

    x = x[valid]
    y = y[valid]

    ax.plot(x, y, linewidth=0.8)

    ax.set_title(f"Kolam {kolam_number}")
    ax.set_aspect("equal")
    ax.axis("off")

plt.tight_layout()
plt.show()