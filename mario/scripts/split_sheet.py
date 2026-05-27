"""
스프라이트 시트를 개별 셀(코스튬)로 자동 분할.

배경색을 시트의 가장자리 픽셀로 추정하고, 비배경 픽셀이 모인 영역을
행 → 열 순으로 그룹핑하여 각 셀을 PNG로 저장.

사용:
  python3 scripts/split_sheet.py <input_sheet> <output_dir> [--bg R G B] [--min-size N]
예:
  python3 scripts/split_sheet.py sprites/enemies/goomba_sheet.jpeg sprites/enemies/goomba/
"""

import argparse
import os
from PIL import Image
import numpy as np


def split_sheet(path, out_dir, bg_color=None, min_size=20, threshold=40, padding=2,
                prefix="cell", transparent=False):
    img = Image.open(path).convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]

    if bg_color is None:
        # 4개 모서리의 평균색
        corners = np.array([arr[0, 0, :3], arr[0, w-1, :3],
                            arr[h-1, 0, :3], arr[h-1, w-1, :3]], dtype=int)
        bg_color = tuple(corners.mean(axis=0).astype(int))
        print(f"  추정 배경색: {bg_color}")

    bg = np.array(bg_color, dtype=int)
    # 배경이 아닌 픽셀: 색 차이 > threshold (alpha 0인 픽셀도 비배경으로 처리할지 결정)
    diff = np.abs(arr[:, :, :3].astype(int) - bg).sum(axis=2)
    alpha = arr[:, :, 3] if arr.shape[2] == 4 else np.full((h, w), 255)
    mask = (diff > threshold) & (alpha > 30)

    os.makedirs(out_dir, exist_ok=True)

    # 행별 비배경 있는지
    row_has = mask.any(axis=1)
    row_groups = _groups(row_has, h, min_size)
    print(f"  행 그룹 {len(row_groups)}개")

    cell_idx = 0
    for ry1, ry2 in row_groups:
        sub_mask = mask[ry1:ry2]
        col_has = sub_mask.any(axis=0)
        col_groups = _groups(col_has, w, min_size)
        for cx1, cx2 in col_groups:
            # 패딩 추가
            x1 = max(0, cx1 - padding)
            y1 = max(0, ry1 - padding)
            x2 = min(w, cx2 + padding)
            y2 = min(h, ry2 + padding)
            cell = img.crop((x1, y1, x2, y2))
            if transparent:
                cell_arr = np.array(cell)
                # 셀에서 가장 흔한 색을 셀 배경으로 추정 (셀별 배경색이 다른 시트 대응)
                flat = cell_arr[:, :, :3].reshape(-1, 3)
                uniq, cnts = np.unique(flat, axis=0, return_counts=True)
                cell_bg = uniq[cnts.argmax()].astype(int)
                # 셀 배경 + 시트 외곽 배경 둘 다 마스크
                diff_cell = np.abs(cell_arr[:, :, :3].astype(int) - cell_bg).sum(axis=2)
                diff_sheet = np.abs(cell_arr[:, :, :3].astype(int) - bg).sum(axis=2)
                is_bg = (diff_cell < threshold) | (diff_sheet < threshold)
                cell_arr[:, :, 3] = np.where(is_bg, 0, 255).astype(np.uint8)
                cell = Image.fromarray(cell_arr)
            out_path = os.path.join(out_dir, f"{prefix}_{cell_idx + 1:03d}.png")
            cell.save(out_path)
            cell_idx += 1
    print(f"→ {cell_idx}개 셀을 {out_dir}/에 저장")


def _groups(line_has, total, min_size):
    """1D mask에서 연속된 True 구간을 (start, end+1) 리스트로."""
    groups = []
    in_g = False
    start = 0
    for i in range(total):
        if line_has[i]:
            if not in_g:
                start = i
                in_g = True
        else:
            if in_g:
                if i - start >= min_size:
                    groups.append((start, i))
                in_g = False
    if in_g and total - start >= min_size:
        groups.append((start, total))
    return groups


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("out_dir")
    p.add_argument("--bg", nargs=3, type=int, default=None,
                   metavar=("R", "G", "B"))
    p.add_argument("--min-size", type=int, default=20)
    p.add_argument("--threshold", type=int, default=40)
    p.add_argument("--padding", type=int, default=2)
    p.add_argument("--prefix", default="cell")
    p.add_argument("--transparent", action="store_true",
                   help="배경을 투명(alpha=0)으로 처리")
    args = p.parse_args()
    print(f"분할: {args.input}")
    split_sheet(args.input, args.out_dir,
                bg_color=tuple(args.bg) if args.bg else None,
                min_size=args.min_size, threshold=args.threshold,
                padding=args.padding, prefix=args.prefix,
                transparent=args.transparent)
