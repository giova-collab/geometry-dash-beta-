import pygame
import sys
import math

# --- CONFIGURAZIONE ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colori accattivanti
BG_COLOR = (20, 20, 40)      # Blu scuro profondo
GROUND_COLOR = (40, 40, 80)  # Blu elettrico spento
PLAYER_COLOR = (0, 255, 200) # Turchese neon
SPIKE_COLOR = (255, 50, 50)  # Rosso vivido
BLOCK_COLOR = (100, 100, 150)# Viola/Grigio
WHITE = (255, 255, 255)

# Fisica
GRAVITY = 0.9
JUMP_FORCE = -14
SCROLL_SPEED = 7
FLOOR_Y = 500
TILE_SIZE = 40

# Mappa: . (vuoto), S (spina), B (blocco solido)
LEVEL_MAP = "......S...B...S...B....S....SSS...B.B...S...B..S...B...S...B...S...B....S...B...S...B....S...B...S...B...."

class Particle:
    """Gestisce i singoli frammenti dell'esplosione"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = pygame.time.get_ticks() % 10 - 5
        self.vy = pygame.time.get_ticks() % 12 - 8
        self.life = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 10
        self.vy += 0.2 # Gravità sulle particelle

    def draw(self, surface):
        if self.life > 0:
            color = (PLAYER_COLOR[0], PLAYER_COLOR[1], PLAYER_COLOR[2], self.life)
            pygame.draw.rect(surface, color, (self.x, self.y, 4, 4))

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        # Disegno del cubo con bordo definito
        pygame.draw.rect(self.original_image, PLAYER_COLOR, (0, 0, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(self.original_image, (0, 0, 0), (0, 0, TILE_SIZE, TILE_SIZE), 3)
        
        self.image = self.original_image
        self.rect = self.image.get_rect(x=150, bottom=FLOOR_Y)
        self.mask = pygame.mask.from_surface(self.image)
        
        self.vel_y = 0
        self.is_on_ground = True
        self.angle = 0
        self.target_angle = 0

    def apply_physics(self, obstacles):
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y
        
        self.is_on_ground = False
        
        # Collisione col pavimento base
        if self.rect.bottom >= FLOOR_Y:
            self.rect.bottom = FLOOR_Y
            self.vel_y = 0
            self.is_on_ground = True
            
        # Collisione con i Blocchi (Piattaforme)
        for obj in obstacles:
            if isinstance(obj, Block) and self.rect.colliderect(obj.rect):
                # Collisione dall'alto (atterraggio)
                if self.vel_y > 0 and self.rect.bottom <= obj.rect.top + 15:
                    self.rect.bottom = obj.rect.top
                    self.vel_y = 0
                    self.is_on_ground = True
                # Collisione laterale (morte se colpisci il lato del blocco)
                elif self.rect.right > obj.rect.left + 5 and self.rect.left < obj.rect.right - 5:
                    return True # Segnala morte
        return False

    def update_rotation(self):
        if not self.is_on_ground:
            # Ruota di 90 gradi durante il salto (velocità proporzionale allo scroll)
            self.angle -= 5 
            self.image = pygame.transform.rotate(self.original_image, self.angle)
            self.rect = self.image.get_rect(center=self.rect.center)
            self.target_angle = (self.angle // 90) * 90
        else:
            # Snap alla rotazione di 90 gradi più vicina quando tocca terra
            self.angle = self.target_angle
            self.image = pygame.transform.rotate(self.original_image, self.angle)
            # Ripristina il rect per evitare vibrazioni
            new_rect = self.image.get_rect(center=self.rect.center)
            self.rect.y = new_rect.y

    def jump(self):
        if self.is_on_ground:
            self.vel_y = JUMP_FORCE

class Spike(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        points = [(0, TILE_SIZE), (TILE_SIZE//2, 5), (TILE_SIZE, TILE_SIZE)]
        pygame.draw.polygon(self.image, SPIKE_COLOR, points)
        pygame.draw.polygon(self.image, (0, 0, 0), points, 2)
        self.rect = self.image.get_rect(x=x, y=y)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect.x -= SCROLL_SPEED
        if self.rect.right < 0: self.kill()

class Block(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(BLOCK_COLOR)
        pygame.draw.rect(self.image, (0, 0, 0), (0, 0, TILE_SIZE, TILE_SIZE), 2)
        self.rect = self.image.get_rect(x=x, y=y)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect.x -= SCROLL_SPEED
        if self.rect.right < 0: self.kill()

class GameManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Impact", 48)
        self.reset_game()

    def reset_game(self):
        self.player = Player()
        self.all_sprites = pygame.sprite.Group(self.player)
        self.obstacles = pygame.sprite.Group()
        self.particles = []
        self.game_over = False
        self.spawn_level()

    def spawn_level(self):
        for i, char in enumerate(LEVEL_MAP):
            x = 800 + (i * TILE_SIZE)
            if char == "S":
                spike = Spike(x, FLOOR_Y - TILE_SIZE)
                self.obstacles.add(spike)
                self.all_sprites.add(spike)
            elif char == "B":
                block = Block(x, FLOOR_Y - TILE_SIZE)
                self.obstacles.add(block)
                self.all_sprites.add(block)

    def create_explosion(self):
        for _ in range(20):
            self.particles.append(Particle(self.player.rect.centerx, self.player.rect.centery))

    def run(self):
        while True:
            # 1. Input - Auto-jump incluso
            keys = pygame.key.get_pressed()
            if not self.game_over and (keys[pygame.K_SPACE] or keys[pygame.K_UP]):
                self.player.jump()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN and self.game_over and event.key == pygame.K_r:
                    self.reset_game()

            # 2. Update
            if not self.game_over:
                self.all_sprites.update()
                self.player.update_rotation()
                
                # Collisioni e Fisica
                died_by_block = self.player.apply_physics(self.obstacles)
                
                # Collisione Pixel-Perfect con spine
                died_by_spike = pygame.sprite.spritecollide(self.player, self.obstacles, False, pygame.sprite.collide_mask)
                # Filtriamo: solo le spine nel gruppo causano morte immediata al contatto mask
                died_by_spike = any(isinstance(s, Spike) for s in died_by_spike)

                if died_by_block or died_by_spike:
                    self.game_over = True
                    self.create_explosion()

            # Update particelle (anche se game over)
            for p in self.particles: p.update()

            # 3. Draw
            self.screen.fill(BG_COLOR)
            # Disegno pavimento
            pygame.draw.rect(self.screen, GROUND_COLOR, (0, FLOOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT-FLOOR_Y))
            pygame.draw.line(self.screen, WHITE, (0, FLOOR_Y), (SCREEN_WIDTH, FLOOR_Y), 3)
            
            self.all_sprites.draw(self.screen)
            for p in self.particles: p.draw(self.screen)

            if self.game_over:
                txt = self.font.render("impara a giocare! PREMI 'R'", True, WHITE)
                self.screen.blit(txt, (SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2))

            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    GameManager().run()