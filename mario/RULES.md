# 프로젝트 개발 룰

## 1. Spec-First Development (최우선 룰)

수정 요청 시 반드시 다음 순서로 진행:

1. **specs/ 문서 먼저 수정** (캐릭터별 폴더: mario/, turtle/, platform/, stage/)
2. **코드 변경** (mechanics.py 또는 generate_stageN.py)
3. **sb3 재생성** (3개 스테이지 모두 python3 generate_stageN.py 실행)

spec과 코드가 항상 일치하는 상태를 유지한다.

## 2. Sprites 관리

- 사용 중인 스프라이트만 `sprites/` 폴더에 캐릭터별로 보관
- 미사용 스프라이트는 `sprites/archives/`에 보관
- 새 스프라이트 추가 시 해당 캐릭터 폴더에 배치

### 캐릭터-폴더 매핑
| 게임 캐릭터 | 폴더 | 비고 |
|------------|------|------|
| 배경/발판 | `background/` | bg_stage.png, plat_3.png |
| 마리오 | `mario/` | walk, jump 스프라이트 |
| 거북이 | `turtle/` | Stage 1 순찰 거북이 |
| 쿠파 | `koopa/` | Stage 2 등껍질, Stage 3 보스 |
| 피치 | `peach/` | Stage 3 구출 대상 |

### 현재 사용 중인 스프라이트
```
sprites/
├── background/            # 배경/발판
│   ├── bg_stage.png
│   └── plat_3.png
├── mario/                 # 마리오
│   ├── mario3_walk_1.png
│   ├── mario3_walk_3.png
│   ├── mario3_walk_4.png
│   ├── mario3_walk_5.png
│   ├── mario3_walk_6.png
│   ├── mario3_jump_5.png
│   ├── mario3_jump_6.png  # (인트로 전용)
│   └── mario3_jump_7.png  # (인트로 전용)
├── turtle/                # 거북이 (Stage 1)
│   └── koopa_walk_1.png
├── koopa/                 # 쿠파 (Stage 2 등껍질 + Stage 3 보스)
│   ├── bowser_stand_1.png
│   └── bowser_walk_1.png
└── peach/                 # 피치
    └── peach_idle.png
```
