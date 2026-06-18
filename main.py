import pygame
import serial
import serial.tools.list_ports
import random
import time
import sys
import math

# ==========================================
# 🎮 遊戲與睡眠指標演算法配置
# ==========================================
print("=== ACE: Liquid Matrix & Auto-Launch Reboot (Alpha 1.5.0) ===")
try: sleepiness = int(input("Enter Day-time Sleepiness Score (0-4): ") or "0")
except: sleepiness = 0
fog_alpha = int((sleepiness / 4.0) * 150) 

try: memory_score = int(input("Enter Memory Score (0-100): ") or "100")
except: memory_score = 100
sequence_length = 9 if memory_score < 50 else 5  

try: attention_score = int(input("Enter Attention Speed Score (0-100): ") or "100")
except: attention_score = 100

flight_speed = 0.075 - (attention_score / 100.0) * 0.050
is_good_sleep = (memory_score + attention_score) / 2 >= 60
universe_mode = "GOOD_SLEEP" if is_good_sleep else "SLEEP_DEBT"

COLOR_RGB = {
    'PURPLE': (170, 0, 255),   'YELLOW': (255, 230, 0), 'GREEN': (0, 255, 60),
    'BLUE':   (0, 100, 255),   'RED':    (255, 0, 0),   'WHITE': (240, 245, 255)
}
COLOR_POOL = ['GREEN', 'BLUE', 'YELLOW'] if is_good_sleep else ['PURPLE', 'BLUE', 'YELLOW']

def generate_balanced_layout():
    left_colors = COLOR_POOL.copy()
    random.shuffle(left_colors)
    a1_color, b1_color, c1_color = left_colors[0], left_colors[1], left_colors[2]
    c2_color = b1_color 
    remaining_for_right = [c for c in COLOR_POOL if c != c2_color]
    random.shuffle(remaining_for_right)
    a2_color, b2_color = remaining_for_right[0], remaining_for_right[1]
    return {'A1': a1_color, 'A2': a2_color, 'B1': b1_color, 'B2': b2_color, 'C1': c1_color, 'C2': c2_color}

GAME_LAYOUT = generate_balanced_layout()
available_nodes = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
target_nodes = random.choices(available_nodes, k=sequence_length) if universe_mode == "SLEEP_DEBT" else random.sample(available_nodes, sequence_length)
target_colors = [GAME_LAYOUT[n] for n in target_nodes]

# ==========================================
# 🔌 序列埠安全連線
# ==========================================
ser = None
ports = list(serial.tools.list_ports.comports())
for p in ports:
    if "usbserial" in p.device or "cu.usbserial" in p.device:
        try: ser = serial.Serial(p.device, 115200, timeout=0.01); print(f"[INFO] Linked on {p.device}"); break
        except: pass

def send_led_command(ser, node_key, color_char):
    if not ser or not ser.is_open: return
    node_map = {'A1': '0', 'A2': '1', 'B1': '2', 'B2': '3', 'C1': '4', 'C2': '5'}
    try: ser.write((node_map[node_key] + color_char).encode('ascii')); ser.flush()
    except: pass

def global_hardware_reset(ser):
    if not ser or not ser.is_open: return
    try: ser.write(b"XX"); ser.flush()
    except: pass

# ==========================================
# 🖥️ Pygame 初始化與全域視覺配置
# ==========================================
pygame.init()
size = (800, 750)
screen = pygame.display.set_mode(size)
pygame.display.set_caption("ACE: Liquid Glass Matrix")

font_large = pygame.font.SysFont("Helvetica", 40, bold=True)
font_sub = pygame.font.SysFont("Helvetica", 20)
font_core = pygame.font.SysFont("Helvetica", 22, bold=True)

NODE_POSITIONS = {'A1': (150, 120), 'A2': (650, 120), 'B1': (90, 360), 'B2': (710, 360), 'C1': (150, 600), 'C2': (650, 600)}
CENTER_CORE_POS = (400, 360)
KEY_NODE_MAP = {pygame.K_1: 'A1', pygame.K_2: 'A2', pygame.K_3: 'B1', pygame.K_4: 'B2', pygame.K_5: 'C1', pygame.K_6: 'C2'}

game_state = 0  
player_index = 0
current_led_states = {k: False for k in available_nodes} 
global_hardware_reset(ser)

flash_idx = 0; anim_t = 0.0; is_ball_flying = False; ball_current_pos = list(CENTER_CORE_POS); ball_history = [] 
countdown_start_ticks = 0 

def draw_liquid_glass_sphere(surface, center, radius, color, base_alpha=120):
    for r in range(radius, 0, -3):
        alpha = int(base_alpha * (1.0 - (r / radius) ** 1.5))
        if alpha <= 0: alpha = 1
        glow_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, color + (alpha,), (r, r), r)
        surface.blit(glow_surf, (center[0] - r, center[1] - r))

clock = pygame.time.Clock()
running = True

while running:
    pulse_factor = (math.sin(pygame.time.get_ticks() * 0.004) + 1.0) / 2.0  
    
    if ser and ser.is_open and ser.in_waiting > 0:
        raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
        if raw_line == "DOUBLE":
            if game_state == 0:
                global_hardware_reset(ser)
                game_state = 1; flash_idx = 0; anim_t = 0.0; is_ball_flying = True; ball_history.clear()
            elif game_state in [3, 4]:
                print("[SYS] Restart triggered via hardware! Sending WW to MCU...")
                game_state = 5
                countdown_start_ticks = pygame.time.get_ticks()
                if ser and ser.is_open: ser.write(b"WW"); ser.flush() # 🌟 指令：引爆實體低亮度白光呼吸！
        elif game_state == 2 and raw_line in available_nodes:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=None, unicode=raw_line))

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if game_state == 0:
                    global_hardware_reset(ser)
                    game_state = 1; flash_idx = 0; anim_t = 0.0; is_ball_flying = True; ball_history.clear()
                elif game_state in [3, 4]:
                    print("[SYS] Restart triggered via keyboard! Sending WW to MCU...")
                    game_state = 5
                    countdown_start_ticks = pygame.time.get_ticks()
                    if ser and ser.is_open: ser.write(b"WW"); ser.flush()

            if game_state == 2:
                pressed_node = None
                if event.key in KEY_NODE_MAP: pressed_node = KEY_NODE_MAP[event.key]
                elif hasattr(event, 'unicode') and event.unicode in available_nodes: pressed_node = event.unicode
                
                if pressed_node:
                    if player_index > 0 and pressed_node == target_nodes[player_index - 1]: continue
                    expected_node = target_nodes[player_index]
                    
                    if pressed_node == expected_node:
                        print(f"🎯 MATCH! Node {pressed_node} correctly recalled.")
                        current_led_states[pressed_node] = False
                        send_led_command(ser, pressed_node, 'X') 
                        
                        if universe_mode == "SLEEP_DEBT":
                            mutation_color = random.choice(['RED', 'WHITE'])
                            GAME_LAYOUT[pressed_node] = mutation_color
                            current_led_states[pressed_node] = True
                            send_led_command(ser, pressed_node, mutation_color[0]) 
                        
                        player_index += 1
                        if player_index >= len(target_nodes):
                            print("🏆 VICTORY! Triggering physical circular wave motion!")
                            game_state = 3 
                            if ser and ser.is_open: ser.write(b"SS"); ser.flush()
                    else:
                        print("❌ LAPSE! Critical Error. System Locked.")
                        game_state = 4
                        for n in available_nodes: send_led_command(ser, n, 'R')

    # ==========================================
    # 🌊 Apple 極簡流體玻璃美學引擎
    # ==========================================
    screen.fill((8, 8, 12)) 
    
    if game_state == 1 and is_ball_flying:
        active_node = target_nodes[flash_idx]
        active_color_name = target_colors[flash_idx]
        rgb = COLOR_RGB[active_color_name]
        target_pos = NODE_POSITIONS[active_node]
        
        anim_t += flight_speed
        if anim_t >= 1.0:
            anim_t = 1.0; is_ball_flying = False
            current_led_states[active_node] = True
            send_led_command(ser, active_node, active_color_name[0]) 
            time.sleep(0.25) 
            flash_idx += 1
            if flash_idx < len(target_colors): anim_t = 0.0; is_ball_flying = True; ball_history.clear()
            else: game_state = 2; player_index = 0
        
        ball_current_pos[0] = int(CENTER_CORE_POS[0] + (target_pos[0] - CENTER_CORE_POS[0]) * anim_t)
        ball_current_pos[1] = int(CENTER_CORE_POS[1] + (target_pos[1] - CENTER_CORE_POS[1]) * anim_t)
        ball_history.append(tuple(ball_current_pos))
        if len(ball_history) > 8: ball_history.pop(0)
            
        for h_idx, pos in enumerate(ball_history):
            trail_alpha = int(140 * (h_idx / len(ball_history)))
            trail_radius = int(15 + 20 * (h_idx / len(ball_history)))
            draw_liquid_glass_sphere(screen, pos, trail_radius, rgb, base_alpha=trail_alpha)
        draw_liquid_glass_sphere(screen, ball_current_pos, 45, rgb, base_alpha=220); draw_liquid_glass_sphere(screen, ball_current_pos, 22, (255, 255, 255), base_alpha=180)

    core_color = (18, 20, 28); core_text = "READY"
    if game_state == 0:
        glow_radius = int(65 + pulse_factor * 12)
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, glow_radius, (100, 120, 180), base_alpha=45)
    elif game_state == 1: core_text = "" 
    elif game_state == 2:
        core_color = (30, 35, 50); core_text = "INPUT NOW"
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, int(70 + pulse_factor * 6), (0, 180, 255), base_alpha=40)
    elif game_state == 3:
        core_color = (12, 70, 30); core_text = "PASS"
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, 100, COLOR_RGB['GREEN'], base_alpha=120)
    elif game_state == 4:
        core_color = (100, 0, 0); core_text = "LAPSE"
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, 140, COLOR_RGB['RED'], base_alpha=180)
    
    # 🌟【狀態 5 大改版：3秒倒數結束「無縫開局」機制】
    elif game_state == 5:
        elapsed_ms = pygame.time.get_ticks() - countdown_start_ticks
        seconds_left = 3 - (elapsed_ms // 1000)
        
        if seconds_left <= 0:
            print("[SYS] Countdown complete! 🚀 AUTO-LAUNCHING NEXT MATRIX STAGE 1...")
            # 🌟 直接強行灌入第一局開場狀態（state 1），拒絕回到 READY 閒置！
            game_state = 1
            player_index = 0
            flash_idx = 0
            anim_t = 0.0
            is_ball_flying = True
            ball_history.clear()
            current_led_states = {k: False for k in available_nodes}
            
            # 全面洗牌
            GAME_LAYOUT = generate_balanced_layout()
            target_nodes = random.choices(available_nodes, k=sequence_length) if universe_mode == "SLEEP_DEBT" else random.sample(available_nodes, sequence_length)
            target_colors = [GAME_LAYOUT[n] for n in target_nodes]
            global_hardware_reset(ser) # 發送 XX 指令，自動切斷 ESP32 的白光呼吸！
        else:
            core_color = (32, 35, 48)
            core_text = f"REBOOT {seconds_left}"
            scale_pulse = (elapsed_ms % 1000) / 1000.0
            glow_radius = int(60 + (1.0 - scale_pulse) * 45)
            draw_liquid_glass_sphere(screen, CENTER_CORE_POS, glow_radius, (240, 245, 255), base_alpha=int(70 * (1.0 - scale_pulse)))

    pygame.draw.circle(screen, core_color, CENTER_CORE_POS, 55); pygame.draw.circle(screen, (150, 165, 200), CENTER_CORE_POS, 57, 2) 
    if core_text != "":
        text_surface = font_core.render(core_text, True, (225, 230, 250)); screen.blit(text_surface, (CENTER_CORE_POS[0] - text_surface.get_width()//2, CENTER_CORE_POS[1] - 11))

    for node, pos in NODE_POSITIONS.items(): screen.blit(font_sub.render(node, True, (35, 35, 45)), (pos[0]-12, pos[1]-10))
    if fog_alpha > 0 and game_state not in [3, 5]: 
        fog_surface = pygame.Surface(size, pygame.SRCALPHA); fog_surface.fill((6, 8, 18, fog_alpha)); screen.blit(fog_surface, (0, 0))

    screen.blit(font_large.render("Adaptive Cognitive Evaluator", True, (210, 215, 240)), (50, 25))
    screen.blit(font_sub.render(f"Universe: {universe_mode} | Sequence: {len(target_nodes)} Steps", True, (100, 100, 125)), (50, 75))
    if game_state == 2:
        screen.blit(font_large.render(f"Progress Matrix: {player_index} / {len(target_nodes)}", True, (255, 255, 255)), (240, 675))
    if game_state == 4:
        fail_overlay = pygame.Surface(size, pygame.SRCALPHA); fail_overlay.fill((255, 0, 0, int(35 + pulse_factor * 25))); screen.blit(fail_overlay, (0, 0))

    pygame.display.flip()
    clock.tick(60)

global_hardware_reset(ser)
if ser and ser.is_open: ser.close()
pygame.quit()
sys.exit()