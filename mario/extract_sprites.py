"""Extract individual sprites from a Mario cross-stitch sprite sheet.

The source image is a cross-stitch pattern where each "bead" is a colored pixel
surrounded by grid gaps. Strategy:
1. Detect colorful "bead" pixels (high saturation or dark)
2. Find connected sprite regions via components
3. For each sprite: fill interior gaps with nearest neighbor colors, then
   make exterior background transparent.
"""
from PIL import Image
import numpy as np
import os
from scipy import ndimage


def inpaint_gaps(sprite_arr, color_mask):
    """Fill gap pixels inside a sprite using nearest-neighbor color from known pixels.

    color_mask: True where we have good sprite color pixels.
    Gap pixels surrounded by sprite pixels get filled with average of nearest neighbors.
    """
    h, w = color_mask.shape

    # Determine the sprite interior: fill holes in the color_mask
    # Use binary_fill_holes to find the sprite silhouette
    filled = ndimage.binary_fill_holes(
        ndimage.binary_dilation(color_mask, iterations=2)
    )

    # Gap pixels = inside the silhouette but not a color pixel
    gaps = filled & ~color_mask

    if not np.any(gaps):
        return sprite_arr

    # Use distance transform to find nearest colored pixel for each gap
    # For each channel, interpolate from known pixels
    result = sprite_arr.copy()

    # Label the known color pixels, use nearest-neighbor via distance_transform_edt
    dist, indices = ndimage.distance_transform_edt(
        ~color_mask, return_distances=True, return_indices=True
    )

    # Fill gap pixels with the color of their nearest known pixel
    gap_ys, gap_xs = np.where(gaps)
    nearest_ys = indices[0][gap_ys, gap_xs]
    nearest_xs = indices[1][gap_ys, gap_xs]

    result[gap_ys, gap_xs, :3] = sprite_arr[nearest_ys, nearest_xs, :3]
    result[gap_ys, gap_xs, 3] = 255  # Make filled pixels opaque

    return result


def main():
    src = "/Users/yamkim/.claude/image-cache/7ae3aba0-80e1-4bfb-9213-1cbbd8ab6c67/3.png"
    out_dir = "/Users/yamkim/Documents/iingenieur/ScratchHomework/mario/sprites/mario"

    img = Image.open(src).convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f"Image size: {w}x{h}")

    # Detect colorful sprite pixels via HSV
    hsv = np.array(img.convert("RGB").convert("HSV"))
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    # Sprite pixels: high saturation OR very dark (outlines)
    color_mask_global = (saturation > 40) | (value < 100)

    # Clean up noise
    color_mask_global = ndimage.binary_opening(color_mask_global, iterations=1)

    # Dilation for component detection (grouping beads into sprites)
    struct = ndimage.generate_binary_structure(2, 2)
    dilated = ndimage.binary_dilation(color_mask_global, structure=struct, iterations=2)
    labeled, num_features = ndimage.label(dilated)
    print(f"Raw components: {num_features}")

    # Extract bounding boxes
    bboxes = []
    for i in range(1, num_features + 1):
        ys, xs = np.where(labeled == i)
        if len(ys) < 200:
            continue
        y_min, y_max = ys.min(), ys.max()
        x_min, x_max = xs.min(), xs.max()
        bw, bh = x_max - x_min, y_max - y_min
        if bw < 20 or bh < 20 or bw > 200 or bh > 200:
            continue
        pad = 2
        bboxes.append((
            max(0, x_min - pad), max(0, y_min - pad),
            min(w, x_max + pad), min(h, y_max + pad)
        ))

    print(f"Filtered sprites: {len(bboxes)}")

    # Sort in reading order
    bboxes.sort(key=lambda b: b[1])
    rows = []
    current_row = [bboxes[0]]
    for bb in bboxes[1:]:
        cy_cur = (current_row[0][1] + current_row[0][3]) / 2
        cy_new = (bb[1] + bb[3]) / 2
        if abs(cy_new - cy_cur) < 40:
            current_row.append(bb)
        else:
            rows.append(sorted(current_row, key=lambda b: b[0]))
            current_row = [bb]
    rows.append(sorted(current_row, key=lambda b: b[0]))

    print(f"Detected {len(rows)} rows")

    row_names = ["small", "walk", "action", "run", "cape", "fly", "spin"]

    idx = 0
    for row_i, row in enumerate(rows):
        row_name = row_names[row_i] if row_i < len(row_names) else f"row{row_i+1}"
        print(f"Row {row_i+1} ({row_name}): {len(row)} sprites")

        for col_i, bbox in enumerate(row):
            x_min, y_min, x_max, y_max = bbox

            sprite_arr = arr[y_min:y_max, x_min:x_max].copy()
            local_mask = color_mask_global[y_min:y_max, x_min:x_max]

            # Step 1: Inpaint gaps inside the sprite with nearest color
            sprite_arr = inpaint_gaps(sprite_arr, local_mask)

            # Step 2: Make exterior background transparent
            # The sprite silhouette = filled holes of the color mask
            silhouette = ndimage.binary_fill_holes(
                ndimage.binary_dilation(local_mask, iterations=2)
            )
            # Erode slightly to clean edges
            silhouette = ndimage.binary_erosion(silhouette, iterations=1)
            # Re-dilate to restore size
            silhouette = ndimage.binary_dilation(silhouette, iterations=1)

            sprite_arr[~silhouette, 3] = 0

            sprite_clean = Image.fromarray(sprite_arr)
            fname = f"mario_{row_name}_{col_i+1}.png"
            sprite_clean.save(os.path.join(out_dir, fname))
            print(f"  {fname} ({x_max-x_min}x{y_max-y_min})")
            idx += 1

    print(f"\nTotal: {idx} sprites saved to {out_dir}")


if __name__ == "__main__":
    main()
