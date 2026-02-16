import hashlib
import pandas as pd
import colorsys

def colorize_wo_ppm(value, color_map_cache={}):
    """
    Assign a consistent background color to each unique WO/PPM value.
    - If numeric > 600000: no background, black font
    - If numeric <= 600000: semi-transparent background (alpha ~0.5), black font
    """
    if pd.isna(value) or str(value).strip() == "":
        return ""

    val_str = str(value).strip()

    # Determine if numeric and greater than 600000
    try:
        num_val = float(val_str)
        is_large = num_val > 600000
    except ValueError:
        is_large = False

    # Reuse cached color
    if val_str in color_map_cache:
        base_color = color_map_cache[val_str]
    else:
        # --- Generate a unique but visually distinct color ---
        hash_val = int(hashlib.sha1(val_str.encode()).hexdigest(), 16)
        hue = (hash_val % 360) / 360.0
        sat = 0.55 + ((hash_val >> 8) % 30) / 100.0
        light = 0.55 + ((hash_val >> 16) % 30) / 100.0

        r, g, b = colorsys.hls_to_rgb(hue, light, sat)
        base_color = (int(r*255), int(g*255), int(b*255))
        color_map_cache[val_str] = base_color

    r, g, b = base_color

    if is_large:
        # No background, black font
        bg_style = "transparent"
        text_color = "#1E40AF"
    else:
        # Semi-transparent background (~50%), black font
        bg_style = f"rgba({r},{g},{b},0.5)"
        text_color = "#000000"

    return f"<div style='color:{text_color}; background-color:{bg_style}; border-radius:5px; padding:3px 6px; font-weight:600;'>{val_str}</div>"
