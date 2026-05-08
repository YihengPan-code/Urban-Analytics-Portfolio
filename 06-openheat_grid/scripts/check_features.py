import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('data/grid/toa_payoh_grid_v07_features.csv')

features = [
    'building_density',
    'road_fraction',
    'tree_canopy_fraction',
    'impervious_fraction',
    'park_distance_m',
    'water_distance_m',
]

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
for ax, feat in zip(axes.flat, features):
    sc = ax.scatter(df['lon'], df['lat'], c=df[feat], s=10, cmap='viridis')
    ax.set_title(f'{feat}\nmean={df[feat].mean():.3f}, max={df[feat].max():.3f}')
    ax.set_aspect('equal')
    plt.colorbar(sc, ax=ax, fraction=0.04)

plt.tight_layout()
plt.savefig('outputs/v07_six_features_check.png', dpi=120, bbox_inches='tight')
print('Saved: outputs/v07_six_features_check.png')