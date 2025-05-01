import os, sys
import pygame
import requests
from dotenv import load_dotenv

# ── Load API key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not set in .env")
    sys.exit(1)

# ── Settings
WIDTH, HEIGHT = 800, 600
FPS = 60
CHAT_H = 150
INPUT_H = 30
SECRET = "golden_key"

# ── Asset paths
PLAYER_SHEET = "assets/player.png"  # 1×6 @32×64
NPC_SHEET    = "assets/npc.png"     # 1×4 @32×64

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chatty Adventure")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 28)
input_font = pygame.font.Font(None, 24)

def load_frames(path, w, h):
    sheet = pygame.image.load(path).convert_alpha()
    sw, sh = sheet.get_size()
    cols, rows = sw//w, sh//h
    frames = []
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(c*w, r*h, w, h)
            frames.append(sheet.subsurface(rect))
    return frames

# Load sprites
player_frames = load_frames(PLAYER_SHEET, 32, 64)
npc_images    = load_frames(NPC_SHEET,    32, 64)

player_idx = 0
player_img = player_frames[0]
npc_img    = npc_images[0]

player_rect = player_img.get_rect(center=(WIDTH//2, HEIGHT//2 - CHAT_H//2))
npc_rect    = npc_img.get_rect(center=(WIDTH//4, HEIGHT//2 - CHAT_H//2))

# Chat state
chat_log = []       # list of (speaker, text)
input_text = ""     # current typing buffer

def ask_npc(prompt: str) -> str:
    """
    Sends `prompt` to the Gemini 2.0-flash generateContent endpoint
    and returns only the flattened text reply.
    """
    url = (
      "https://generativelanguage.googleapis.com/"
      "v1beta/models/gemini-2.0-flash:generateContent"
      f"?key={API_KEY}"
    )
    headers = {"Content-Type": "application/json"}  # per spec :contentReference[oaicite:2]{index=2}
    body = {"contents":[{"parts":[{"text": prompt}]}]}
    
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    data = resp.json()
    
    # Extract the first candidate
    cand = data.get("candidates", [{}])[0]
    content = cand.get("content", "")
    
    # If content is a dict with parts, join their 'text'
    if isinstance(content, dict) and "parts" in content:
        return "".join(p.get("text", "") for p in content["parts"])
    
    # Otherwise, if it's a plain string, return it
    if isinstance(content, str):
        return content
    
    # Fallback to string conversion
    return str(content)


def draw():
    screen.fill((20,20,20))
    # Game area
    screen.blit(player_img, player_rect)
    screen.blit(npc_img,    npc_rect)
    # Chat background
    chat_bg = pygame.Rect(0, HEIGHT-CHAT_H-INPUT_H, WIDTH, CHAT_H)
    pygame.draw.rect(screen, (30,30,30), chat_bg)
    # Draw last 5 messages
    y = HEIGHT-CHAT_H-INPUT_H + 5
    for speaker, text in chat_log[-5:]:
        col = (200,200,255) if speaker=="NPC" else (200,255,200)
        line = f"{speaker}: {text}"
        surf = font.render(line, True, col)
        screen.blit(surf, (10, y))
        y += surf.get_height()+2
    # Only draw input when near NPC
    if player_rect.colliderect(npc_rect):
        inp_rect = pygame.Rect(0, HEIGHT-INPUT_H, WIDTH, INPUT_H)
        pygame.draw.rect(screen, (50,50,50), inp_rect)
        txt = input_font.render("> " + input_text, True, (240,240,240))
        screen.blit(txt, (10, HEIGHT-INPUT_H+5))
    pygame.display.flip()

# Main loop
running = True
while running:
    dt = clock.tick(FPS)
    moved = False

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False

        # Handle typing only if near NPC
        if player_rect.colliderect(npc_rect) and ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                msg = input_text.strip()
                if msg:
                    chat_log.append(("You", msg))
                    reply = ask_npc(msg)
                    chat_log.append(("NPC", reply))
                    # Victory check
                    if SECRET in reply.lower():
                        chat_log.append(("SYSTEM", "🎉 You've found the golden key!"))
                        draw()
                        pygame.time.delay(3000)
                        running = False
                input_text = ""
            elif ev.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            else:
                if ev.unicode.isprintable():
                    input_text += ev.unicode

    # Movement (no fractional steps)
    keys = pygame.key.get_pressed()
    dx = dy = 0
    if keys[pygame.K_LEFT]:
        dx = -5; moved = True
    if keys[pygame.K_RIGHT]:
        dx = 5;  moved = True
    if keys[pygame.K_UP]:
        dy = -5; moved = True
    if keys[pygame.K_DOWN]:
        dy = 5;  moved = True

    player_rect.move_ip(dx, dy)

    # Simple animation: cycle through frames if moving
    if moved:
        player_idx = (player_idx + 1) % len(player_frames)
    else:
        player_idx = 0
    player_img = player_frames[player_idx]

    draw()

pygame.quit()