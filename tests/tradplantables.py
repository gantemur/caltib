#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Table 12: Equation for planets
    table_12 = {
        'Mercury': [0, 10, 17, 20],
        'Venus':   [0, 5, 9, 10],
        'Mars':    [0, 25, 43, 50],
        'Jupiter': [0, 11, 20, 23],
        'Saturn':  [0, 22, 37, 43]
    }

    # Table 13: Final correction for planets
    table_13 = {
        'Mercury': [0, 16, 32, 47, 61, 74, 85, 92, 97, 97, 93, 82, 62, 34],
        'Venus':   [0, 25, 50, 75, 99, 123, 145, 167, 185, 200, 208, 202, 172, 83],
        'Mars':    [0, 24, 47, 70, 93, 114, 135, 153, 168, 179, 182, 171, 133, 53],
        'Jupiter': [0, 10, 20, 29, 37, 43, 49, 51, 52, 49, 43, 34, 23, 7],
        'Saturn':  [0, 6, 11, 16, 20, 24, 26, 28, 28, 26, 22, 17, 11, 3]
    }

    planets = ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']
    colors = {'Mercury': 'gray', 'Venus': 'orange', 'Mars': 'red', 'Jupiter': 'brown', 'Saturn': 'purple'}

    # Modern orbital radius ratios (inner/outer)
    r_modern = {
        'Mercury': 0.387,
        'Venus': 0.723,
        'Mars': 1.0 / 1.524,  # 0.656
        'Jupiter': 1.0 / 5.204, # 0.192
        'Saturn': 1.0 / 9.582  # 0.104
    }

    # --- Plot Table 12 (Extended to Half Period) ---
    plt.figure(figsize=(9, 7))
    
    # 1. Define the anomaly angles (in Degrees) for a half-period
    # (The indices 0, 1, 2, 3 correspond to 0r0°, 1r0°, 2r0°, 3r0°/90° Anomaly)
    anomaly_angles_deg = np.array([0, 30, 60, 90, 120, 150, 180])

    # 2. Draw the target mathematical curve FIRST (dashed, behind the lines)
    # y = sin(x) for the normalized profile
    smooth_x_deg = np.linspace(0, 180, 200)
    ideal_sine_wave = np.sin(np.radians(smooth_x_deg))
    
    plt.plot(smooth_x_deg, ideal_sine_wave, linestyle='--', color='black', 
             linewidth=1.5, alpha=0.5, label='Ideal sin(Anomaly)')

    # 3. Plot the ancient reflected tabular data
    for p in planets:
        # Get raw data for the first quarter period [0, 1, 2, 3]
        y_quarter = np.array(table_12[p], dtype=float)
        y_max = np.max(y_quarter)
        
        # Create full half-period array: [y[0], y[1], y[2], y[3], y[2], y[1], y[0]]
        # We slice 2::-1 to reverse the array from index 2 down, reflecting the sine shape
        y_reflected = y_quarter[2::-1]
        y_half_period_raw = np.concatenate([y_quarter, y_reflected])
        
        # Normalize to 1.0 based on the quarter-period max
        y_norm = y_half_period_raw / y_max
        
        # Plot piecewise-linear data using degrees on the X-axis
        plt.plot(anomaly_angles_deg, y_norm, marker='o', markersize=5, 
                 label=f"{p} (Kālacakra)", color=colors[p], alpha=0.9, linewidth=1.2)

    plt.title('Table 12: Equation for Planets (Normalized Half Period)')
    plt.xlabel('Anomaly Angle from Apogee (Degrees)')
    plt.ylabel('Normalized Sine Amplitude')
    
    # Force x-axis ticks at useful 1-Rashi (30°) intervals
    plt.xticks(anomaly_angles_deg)
    
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig('table_12_half_period_sine_check.png', dpi=200)
    print("Saved: table_12_half_period_sine_check.png")
    plt.close()

    # --- Table 13 ---
    print("--- Implied vs Modern Radius Ratios (r) ---")
    for p in planets:
        # 1 Kālacakra unit (chu-tsho) = 360 / (27 * 60) degrees
        max_val = np.max(table_13[p])
        max_deg = max_val * (360.0 / 1620.0)
        r_implied = np.sin(np.radians(max_deg))
        print(f"{p:8s} | Implied r: {r_implied:.4f} | Modern r: {r_modern[p]:.4f} | Diff: {abs(r_implied - r_modern[p]):.4f}")

    plt.figure(figsize=(11, 7))
    
    # Smooth X axis from 0 to 13.5 Nakshatras (which maps exactly to 0° to 180°)
    x_smooth_idx = np.linspace(0, 13.5, 200)
    x_smooth_deg = x_smooth_idx * (360.0 / 27.0)

    for p in planets:
        r = r_modern[p]
        
        # 1. Plot the Modern Kinematic Curve (Dashed)
        # C(x) = arctan( r*sin(x) / (1 + r*cos(x)) )
        C_smooth_rad = np.arctan2(r * np.sin(np.radians(x_smooth_deg)), 1 + r * np.cos(np.radians(x_smooth_deg)))
        C_smooth_norm = C_smooth_rad / np.max(C_smooth_rad)
        
        # CHANGED: Now plotting against x_smooth_deg
        plt.plot(x_smooth_deg, C_smooth_norm, linestyle='--', color=colors[p], 
                 alpha=0.5, linewidth=2)

        # 2. Plot the Discrete Kālacakra Data (Dots/Solid Line)
        y = np.array(table_13[p], dtype=float)
        y_norm = y / np.max(y)
        x_kalacakra_deg = np.arange(len(y_norm)) * (360.0 / 27.0)
        plt.plot(x_kalacakra_deg, y_norm, marker='o', markersize=5, 
                 color=colors[p], alpha=0.9, linewidth=1.5)

    plt.title('Table 13: Equation of Conjunction (Kālacakra vs. Modern Kinematics)')
    plt.xlabel('Anomaly Angle (Degrees)') # Nakshatra Steps of 13.33°
    plt.ylabel('Normalized Amplitude')
    plt.xticks(np.arange(0, 181, 30))  # Force ticks every 30 degrees
    plt.grid(True, alpha=0.3)
    
    # Custom Legend
    import matplotlib.lines as mlines
    legend_elements = [mlines.Line2D([0], [0], color='black', linestyle='--', alpha=0.5, label='Modern Kinematic C(x)')]
    for p in planets:
        legend_elements.append(mlines.Line2D([0], [0], color=colors[p], marker='o', label=f"{p} (Kālacakra)"))
        
    plt.legend(handles=legend_elements)
    plt.tight_layout()
    plt.savefig('table_13_modern_overlay.png', dpi=200)
    print("\nSaved: table_13_modern_overlay.png")

if __name__ == "__main__":
    main()
