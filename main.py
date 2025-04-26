import pygame
import sys
import os
import random
import json
from pygame.locals import *

# Инициализация
pygame.init()
pygame.mixer.init()
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Epic Platformer Adventure")

# Константы
FPS = 60
GRAVITY = 0.5
JUMP_FORCE = -15
PLAYER_SPEED = 7
ATTACK_COOLDOWN = 500  # мс

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)

# Шрифты
font_small = pygame.font.Font(None, 24)
font_medium = pygame.font.Font(None, 36)
font_large = pygame.font.Font(None, 72)

class AssetManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.assets = {
            "images": {},
            "sounds": {},
            "music": {}
        }
        self._load_assets()
    
    def _load_assets(self):
        # Создаем папки если их нет
        os.makedirs("assets/images", exist_ok=True)
        os.makedirs("assets/sounds", exist_ok=True)
        os.makedirs("assets/music", exist_ok=True)
        
        # Загрузка изображений
        for char_type in ["warrior", "mage", "archer"]:
            self.assets["images"][f"{char_type}_idle"] = self._load_image(f"assets/images/{char_type}_idle.png", 2)
            self.assets["images"][f"{char_type}_run"] = self._load_image(f"assets/images/{char_type}_run.png", 2)
            self.assets["images"][f"{char_type}_jump"] = self._load_image(f"assets/images/{char_type}_jump.png", 2)
            self.assets["images"][f"{char_type}_attack"] = self._load_image(f"assets/images/{char_type}_attack.png", 2)
            self.assets["images"][f"{char_type}_death"] = self._load_image(f"assets/images/{char_type}_death.png", 2)
        
        # Загрузка звуков
        for sound in ["jump", "attack", "hurt", "coin", "victory"]:
            self.assets["sounds"][sound] = self._load_sound(f"assets/sounds/{sound}.wav")
        
        # Загрузка музыки
        for music in ["menu", "level1", "level2", "level3"]:
            self.assets["music"][music] = f"assets/music/{music}.mp3"
    
    def _load_image(self, path, scale=1):
        try:
            image = pygame.image.load(path).convert_alpha()
            if scale != 1:
                size = (int(image.get_width() * scale), int(image.get_height() * scale))
                return pygame.transform.scale(image, size)
            return image
        except:
            print(f"Error loading: {path}")
            surf = pygame.Surface((50, 50), pygame.SRCALPHA)
            surf.fill((random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)))
            return surf
    
    def _load_sound(self, path):
        try:
            return pygame.mixer.Sound(path)
        except:
            print(f"Error loading sound: {path}")
            return None
    
    def get_image(self, name):
        return self.assets["images"].get(name, None)
    
    def get_sound(self, name):
        return self.assets["sounds"].get(name, None)
    
    def play_music(self, name, loops=-1, volume=0.5):
        try:
            pygame.mixer.music.load(self.assets["music"][name])
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
        except:
            print(f"Error playing music: {name}")

class Animation:
    def __init__(self, frames, speed=0.1, loop=True):
        self.frames = frames
        self.speed = speed
        self.loop = loop
        self.current_frame = 0
        self.done = False
    
    def reset(self):
        self.current_frame = 0
        self.done = False
    
    def update(self):
        if not self.done:
            self.current_frame += self.speed
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.done = True
    
    def get_current_frame(self):
        return self.frames[int(self.current_frame)]

class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.animations = {}
        self.current_animation = None
        self.state = "idle"
        self.facing_right = True
        self.rect = pygame.Rect(x, y, 50, 80)
        self.velocity = pygame.math.Vector2(0, 0)
        self.health = 100
        self.max_health = 100
        self.attack_cooldown = 0
        self.attack_power = 10
        self.alive = True
    
    def set_animation(self, name):
        if name in self.animations and self.current_animation != self.animations[name]:
            self.current_animation = self.animations[name]
            self.current_animation.reset()
    
    def update_animation(self):
        if self.current_animation:
            self.current_animation.update()
            self.image = self.current_animation.get_current_frame()
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)
    
    def take_damage(self, amount):
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.set_animation("death")
                return True
        return False
    
    def update_cooldowns(self):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1000 / FPS

class Player(Entity):
    def __init__(self, x, y, char_type="warrior"):
        super().__init__(x, y)
        self.char_type = char_type
        self.load_animations()
        self.set_animation("idle")
        self.jumping = False
        self.attacking = False
        self.coins = 0
        self.score = 0
    
    def load_animations(self):
        asset_manager = AssetManager()
        
        # Загрузка анимаций для выбранного персонажа
        idle = asset_manager.get_image(f"{self.char_type}_idle")
        run = asset_manager.get_image(f"{self.char_type}_run")
        jump = asset_manager.get_image(f"{self.char_type}_jump")
        attack = asset_manager.get_image(f"{self.char_type}_attack")
        death = asset_manager.get_image(f"{self.char_type}_death")
        
        # Разделение спрайтшитов на кадры (в реальной игре загружайте отдельные файлы)
        def split_sprite(sprite, cols, rows):
            frames = []
            frame_width = sprite.get_width() // cols
            frame_height = sprite.get_height() // rows
            for row in range(rows):
                for col in range(cols):
                    frame = sprite.subsurface(pygame.Rect(
                        col * frame_width,
                        row * frame_height,
                        frame_width,
                        frame_height
                    ))
                    frames.append(frame)
            return frames
        
        self.animations = {
            "idle": Animation(split_sprite(idle, 4, 1), 0.1),
            "run": Animation(split_sprite(run, 6, 1), 0.15),
            "jump": Animation(split_sprite(jump, 1, 1), 0.1, False),
            "attack": Animation(split_sprite(attack, 4, 1), 0.2, False),
            "death": Animation(split_sprite(death, 4, 1), 0.15, False)
        }
    
    def update(self, platforms, enemies):
        if not self.alive:
            self.set_animation("death")
            self.update_animation()
            return
        
        # Физика
        self.velocity.y += GRAVITY
        self.rect.y += self.velocity.y
        
        # Коллизия с платформами
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.velocity.y > 0:  # Падение вниз
                    self.rect.bottom = platform.rect.top
                    self.velocity.y = 0
                    self.jumping = False
        
        # Определение состояния
        if self.attacking:
            self.set_animation("attack")
            if self.current_animation.done:
                self.attacking = False
        elif self.jumping:
            self.set_animation("jump")
        elif abs(self.velocity.x) > 0.1:
            self.set_animation("run")
        else:
            self.set_animation("idle")
        
        # Кулдаун атаки
        self.update_cooldowns()
        self.update_animation()
    
    def jump(self):
        if not self.jumping and not self.attacking and self.alive:
            self.velocity.y = JUMP_FORCE
            self.jumping = True
            AssetManager().get_sound("jump").play()
    
    def attack(self):
        if not self.attacking and self.attack_cooldown <= 0 and self.alive:
            self.attacking = True
            self.attack_cooldown = ATTACK_COOLDOWN
            self.set_animation("attack")
            AssetManager().get_sound("attack").play()
            return True
        return False
    
    def add_coin(self):
        self.coins += 1
        self.score += 100
        AssetManager().get_sound("coin").play()

class Enemy(Entity):
    def __init__(self, x, y, enemy_type="slime"):
        super().__init__(x, y)
        self.enemy_type = enemy_type
        self.load_animations()
        self.set_animation("idle")
        self.speed = 1.5
        self.direction = 1
        self.attack_range = 50
        self.detection_range = 300
    
    def load_animations(self):
        # Заглушка - в реальной игре загружайте спрайты
        idle = pygame.Surface((50, 50))
        run = pygame.Surface((50, 50))
        attack = pygame.Surface((60, 50))
        death = pygame.Surface((50, 50))
        
        idle.fill(RED)
        run.fill((200, 0, 0))
        attack.fill((255, 100, 100))
        death.fill((100, 0, 0))
        
        self.animations = {
            "idle": Animation([idle], 0.1),
            "run": Animation([run], 0.15),
            "attack": Animation([attack], 0.2, False),
            "death": Animation([death], 0.15, False)
        }
    
    def update(self, platforms, player):
        if not self.alive:
            self.set_animation("death")
            if self.current_animation.done:
                self.kill()
            self.update_animation()
            return
        
        # Простой ИИ
        if abs(self.rect.x - player.rect.x) < self.detection_range:
            self.direction = 1 if player.rect.x > self.rect.x else -1
        
        self.velocity.x = self.speed * self.direction
        self.rect.x += self.velocity.x
        
        # Коллизия с платформами
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.direction > 0:
                    self.rect.right = platform.rect.left
                else:
                    self.rect.left = platform.rect.right
                self.direction *= -1
        
        # Атака игрока
        if abs(self.rect.x - player.rect.x) < self.attack_range and self.attack_cooldown <= 0:
            self.set_animation("attack")
            if player.alive:
                player.take_damage(5)
                AssetManager().get_sound("hurt").play()
            self.attack_cooldown = ATTACK_COOLDOWN
        elif abs(self.velocity.x) > 0.1:
            self.set_animation("run")
        else:
            self.set_animation("idle")
        
        self.facing_right = self.direction > 0
        self.update_cooldowns()
        self.update_animation()

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color=GREEN):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=(x, y))
        self.value = 1

class GameState:
    def __init__(self):
        self.current_level = 1
        self.max_level = 3
        self.player_name = "Player"
        self.player_class = "warrior"
        self.highscores = self.load_highscores()
    
    def load_highscores(self):
        try:
            with open("highscores.json", "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_highscore(self, score):
        self.highscores.append({
            "name": self.player_name,
            "class": self.player_class,
            "score": score,
            "level": self.current_level
        })
        self.highscores.sort(key=lambda x: x["score"], reverse=True)
        self.highscores = self.highscores[:10]  # Топ-10
        
        with open("highscores.json", "w") as f:
            json.dump(self.highscores, f)
    
    def next_level(self):
        if self.current_level < self.max_level:
            self.current_level += 1
            return True
        return False

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
    
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=10)
        
        text_surf = font_medium.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
    
    def is_clicked(self, pos, click):
        return self.rect.collidepoint(pos) and click

def main_menu():
    game_state = GameState()
    asset_manager = AssetManager()
    asset_manager.play_music("menu")
    
    title = font_large.render("EPIC PLATFORMER", True, PURPLE)
    subtitle = font_medium.render("Выберите действие:", True, WHITE)
    
    buttons = [
        Button(WIDTH//2 - 100, HEIGHT//2 - 50, 200, 50, "Играть", BLUE, (0, 100, 255)),
        Button(WIDTH//2 - 100, HEIGHT//2 + 20, 200, 50, "Рекорды", GREEN, (0, 200, 100)),
        Button(WIDTH//2 - 100, HEIGHT//2 + 90, 200, 50, "Выход", RED, (200, 0, 0))
    ]
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True
        
        screen.fill(BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 200))
        
        for button in buttons:
            button.check_hover(mouse_pos)
            button.draw(screen)
            
            if button.is_clicked(mouse_pos, mouse_click):
                if button.text == "Играть":
                    character_select(game_state)
                elif button.text == "Рекорды":
                    show_highscores(game_state)
                elif button.text == "Выход":
                    pygame.quit()
                    sys.exit()
        
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)

def character_select(game_state):
    asset_manager = AssetManager()
    
    title = font_large.render("Выберите персонажа", True, WHITE)
    
    classes = [
        {"name": "Воин", "type": "warrior", "desc": "Сильный и выносливый"},
        {"name": "Маг", "type": "mage", "desc": "Мощные атаки"},
        {"name": "Лучник", "type": "archer", "desc": "Быстрый и ловкий"}
    ]
    
    buttons = []
    for i, cls in enumerate(classes):
        buttons.append(Button(
            WIDTH//2 - 150, 
            200 + i*120, 
            300, 
            100, 
            cls["name"], 
            (50, 50, 150), 
            (100, 100, 255)
        ))
    
    back_button = Button(50, HEIGHT - 70, 150, 50, "Назад", RED, (200, 0, 0))
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True
        
        screen.fill(BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        for i, button in enumerate(buttons):
            button.check_hover(mouse_pos)
            button.draw(screen)
            
            # Описание класса
            desc = font_small.render(classes[i]["desc"], True, WHITE)
            screen.blit(desc, (WIDTH//2 - desc.get_width()//2, button.rect.bottom + 5))
            
            if button.is_clicked(mouse_pos, mouse_click):
                game_state.player_class = classes[i]["type"]
                name_input(game_state)
        
        back_button.check_hover(mouse_pos)
        back_button.draw(screen)
        if back_button.is_clicked(mouse_pos, mouse_click):
            return
        
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)

def name_input(game_state):
    input_active = True
    name = ""
    
    title = font_large.render("Введите имя", True, WHITE)
    prompt = font_medium.render("Имя персонажа:", True, WHITE)
    
    while input_active:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_RETURN:
                    input_active = False
                elif event.key == K_BACKSPACE:
                    name = name[:-1]
                else:
                    if len(name) < 15:
                        name += event.unicode
        
        screen.fill(BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, 200))
        
        name_text = font_medium.render(name, True, WHITE)
        screen.blit(name_text, (WIDTH//2 - name_text.get_width()//2, 250))
        
        enter_text = font_small.render("Нажмите ENTER для продолжения", True, WHITE)
        screen.blit(enter_text, (WIDTH//2 - enter_text.get_width()//2, 350))
        
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)
    
    game_state.player_name = name if name else "Player"
    game_loop(game_state)

def game_loop(game_state):
    asset_manager = AssetManager()
    asset_manager.play_music(f"level{game_state.current_level}")
    
    # Создание уровня
    player = Player(100, 300, game_state.player_class)
    platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    
    # Базовый пол
    platforms.add(Platform(0, HEIGHT - 50, WIDTH, 50))
    
    # Генерация уровня
    if game_state.current_level == 1:
        platforms.add(Platform(100, 500, 200, 20))
        platforms.add(Platform(400, 400, 200, 20))
        platforms.add(Platform(200, 300, 100, 20))
        
        coins.add(Coin(200, 450))
        coins.add(Coin(500, 350))
        
        enemies.add(Enemy(300, 450))
    
    elif game_state.current_level == 2:
        # ... аналогично для других уровней
        pass
    
    all_sprites = pygame.sprite.Group()
    all_sprites.add(platforms)
    all_sprites.add(coins)
    all_sprites.add(enemies)
    all_sprites.add(player)
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_SPACE:
                    player.jump()
                if event.key == K_f:
                    player.attack()
                if event.key == K_ESCAPE:
                    return
        
        # Управление
        keys = pygame.key.get_pressed()
        player.velocity.x = 0
        if keys[K_LEFT]:
            player.velocity.x = -PLAYER_SPEED
            player.facing_right = False
        if keys[K_RIGHT]:
            player.velocity.x = PLAYER_SPEED
            player.facing_right = True
        
        # Обновление
        player.update(platforms, enemies)
        enemies.update(platforms, player)
        
        # Коллизия с монетами
        collected = pygame.sprite.spritecollide(player, coins, True)
        for coin in collected:
            player.add_coin()
        
        # Отрисовка
        screen.fill(BLACK)
        all_sprites.draw(screen)
        
        # UI
        health_text = font_medium.render(f"HP: {player.health}", True, WHITE)
        coin_text = font_medium.render(f"Монеты: {player.coins}", True, YELLOW)
        score_text = font_medium.render(f"Счёт: {player.score}", True, WHITE)
        level_text = font_medium.render(f"Уровень: {game_state.current_level}", True, WHITE)
        
        screen.blit(health_text, (10, 10))
        screen.blit(coin_text, (10, 50))
        screen.blit(score_text, (10, 90))
        screen.blit(level_text, (WIDTH - level_text.get_width() - 10, 10))
        
        pygame.display.flip()
        clock.tick(FPS)
        
        # Проверка условий уровня
        if not player.alive:
            game_over_screen(game_state, player.score)
            return
        
        if player.rect.y > HEIGHT:  # Упал за экран
            player.take_damage(10)
            player.rect.y = 100
        
        # Переход на следующий уровень
        if player.rect.x > WIDTH - 50:
            if game_state.next_level():
                game_loop(game_state)
            else:
                victory_screen(game_state, player.score)
            return

def game_over_screen(game_state, score):
    asset_manager = AssetManager()
    asset_manager.play_music("menu")
    
    title = font_large.render("Игра окончена", True, RED)
    score_text = font_medium.render(f"Ваш счёт: {score}", True, WHITE)
    
    buttons = [
        Button(WIDTH//2 - 100, HEIGHT//2 + 50, 200, 50, "Заново", BLUE, (0, 100, 255)),
        Button(WIDTH//2 - 100, HEIGHT//2 + 120, 200, 50, "В меню", GREEN, (0, 200, 100))
    ]
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True
        
        screen.fill(BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 200))
        
        for button in buttons:
            button.check_hover(mouse_pos)
            button.draw(screen)
            
            if button.is_clicked(mouse_pos, mouse_click):
                if button.text == "Заново":
                    game_state.current_level = 1
                    game_loop(game_state)
                else:
                    main_menu()
                return
        
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)

def victory_screen(game_state, score):
    asset_manager = AssetManager()
    asset_manager.play_music("menu")
    asset_manager.get_sound("victory").play()
    
    game_state.save_highscore(score)
    
    title = font_large.render("Победа!", True, GREEN)
    score_text = font_medium.render(f"Финальный счёт: {score}", True, WHITE)
    
    buttons = [
        Button(WIDTH//2 - 100, HEIGHT//2 + 50, 200, 50, "Заново", BLUE, (0, 100, 255)),
        Button(WIDTH//2 - 100, HEIGHT//2 + 120, 200, 50, "В меню", GREEN, (0, 200, 100))
    ]
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True
        
        screen.fill(BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 200))
        
        for button in buttons:
            button.check_hover(mouse_pos)
            button.draw(screen)
            
            if button.is_clicked(mouse_pos, mouse_click):
                if button.text == "Заново":
                    game_state.current_level = 1
                    game_loop(game_state)
                else:
                    main_menu()
                return
        
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)

def show_highscores(game_state):
    title = font_large.render("Рекорды", True, WHITE)
    
    back_button = Button(50, HEIGHT - 70, 150, 50, "Назад", RED, (200, 0, 0))
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True
        
        screen.fill(BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        if not game_state.highscores:
            no_scores = font_medium.render("Рекордов пока нет!", True, WHITE)
            screen.blit(no_scores, (WIDTH//2 - no_scores.get_width()//2, 200))
        else:
            for i, score in enumerate(game_state.highscores[:10]):
                score_text = font_medium.render(
                    f"{i+1}. {score['name']} ({score['class']}): {score['score']} (ур. {score['level']})", 
                    True, WHITE
                )
                screen.blit(score_text, (WIDTH//2 - 250, 150 + i * 40))
        
        back_button.check_hover(mouse_pos)
        back_button.draw(screen)
        if back_button.is_clicked(mouse_pos, mouse_click):
            return
        
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)

if __name__ == "__main__":
    main_menu()