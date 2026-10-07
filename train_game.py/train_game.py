import pygame
import sys

# -----------------
# 初期設定
# -----------------
pygame.init()

WIDTH = 1000
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("EF81 Freight Train")

clock = pygame.time.Clock()

# -----------------
# 色
# -----------------
SKY = (120, 190, 255)
GRASS = (70, 170, 70)
TRACK = (90, 90, 90)
RAIL = (180, 180, 180)

EF81_RED = (180, 30, 30)
YELLOW = (240, 220, 80)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# -----------------
# 背景スクロール
# -----------------
bg_x = 0
speed = 4

# -----------------
# EF81描画
# -----------------
def draw_ef81(x, y):

    # 車体
    pygame.draw.rect(screen, EF81_RED, (x, y, 140, 60))

    # 屋根
    pygame.draw.rect(screen, (140, 20, 20), (x + 5, y - 8, 130, 8))

    # 前面
    pygame.draw.rect(screen, EF81_RED, (x - 15, y + 10, 20, 40))

    # 窓
    pygame.draw.rect(screen, BLACK, (x + 20, y + 12, 25, 18))
    pygame.draw.rect(screen, BLACK, (x + 50, y + 12, 25, 18))

    # ライト
    pygame.draw.circle(screen, YELLOW, (x - 5, y + 20), 4)
    pygame.draw.circle(screen, YELLOW, (x - 5, y + 40), 4)

    # ライン
    pygame.draw.rect(screen, YELLOW, (x, y + 35, 140, 5))

    # 車輪
    for i in range(4):
        pygame.draw.circle(screen, BLACK, (x + 20 + i * 35, y + 65), 10)

# -----------------
# 貨車
# -----------------
def draw_container_car(x, y):

    pygame.draw.rect(screen, (60, 60, 60), (x, y + 25, 120, 20))

    pygame.draw.rect(screen, (30, 90, 180), (x + 10, y - 5, 45, 30))
    pygame.draw.rect(screen, (180, 60, 60), (x + 60, y - 5, 45, 30))

    pygame.draw.circle(screen, BLACK, (x + 20, y + 50), 8)
    pygame.draw.circle(screen, BLACK, (x + 100, y + 50), 8)

# -----------------
# 背景
# -----------------
def draw_background(offset):

    screen.fill(SKY)

    # 山
    for i in range(-1, 6):
        mx = i * 250 - (offset * 0.2 % 250)

        pygame.draw.polygon(
            screen,
            (80, 130, 80),
            [
                (mx, 350),
                (mx + 125, 200),
                (mx + 250, 350)
            ]
        )

    # 草原
    pygame.draw.rect(screen, GRASS, (0, 350, WIDTH, 250))

    # 電柱
    for i in range(-1, 15):
        px = i * 120 - (offset % 120)

        pygame.draw.rect(screen, (100, 80, 60), (px, 250, 6, 150))
        pygame.draw.line(screen, BLACK, (px, 260), (px + 40, 260), 2)

# -----------------
# 線路
# -----------------
def draw_track(offset):

    pygame.draw.rect(screen, TRACK, (0, 430, WIDTH, 80))

    pygame.draw.line(screen, RAIL, (0, 450), (WIDTH, 450), 4)
    pygame.draw.line(screen, RAIL, (0, 490), (WIDTH, 490), 4)

    for i in range(-1, 40):
        x = i * 30 - (offset % 30)

        pygame.draw.rect(screen, (120, 80, 50), (x, 445, 8, 50))

# -----------------
# メインループ
# -----------------
while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    bg_x += speed

    draw_background(bg_x)
    draw_track(bg_x)

    train_y = 385

    # EF81
    draw_ef81(250, train_y)

    # 貨車
    draw_container_car(420, train_y + 15)
    draw_container_car(560, train_y + 15)
    draw_container_car(700, train_y + 15)
    draw_container_car(840, train_y + 15)

    pygame.display.flip()

    clock.tick(60)