# main.py (root: maze-puzzle)
import random
import ctypes
import pygame as pg
from collections import deque

# 기본 변수(색상, 키 등)
WHITE, BLACK, GREEN, BLUE, RED, GRAY = (255,255,255), (0,0,0), (0,255,0), (0,0,255), (220,0,0), (240,240,240)
BASE_CELL = 72
MARGIN = 6
FPS = 60
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"
KEYS_DIR = {pg.K_UP:"N", pg.K_w:"N", pg.K_RIGHT:"E", pg.K_d:"E",
            pg.K_DOWN:"S", pg.K_s:"S", pg.K_LEFT:"W", pg.K_a:"W"}
DIRS = {"N":(-1,0), "E":(0,1), "S":(1,0), "W":(0,-1)}
OPP  = {"N":"S","S":"N","E":"W","W":"E"}

# 메시지 박스 설정
MB_OK = 0x00000000
MB_ICONINFO = 0x00000040
MB_TOPMOST = 0x00040000
MB_SETFOREGROUND = 0x00010000
def win_msgbox(text, title="미로 퍼즐"):
    ctypes.windll.user32.MessageBoxW(None, text, title,
        MB_OK | MB_ICONINFO | MB_TOPMOST | MB_SETFOREGROUND)

# 미로 생성
def add(doors, r, c, d):
    R, C = len(doors), len(doors[0])
    dr, dc = DIRS[d]; nr, nc = r+dr, c+dc
    if 0<=nr<R and 0<=nc<C:
        doors[r][c].add(d); doors[nr][nc].add(OPP[d])

# 문 생성
def gen_doors(R, C):
    doors = [[set() for _ in range(C)] for _ in range(R)]
    p = 0.22
    for r in range(R):
        for c in range(C):
            for d,(dr,dc) in DIRS.items():
                nr, nc = r+dr, c+dc
                if 0<=nr<R and 0<=nc<C and random.random()<p:
                    add(doors, r, c, d)
    # 2~4개 보정
    changed = True
    while changed:
        changed = False
        for r in range(R):
            for c in range(C):
                cnt = len(doors[r][c])
                while cnt < 2:
                    cand = [d for d,(dr,dc) in DIRS.items()
                            if 0<=r+dr<R and 0<=c+dc<C and d not in doors[r][c]
                            and len(doors[r+dr][c+dc]) < 4]
                    if not cand: break
                    add(doors, r, c, random.choice(cand)); cnt += 1; changed = True
                while cnt > 4:
                    d = random.choice(tuple(doors[r][c]))
                    dr,dc = DIRS[d]; nr,nc = r+dr,c+dc
                    if len(doors[nr][nc]) > 2:
                        doors[r][c].remove(d); doors[nr][nc].remove(OPP[d])
                        cnt -= 1; changed = True
    return doors

# 탈출구가 닿을 수 있는 위치인지 검사
def bfs_reachable(doors, start):
    R, C = len(doors), len(doors[0])
    q = deque([tuple(start)]); seen = {tuple(start)}
    while q:
        r,c = q.popleft()
        for d in doors[r][c]:
            dr,dc = DIRS[d]; nr,nc = r+dr,c+dc
            if (nr,nc) not in seen:
                seen.add((nr,nc)); q.append((nr,nc))
    return seen

# 탈출구가 시작 지점과 그 주변 칸으로부터 직선 경로 내에 있는 지 검사
def straight_connected(doors, start, goal):
    r0, c0 = start
    r1, c1 = goal
    if r0 == r1:  # 같은 행
        step = 1 if c1 > c0 else -1
        for c in range(c0, c1, step):
            if step == 1:
                if "E" not in doors[r0][c] or "W" not in doors[r0][c+1]:
                    return False
            else:
                if "W" not in doors[r0][c] or "E" not in doors[r0][c-1]:
                    return False
        return True
    if c0 == c1:  # 같은 열
        step = 1 if r1 > r0 else -1
        for r in range(r0, r1, step):
            if step == 1:
                if "S" not in doors[r][c0] or "N" not in doors[r+1][c0]:
                    return False
            else:
                if "N" not in doors[r][c0] or "S" not in doors[r-1][c0]:
                    return False
        return True
    return False

def ortho_neighbors_in_bounds(R, C, r, c):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0<=nr<R and 0<=nc<C:
            yield (nr, nc)

# 시작 지점과 탈출구를 생성한 칸 내에서 선택
def pick_start_exit(doors):
    R, C = len(doors), len(doors[0])
    while True:
        start = [random.randrange(R), random.randrange(C)]
        reach = bfs_reachable(doors, start)

        # 시작점으로부터 이웃하는 8칸 내 탈출구 생성 금지
        banned = {(start[0]+dr, start[1]+dc) for dr in (-1,0,1) for dc in (-1,0,1)}

        # 추가 조건: 시작점과 그 상하좌우 이웃들 중 어느 곳에서도
        # 탈출까지 "직선"으로 연결되어 있으면 후보에서 제외
        straight_origins = [(start[0], start[1])]
        straight_origins.extend(list(ortho_neighbors_in_bounds(R, C, start[0], start[1])))

        def violates_straight(p):
            for s in straight_origins:
                if straight_connected(doors, s, p):
                    return True
            return False

        candidates = [p for p in reach
                      if p not in banned and not violates_straight(p)]
        if candidates:
            return start, list(random.choice(candidates))

        # 조건 만족 후보 없으면 미로 재생성
        doors[:] = gen_doors(R, C)

# 줌 기능(휠 스크롤)
def zoom_limits(diff): return 0 if diff=="easy" else (1 if diff=="normal" else 2)
def vis_size(diff, zoom):
    if zoom==0: return None
    if diff=="normal": return (3,3)
    if diff=="hard": return (5,5) if zoom==1 else (3,3)
    return None
def compute_view(R, C, player, diff, zoom):
    size = vis_size(diff, zoom)
    if size is None: return 0, 0, R, C
    h, w = size
    r0 = max(0, min(player[0]-h//2, R-h))
    c0 = max(0, min(player[1]-w//2, C-w))
    return r0, c0, h, w

# 미로/탈출구 깃발 드로잉
def draw_flag(screen, x0, y0, cell):
    pole_w = max(2, cell//16)
    pg.draw.rect(screen, BLACK, pg.Rect(x0+cell//4, y0+cell//4, pole_w, cell//2))
    pts = [(x0+cell//4+pole_w, y0+cell//4),
           (x0+cell*3//4,     y0+cell//3),
           (x0+cell//4+pole_w, y0+cell//2)]
    pg.draw.polygon(screen, RED, pts)

def draw_scene(screen, doors, player, exit_pos, diff, zoom):
    R, C = len(doors), len(doors[0])
    r0, c0, h, w = compute_view(R, C, player, diff, zoom)
    W, H = screen.get_size()
    cell = min(W//w, H//h) if (h,w)!=(R,C) else BASE_CELL
    door_len = cell//3
    screen.fill(WHITE)
    pg.draw.rect(screen, GRAY, pg.Rect(0,0,w*cell,h*cell))
    for i in range(h+1):
        y = i*cell; pg.draw.line(screen, BLACK, (0,y), (w*cell,y), 2)
    for j in range(w+1):
        x = j*cell; pg.draw.line(screen, BLACK, (x,0), (x,h*cell), 2)
    for vr in range(h):
        for vc in range(w):
            r, c = r0+vr, c0+vc
            x0, y0 = vc*cell, vr*cell
            cx, cy = x0+cell//2, y0+cell//2
            if "N" in doors[r][c] and r>0:   pg.draw.rect(screen, GREEN, pg.Rect(cx-door_len//2, y0-MARGIN//2, door_len, MARGIN))
            if "S" in doors[r][c] and r<R-1: pg.draw.rect(screen, GREEN, pg.Rect(cx-door_len//2, y0+cell-MARGIN//2, door_len, MARGIN))
            if "W" in doors[r][c] and c>0:   pg.draw.rect(screen, GREEN, pg.Rect(x0-MARGIN//2, cy-door_len//2, MARGIN, door_len))
            if "E" in doors[r][c] and c<C-1: pg.draw.rect(screen, GREEN, pg.Rect(x0+cell-MARGIN//2, cy-door_len//2, MARGIN, door_len))
    if r0 <= exit_pos[0] < r0+h and c0 <= exit_pos[1] < c0+w:
        er, ec = exit_pos[0]-r0, exit_pos[1]-c0
        ex, ey = ec*cell, er*cell
        draw_flag(screen, ex, ey, cell)
    if r0 <= player[0] < r0+h and c0 <= player[1] < c0+w:
        pr, pc = player[0]-r0, player[1]-c0
        x0, y0 = pc*cell, pr*cell
        size = cell//2
        pg.draw.rect(screen, BLUE, pg.Rect(x0+cell//2-size//2, y0+cell//2-size//2, size, size))
    pg.display.flip()

# 캐릭터 이동
def move(player, doors, want):
    r,c = player
    if want in doors[r][c]:
        dr,dc = DIRS[want]; nr, nc = r+dr, c+dc
        R, C = len(doors), len(doors[0])
        if 0<=nr<R and 0<=nc<C: player[0], player[1] = nr, nc

# 초기 화면 메뉴
def menu(screen):
    W,H = screen.get_size()
    title_font = pg.font.Font(FONT_PATH, 56)
    line_font  = pg.font.Font(FONT_PATH, 28)
    sub_font   = pg.font.Font(FONT_PATH, 22)
    choices = [("쉬움", "4×4", (4,4,"easy")),
               ("보통", "6×6", (6,6,"normal")),
               ("어려움", "9×9", (9,9,"hard"))]
    col_w = W//3
    boxes = [pg.Rect(i*col_w+col_w//8, H//2-40, col_w*3//4, 150) for i in range(3)]

    while True:
        screen.fill(WHITE)
        title = title_font.render("난이도 선택", True, BLACK)
        screen.blit(title, (W//2 - title.get_width()//2, H//6))
        for i,(name, sub, _) in enumerate(choices):
            r = boxes[i]
            pg.draw.rect(screen, BLACK, r, 3)
            t1 = line_font.render(name, True, BLACK)
            t2 = sub_font.render(f"({sub})", True, BLACK)
            screen.blit(t1, (r.centerx - t1.get_width()//2, r.top + 28))
            screen.blit(t2, (r.centerx - t2.get_width()//2, r.top + 72))
        pg.display.flip()

        for e in pg.event.get():
            if e.type == pg.QUIT: return None
            if e.type == pg.MOUSEBUTTONDOWN and e.button==1:
                for i,r in enumerate(boxes):
                    if r.collidepoint(e.pos): return choices[i][2]
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_1, pg.K_KP1): return choices[0][2]
                if e.key in (pg.K_2, pg.K_KP2): return choices[1][2]
                if e.key in (pg.K_3, pg.K_KP3): return choices[2][2]

# 메인 작동 코드
def main():
    pg.init()
    pg.display.set_caption("미로 퍼즐")
    icon = pg.Surface((32,32)); icon.fill(WHITE)
    pg.draw.rect(icon, BLUE, pg.Rect(8,8,16,16)); pg.draw.rect(icon, GREEN, pg.Rect(0,15,32,2))
    pg.display.set_icon(icon)

    screen = pg.display.set_mode((720, 540))

    while True:
        sel = menu(screen)
        if sel is None: break
        R,C,diff = sel

        # 게임 준비
        screen = pg.display.set_mode((C*BASE_CELL, R*BASE_CELL))
        doors = gen_doors(R,C)
        player, exit_pos = pick_start_exit(doors)
        start_pos = player.copy()
        max_zoom = zoom_limits(diff); zoom = 0
        clock = pg.time.Clock()
        pressed = set()
        HOLD_MS = 2000
        r_hold_start = None; r_trig = False
        q_hold_start = None; q_trig = False

        # 조작법 메시지박스
        win_msgbox("조작법\n"
                   "이동: 화살표 / WASD\n"
                   "R 3초: 캐릭터 위치 리셋\n"
                   "Q 3초: 맵과 캐릭터 위치 리셋\n"
                   "휠: 확대/축소(보통/어려움 난이도만)")

        running = True
        while running:
            now = pg.time.get_ticks()
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    running = False; return
                elif e.type == pg.KEYDOWN:
                    if e.key in KEYS_DIR and e.key not in pressed:
                        move(player, doors, KEYS_DIR[e.key]); pressed.add(e.key)
                    if e.key == pg.K_r and r_hold_start is None: r_hold_start = now; r_trig = False
                    if e.key == pg.K_q and q_hold_start is None: q_hold_start = now; q_trig = False
                elif e.type == pg.KEYUP:
                    if e.key in pressed: pressed.remove(e.key)
                    if e.key == pg.K_r: r_hold_start = None; r_trig = False
                    if e.key == pg.K_q: q_hold_start = None; q_trig = False
                elif e.type == pg.MOUSEWHEEL and max_zoom>0:
                    zoom = min(max(0, zoom + (1 if e.y>0 else -1)), max_zoom)

            if r_hold_start is not None and not r_trig and now - r_hold_start >= HOLD_MS:
                player[:] = start_pos; r_trig = True
            if q_hold_start is not None and not q_trig and now - q_hold_start >= HOLD_MS:
                doors = gen_doors(R,C)
                player, exit_pos = pick_start_exit(doors)
                start_pos = player.copy()
                zoom = 0
                q_trig = True

            draw_scene(screen, doors, player, exit_pos, diff, zoom)

            # 탈출 시 메시지박스로 안내 후 메뉴 복귀
            if player[0]==exit_pos[0] and player[1]==exit_pos[1]:
                win_msgbox("탈출에 성공했습니다.\n확인을 누르면 초기 화면으로 돌아갑니다.")
                running = False
                screen = pg.display.set_mode((720, 540))
                break

            clock.tick(FPS)

if __name__ == "__main__":
    main()
