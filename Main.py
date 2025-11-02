import pygame
import sys
import random
from level import level_map, TILE_SIZE

pygame.init()
screen = pygame.display.set_mode((1200, 700))
pygame.display.set_caption("Tarzan in the Lost Jungle")
clock = pygame.time.Clock()

# === Load Background ===
original_sky = pygame.image.load('assets/images/background/sky.jpg').convert()
scale_factor = 640 / original_sky.get_height()
new_width = int(original_sky.get_width() * scale_factor)
sky_image = pygame.transform.scale(original_sky, (new_width, 640))

# === Fonts and UI ===
font = pygame.font.SysFont('Venite Adoremus', 30)
score = 0
lives = 3
game_over = False

MENU, PLAYING = 'menu', 'playing'
state = MENU
transition_alpha = 255
transitioning = False

# === UI Images ===
pause_img = pygame.image.load("assets/images/objects/pause.png").convert_alpha()
pause_img = pygame.transform.scale(pause_img, (60, 60))
pause_rect = pause_img.get_rect(topright=(1180, 20))

score_panel_img = pygame.image.load("assets/images/ui/score_panel.png").convert_alpha()
score_panel_img = pygame.transform.scale(score_panel_img, (330, 140))
score_panel_rect = score_panel_img.get_rect(topleft=(-5, 10))


# === Utility Functions ===
def blur_surface(surface, scale_factor=0.1):
    w, h = surface.get_size()
    small = pygame.transform.smoothscale(surface, (int(w * scale_factor), int(h * scale_factor)))
    return pygame.transform.smoothscale(small, (w, h))


def draw_button(surface, rect, text, font, bg_color, text_color):
    pygame.draw.rect(surface, bg_color, rect, border_radius=15)
    pygame.draw.rect(surface, (0, 0, 0), rect, 2, border_radius=15)
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)


def draw_text_with_stroke(surface, text, font, x, y, text_color, stroke_color, stroke_width=2):
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx != 0 or dy != 0:
                outline = font.render(text, True, stroke_color)
                surface.blit(outline, (x + dx, y + dy))
    text_surface = font.render(text, True, text_color)
    surface.blit(text_surface, (x, y))


# === Game Object Classes ===
class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, kind='middle'):
        super().__init__()
        tile_files = {
            'left': 'tile_left.png',
            'middle': 'tile_middle.png',
            'right': 'tile_right.png'
        }
        base_image = pygame.image.load(f'assets/images/tiles/{tile_files[kind]}').convert_alpha()
        base_image = pygame.transform.scale(base_image, (TILE_SIZE, TILE_SIZE))
        self.image = base_image
        self.rect = self.image.get_rect(topleft=(x, y))


class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.original_image = pygame.image.load('assets/images/objects/coin.png').convert_alpha()
        self.image = pygame.transform.scale(self.original_image, (TILE_SIZE // 2, TILE_SIZE // 2))
        self.rect = self.image.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
        self.flip = False
        self.flip_timer = 0

    def update(self):
        self.flip_timer += 1
        if self.flip_timer >= 10:
            self.flip = not self.flip
            self.flip_timer = 0
            flipped_image = pygame.transform.flip(self.original_image, True, False)
            self.image = pygame.transform.scale(flipped_image if self.flip else self.original_image,
                                                (TILE_SIZE // 2, TILE_SIZE // 2))
            old_center = self.rect.center
            self.rect = self.image.get_rect()
            self.rect.center = old_center


class Tree(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        tree_image_file = random.choice(['T1.png', 'T2.png', 'T3.png'])
        original = pygame.image.load(f'assets/images/objects/{tree_image_file}').convert_alpha()
        self.image = pygame.transform.scale(original, (TILE_SIZE * 2, TILE_SIZE * 2))
        self.rect = self.image.get_rect(midbottom=(x + TILE_SIZE // 2, y + TILE_SIZE + 12))


class Rock(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        rock_image_file = random.choice(['R1.png', 'R2.png', 'R3.png'])
        original = pygame.image.load(f'assets/images/objects/{rock_image_file}').convert_alpha()
        self.image = pygame.transform.scale(original, (TILE_SIZE * 2, TILE_SIZE * 2))
        self.rect = self.image.get_rect(midbottom=(x + TILE_SIZE // 2, y + TILE_SIZE + 14))


class Inter_tile(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        original = pygame.image.load('assets/images/tiles/tile_inter.png').convert_alpha()
        self.image = pygame.transform.scale(original, (TILE_SIZE, int(TILE_SIZE * 1.1)))
        self.rect = self.image.get_rect(midbottom=(x + TILE_SIZE // 2, y + TILE_SIZE + 3))


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, tiles):
        super().__init__()
        self.tiles = tiles
        self.vel = pygame.Vector2(0, 0)
        self.on_ground = False
        self.last_hit_time = 0
        self.invincible_duration = 1500

        self.width = int(TILE_SIZE * 1.1)
        self.height = int(TILE_SIZE * 1.5)

        self.images = {
            "idle": pygame.transform.scale(pygame.image.load("assets/images/player/player.png").convert_alpha(), (self.width, self.height)),
            "walk1": pygame.transform.scale(pygame.image.load("assets/images/player/player_w1.png").convert_alpha(), (self.width, self.height)),
            "walk2": pygame.transform.scale(pygame.image.load("assets/images/player/player_w2.png").convert_alpha(), (self.width, self.height)),
        }

        self.image = self.images["idle"]
        self.rect = self.image.get_rect(topleft=(x, y + 5))
        self.walk_index = 0
        self.walk_timer = 0

    def input(self):
        keys = pygame.key.get_pressed()
        self.vel.x = 0
        if keys[pygame.K_LEFT]:
            self.vel.x = -5
        if keys[pygame.K_RIGHT]:
            self.vel.x = 5
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel.y = -12
            self.on_ground = False

    def apply_gravity(self):
        self.vel.y += 0.5
        self.rect.y += self.vel.y

    def animate(self):
        if self.vel.x != 0:
            self.walk_timer += 1
            if self.walk_timer >= 10:
                self.walk_index = (self.walk_index + 1) % 2
                self.walk_timer = 0
            self.image = self.images["walk1"] if self.walk_index == 0 else self.images["walk2"]
            if self.vel.x < 0:
                self.image = pygame.transform.flip(self.image, True, False)
        else:
            self.image = self.images["idle"]

    def update(self):
        self.input()
        self.rect.x += self.vel.x
        self.check_collision("x")
        self.apply_gravity()
        self.check_collision("y")
        self.animate()

    def check_collision(self, dir):
        for tile in self.tiles:
            if self.rect.colliderect(tile.rect):
                if dir == "x":
                    if self.vel.x > 0:
                        self.rect.right = tile.rect.left
                    if self.vel.x < 0:
                        self.rect.left = tile.rect.right
                if dir == "y":
                    if self.vel.y > 0:
                        self.rect.bottom = tile.rect.top
                        self.vel.y = 0
                        self.on_ground = True
                    elif self.vel.y < 0:
                        self.rect.top = tile.rect.bottom
                        self.vel.y = 0


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, tiles):
        super().__init__()
        self.image1 = pygame.transform.scale(pygame.image.load('assets/images/enemies/enemy_w3.png').convert_alpha(), (int(TILE_SIZE * 1.2), int(TILE_SIZE * 1.5)))
        self.image2 = pygame.transform.scale(pygame.image.load('assets/images/enemies/enemy_w2.png').convert_alpha(), (int(TILE_SIZE), int(TILE_SIZE * 1.5)))

        self.images = [self.image1, self.image2]
        self.image = self.images[0]
        self.rect = self.image.get_rect(topleft=(x, y - 30))
        self.direction = -1
        self.facing_right = False
        self.tiles = tiles

        self.walk_index = 0
        self.walk_timer = 0

    def update(self):
        self.rect.x += self.direction
        self.rect.y += 1
        on_tile = any(tile.rect.colliderect(self.rect.move(0, 1)) for tile in self.tiles)
        self.rect.y -= 1

        front_rect = self.rect.move(self.direction * TILE_SIZE // 2, 1)
        front_tile = any(tile.rect.colliderect(front_rect) for tile in self.tiles)

        if not on_tile or not front_tile:
            self.direction *= -1

        if self.direction > 0 and not self.facing_right:
            self.images = [pygame.transform.flip(img, True, False) for img in self.images]
            self.facing_right = True
        elif self.direction < 0 and self.facing_right:
            self.images = [pygame.transform.flip(img, True, False) for img in self.images]
            self.facing_right = False

        self.walk_timer += 1
        if self.walk_timer >= 10:
            self.walk_index = (self.walk_index + 1) % len(self.images)
            self.walk_timer = 0

        self.image = self.images[self.walk_index]


# === Level Builder ===
def build_level():
    tiles = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    rocks = pygame.sprite.Group()
    trees = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    inter_tiles = pygame.sprite.Group()
    player = None

    for row_idx, row in enumerate(level_map):
        for col_idx, cell in enumerate(row):
            x, y = col_idx * TILE_SIZE, row_idx * TILE_SIZE
            if cell == "#":
                left = row[col_idx - 1] if col_idx > 0 else " "
                right = row[col_idx + 1] if col_idx < len(row) - 1 else " "
                if left != "#" and right == "#":
                    kind = 'left'
                elif left == "#" and right != "#":
                    kind = 'right'
                else:
                    kind = 'middle'
                tiles.add(Tile(x, y, kind))
            elif cell == "P":
                player = Player(x, y, tiles)
            elif cell == "E":
                enemies.add(Enemy(x, y, tiles))
            elif cell == "C":
                coins.add(Coin(x, y))
            elif cell == "T":
                trees.add(Tree(x, y))
            elif cell == "R":
                rocks.add(Rock(x, y))
            elif cell == "I":
                inter_tiles.add(Inter_tile(x, y))

    return tiles, coins, player, enemies, trees, rocks, inter_tiles


# === Game Initialization ===
tiles, coins, player, enemies, trees, rocks, inter_tiles = build_level()
scroll_x = 0

# === Game Loop ===
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if state == MENU and event.type == pygame.MOUSEBUTTONDOWN:
            if 500 <= event.pos[0] <= 700 and 300 <= event.pos[1] <= 360:
                transitioning = True

        if state == PLAYING and event.type == pygame.MOUSEBUTTONDOWN:
            if pause_rect.collidepoint(event.pos):
                state = MENU

    if transitioning:
        transition_alpha -= 5
        if transition_alpha <= 0:
            state = PLAYING
            transitioning = False
            transition_alpha = 255

    if state == PLAYING and not game_over:
        player.update()
        enemies.update()
        coins.update()

        scroll_x = max(0, player.rect.centerx - 400)

        for coin in coins:
            if player.rect.colliderect(coin.rect):
                coin.kill()
                score += 1

        for enemy in enemies:
            if player.rect.colliderect(enemy.rect):
                if player.vel.y > 0 and player.rect.bottom - enemy.rect.top < 20:
                    enemy.kill()
                    player.vel.y = -8
                    score += 5
                elif pygame.time.get_ticks() - player.last_hit_time > player.invincible_duration:
                    lives -= 1
                    player.last_hit_time = pygame.time.get_ticks()
                    if lives <= 0:
                        game_over = True

        if player.rect.top > screen.get_height():
            lives -= 1
            if lives <= 0:
                game_over = True
            else:
                player.rect.topleft = (100, 100)
                player.vel = pygame.Vector2(0, 0)

    max_scroll = sky_image.get_width() - screen.get_width()
    scroll_x_clamped = max(0, min(scroll_x, max_scroll))
    screen.blit(sky_image, (-scroll_x_clamped, 0))

    for group in [trees, tiles, coins, rocks, inter_tiles, enemies]:
        for sprite in group:
            screen.blit(sprite.image, (sprite.rect.x - scroll_x, sprite.rect.y))
    screen.blit(player.image, (player.rect.x - scroll_x, player.rect.y))

    if state == PLAYING:
        screen.blit(score_panel_img, score_panel_rect)
        draw_text_with_stroke(screen, f"Score: {score}", font, 130, 50, (255, 255, 255), (0, 0, 0), stroke_width=2)
        draw_text_with_stroke(screen, f"Lives: {lives}", font, 130, 80, (255, 255, 255), (0, 0, 0), stroke_width=2)
        screen.blit(pause_img, pause_rect)

    if state == MENU:
        blurred = blur_surface(screen)
        screen.blit(blurred, (0, 0))
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))
        title = font.render("Tarzan in the Lost Jungle", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(600, 150)))
        if game_over:
            draw_button(screen, pygame.Rect(400, 300, 400, 80), "Restart Game", font, (255, 255, 255), (0, 0, 0))
        else:
            draw_button(screen, pygame.Rect(400, 300, 400, 80), "Start Game", font, (255, 255, 255), (0, 0, 0))

    if transitioning:
        transition_overlay = pygame.Surface(screen.get_size())
        transition_overlay.fill((0, 0, 0))
        transition_overlay.set_alpha(transition_alpha)
        screen.blit(transition_overlay, (0, 0))

    pygame.display.flip()
    clock.tick(60)
