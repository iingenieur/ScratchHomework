#!/usr/bin/env python3
"""
sprites_new의 참조 이미지를 기반으로 새 스프라이트 생성
- 걷기 애니메이션 (발바꿈 2프레임)
- 점프 스프라이트
- 깃발/깃대 스프라이트
- 배경
"""

from PIL import Image, ImageFilter
import numpy as np
from scipy import ndimage
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE, "sprites_new")
DST_DIR = os.path.join(BASE, "sprites_new")

TARGET_HEIGHT = 80


def remove_bg(img, tolerance=35):
    """이미지 가장자리에 연결된 배경색을 제거"""
    rgba = img.convert("RGBA")
    data = np.array(rgba)
    h, w = data.shape[:2]

    # 가장자리 픽셀에서 배경색 추출
    edge_pixels = np.concatenate([
        data[0, :, :3], data[h-1, :, :3],
        data[:, 0, :3], data[:, w-1, :3]
    ]).reshape(-1, 3).astype(float)
    bg_color = np.median(edge_pixels, axis=0)

    # 배경색과의 거리 계산
    diff = np.sqrt(np.sum((data[:,:,:3].astype(float) - bg_color) ** 2, axis=2))
    similar = diff < tolerance

    # 가장자리에 연결된 배경 픽셀만 제거 (flood fill 효과)
    edge_mask = np.zeros((h, w), dtype=bool)
    edge_mask[0, :] = True
    edge_mask[-1, :] = True
    edge_mask[:, 0] = True
    edge_mask[:, -1] = True

    seed = similar & edge_mask
    labeled, _ = ndimage.label(similar)
    edge_labels = set(labeled[seed].flatten())
    edge_labels.discard(0)

    bg_mask = np.isin(labeled, list(edge_labels))

    # 경계 부분 안티앨리어싱
    bg_float = bg_mask.astype(float)
    bg_smooth = ndimage.gaussian_filter(bg_float, sigma=0.8)
    alpha = np.clip((1.0 - bg_smooth) * 255, 0, 255).astype(np.uint8)

    data[:,:,3] = alpha
    return Image.fromarray(data)


def remove_bg_multi(img, tolerances=[30, 45, 55]):
    """여러 배경색을 순차적으로 제거 (복잡한 배경용)"""
    rgba = img.convert("RGBA")
    data = np.array(rgba)
    h, w = data.shape[:2]

    total_bg = np.zeros((h, w), dtype=bool)

    for tol in tolerances:
        # 현재 가장자리 불투명 픽셀에서 배경색 재계산
        current_alpha = data[:,:,3]

        edge_pixels = []
        for i in range(w):
            if current_alpha[0, i] > 128 and not total_bg[0, i]:
                edge_pixels.append(data[0, i, :3])
            if current_alpha[h-1, i] > 128 and not total_bg[h-1, i]:
                edge_pixels.append(data[h-1, i, :3])
        for i in range(h):
            if current_alpha[i, 0] > 128 and not total_bg[i, 0]:
                edge_pixels.append(data[i, 0, :3])
            if current_alpha[i, w-1] > 128 and not total_bg[i, w-1]:
                edge_pixels.append(data[i, w-1, :3])

        if not edge_pixels:
            break

        edge_arr = np.array(edge_pixels, dtype=float)
        bg_color = np.median(edge_arr, axis=0)

        diff = np.sqrt(np.sum((data[:,:,:3].astype(float) - bg_color) ** 2, axis=2))
        similar = (diff < tol) & (~total_bg)

        edge_touch = np.zeros((h, w), dtype=bool)
        edge_touch[0, :] = True
        edge_touch[-1, :] = True
        edge_touch[:, 0] = True
        edge_touch[:, -1] = True
        edge_touch = edge_touch | total_bg  # 이미 제거된 영역과 접한 것도 포함

        seed = similar & edge_touch
        combined = similar | total_bg
        labeled, _ = ndimage.label(combined)
        edge_labels = set(labeled[seed].flatten())
        edge_labels.discard(0)

        new_bg = np.isin(labeled, list(edge_labels))
        total_bg = new_bg

    # 안티앨리어싱
    bg_float = total_bg.astype(float)
    bg_smooth = ndimage.gaussian_filter(bg_float, sigma=0.8)
    alpha = np.clip((1.0 - bg_smooth) * 255, 0, 255).astype(np.uint8)
    data[:,:,3] = alpha
    return Image.fromarray(data)


def trim(img, padding=2):
    """투명 영역 잘라내기"""
    data = np.array(img)
    alpha = data[:,:,3]
    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    if not np.any(rows) or not np.any(cols):
        return img
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    # 패딩 추가
    rmin = max(0, rmin - padding)
    rmax = min(data.shape[0]-1, rmax + padding)
    cmin = max(0, cmin - padding)
    cmax = min(data.shape[1]-1, cmax + padding)
    return img.crop((cmin, rmin, cmax+1, rmax+1))


def resize_h(img, target_h):
    """높이 기준 리사이즈 (비율 유지)"""
    w, h = img.size
    ratio = target_h / h
    new_w = max(1, int(w * ratio))
    return img.resize((new_w, target_h), Image.LANCZOS)


def create_walk_frame2(img):
    """하반신(다리)을 좌우 반전해서 발바꿈 프레임 생성"""
    w, h = img.size
    split_y = int(h * 0.52)

    upper = img.crop((0, 0, w, split_y))
    lower = img.crop((0, split_y, w, h))

    lower_flipped = lower.transpose(Image.FLIP_LEFT_RIGHT)

    result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    result.paste(upper, (0, 0), upper)
    result.paste(lower_flipped, (0, split_y), lower_flipped)
    return result


def process_mario_running():
    """달리는 마리오 -> 걷기/달리기/점프 스프라이트"""
    print("=== 달리는 마리오 처리 ===")
    src = os.path.join(SRC_DIR, "KakaoTalk_Photo_2026-04-14-16-40-12.jpeg")
    img = Image.open(src)

    clean = remove_bg(img, tolerance=42)
    clean = trim(clean)

    # --- 달리기 ---
    run_right = resize_h(clean, TARGET_HEIGHT)
    run_left = run_right.transpose(Image.FLIP_LEFT_RIGHT)

    # --- 걷기 (2프레임 발바꿈) ---
    walk_right1 = run_right.copy()
    walk_right2 = create_walk_frame2(run_right)
    walk_left1 = run_left.copy()
    walk_left2 = create_walk_frame2(run_left)

    # --- 점프 (살짝 회전 + 위로 올린 포즈) ---
    jump_base = clean.rotate(-10, expand=True, resample=Image.BICUBIC)
    jump_base = trim(jump_base)
    jump = resize_h(jump_base, TARGET_HEIGHT)

    sprites = {
        "mario_run_right.png": run_right,
        "mario_run_left.png": run_left,
        "mario_walk_right1.png": walk_right1,
        "mario_walk_right2.png": walk_right2,
        "mario_walk_left1.png": walk_left1,
        "mario_walk_left2.png": walk_left2,
        "mario_jump_new.png": jump,
    }

    for name, sprite in sprites.items():
        path = os.path.join(DST_DIR, name)
        sprite.save(path)
        print(f"  {name}: {sprite.size}")

    return sprites


def process_mario_standing():
    """서 있는 마리오 -> 정면/좌우 스프라이트"""
    print("\n=== 서 있는 마리오 처리 ===")
    src = os.path.join(SRC_DIR, "KakaoTalk_Photo_2026-04-14-16-40-06.jpeg")
    img = Image.open(src)

    # 복잡한 배경 (하늘+구름+벽돌) -> 다단계 제거
    clean = remove_bg_multi(img, tolerances=[25, 35, 50])
    clean = trim(clean)

    stand = resize_h(clean, TARGET_HEIGHT)
    stand_mirror = stand.transpose(Image.FLIP_LEFT_RIGHT)

    stand.save(os.path.join(DST_DIR, "mario_stand.png"))
    stand_mirror.save(os.path.join(DST_DIR, "mario_stand_mirror.png"))

    print(f"  mario_stand.png: {stand.size}")
    print(f"  mario_stand_mirror.png: {stand_mirror.size}")


def process_flag():
    """깃발 스프라이트"""
    print("\n=== 깃발 처리 ===")
    src = os.path.join(SRC_DIR, "KakaoTalk_Photo_2026-04-14-16-40-08.jpeg")
    img = Image.open(src)

    clean = remove_bg(img, tolerance=50)
    clean = trim(clean)

    flag = resize_h(clean, 60)
    flag.save(os.path.join(DST_DIR, "flag_mario.png"))
    print(f"  flag_mario.png: {flag.size}")


def process_flagpoles():
    """깃대 3종 (쿠파/마리오/해골)"""
    print("\n=== 깃대 처리 ===")
    src = os.path.join(SRC_DIR, "KakaoTalk_Photo_2026-04-14-16-40-10.jpeg")
    img = Image.open(src)

    clean = remove_bg(img, tolerance=50)

    w, h = clean.size
    third = w // 3
    poles = [
        ("flagpole_bowser.png", clean.crop((0, 0, third, h))),
        ("flagpole_mario.png", clean.crop((third, 0, third*2, h))),
        ("flagpole_skull.png", clean.crop((third*2, 0, w, h))),
    ]

    for name, pole in poles:
        trimmed = trim(pole)
        resized = resize_h(trimmed, 120)
        resized.save(os.path.join(DST_DIR, name))
        print(f"  {name}: {resized.size}")


def process_background():
    """배경 -> Scratch 스테이지 크기 (480x360)"""
    print("\n=== 배경 처리 ===")
    src = os.path.join(SRC_DIR, "wp1907519-mario-bros-wallpapers.jpg")
    img = Image.open(src)

    bg = img.resize((480, 360), Image.LANCZOS)
    bg.save(os.path.join(DST_DIR, "background_stage.png"))
    print(f"  background_stage.png: {bg.size}")


if __name__ == "__main__":
    os.makedirs(DST_DIR, exist_ok=True)

    process_mario_running()
    process_mario_standing()
    process_flag()
    process_flagpoles()
    process_background()

    # 결과 요약
    print("\n" + "="*50)
    print("생성 완료! sprites_new/ 디렉토리 확인:")
    generated = [f for f in os.listdir(DST_DIR) if f.endswith('.png')]
    for f in sorted(generated):
        img = Image.open(os.path.join(DST_DIR, f))
        print(f"  {f}: {img.size[0]}x{img.size[1]} ({img.mode})")
