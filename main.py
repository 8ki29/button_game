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
print("=== ACE: Liquid Glass & Motion Trail Sync (Alpha 1.1.0) ===")
try:
    sleepiness = int(input("Enter Day-time Sleepiness Score (0-4): ") or "0")
except: sleepiness = 0
fog_alpha = int((sleepiness / 4.0) * 150) 

try:
    memory_score = int(input("Enter Memory Score (0-100): ") or "100")
except: memory_score = 100
sequence_length = 9 if memory_score < 50 else 5  

try:
    attention_score = int(input("Enter Attention Speed Score (0-100): ") or "100")
except: attention_score = 100

# 🌟 修正點 1：反向速度演算法！分數越高（100）＝ 越慢越容易（0.025）；分數越低（0）＝ 暴衝地獄（0.075）
flight_speed = 0.075 - (attention_score / 100.0) * 0.050

is_good_sleep = (memory_score + attention_score) / 2 >= 60
universe_mode = "GOOD_SLEEP" if is_good_sleep else "SLEEP_DEBT"

# Apple 流體光澤色調
COLOR_RGB = {
    'PURPLE': (170, 0, 255),   'YELLOW': (255, 230, 0), 'GREEN': (0, 255, 60),
    'BLUE':   (0, 100, 255),   'RED':    (255, 20, 50), 'WHITE': (240, 245, 255),
    'DARK_GRAY': (25, 25, 35)
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
if universe_mode == "SLEEP_DEBT":
    target_nodes = random.choices(available_nodes, k=sequence_length)
else:
    target_nodes = random.sample(available_nodes, sequence_length)

target_colors = [GAME_LAYOUT[n] for n in target_nodes]

# ==========================================
# 🔌 序列埠安全連線
# ==========================================
ser = None
ports = list(serial.tools.list_ports.comports())
for p in ports:
    if "usbserial" in p.device or "cu.usbserial" in p.device:
        try:
            ser = serial.Serial(p.device, 115200, timeout=0.01)
            break
        except: pass

def send_led_command(ser, node_key, color_char):
    if not ser or not ser.is_open: return
    node_map = {'A1': '0', 'A2': '1', 'B1': '2', 'B2': '3', 'C1': '4', 'C2': '5'}
    packet = node_map[node_key] + color_char
    try: ser.write(packet.encode('ascii')); ser.flush()
    except: pass

def global_hardware_reset(ser):
    if not ser or not ser.is_open: return
    try: ser.write(f"XX".encode('ascii')); ser.flush()
    except: pass

# ==========================================
# 🖥️ Pygame 初始化與高級字型配置
# ==========================================
pygame.init()
size = (800, 750)
screen = pygame.display.set_mode(size)
pygame.display.set_caption("ACE: Liquid Glass Engine")

font_large = pygame.font.SysFont("Helvetica", 40, bold=True)
font_sub = pygame.font.SysFont("Helvetica", 20)
font_core = pygame.font.SysFont("Helvetica", 22, bold=True)

NODE_POSITIONS = {
    'A1': (150, 120), 'A2': (650, 120),
    'B1': (90, 360),  'B2': (710, 360),
    'C1': (150, 600), 'C2': (650, 600)
}
CENTER_CORE_POS = (400, 360)

KEY_NODE_MAP = {
    pygame.K_1: 'A1', pygame.K_2: 'A2',
    pygame.K_3: 'B1', pygame.K_4: 'B2',
    pygame.K_5: 'C1', pygame.K_6: 'C2'
}

game_state = 0  
player_index = 0
current_led_states = {k: False for k in available_nodes} 
global_hardware_reset(ser)

flash_idx = 0
anim_t = 0.0
is_ball_flying = False
ball_current_pos = list(CENTER_CORE_POS)

# 🌟 修正點 2：新增殘影尾跡陣列，用來記錄過去的軌跡位置，達成流體流線感
ball_history = [] 

def draw_liquid_glass_sphere(surface, center, radius, color, base_alpha=120):
    """高端多層次高斯發光疊加"""
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
        if raw_line == "DOUBLE" and game_state == 0:
            game_state = 1; flash_idx = 0; anim_t = 0.0; is_ball_flying = True; ball_history.clear()
        elif game_state == 2 and raw_line in available_nodes:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=None, unicode=raw_line))

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and game_state == 0:
                print("[SYS] Motion Trigger Activated! Launching Neural Sequence...")
                game_state = 1; flash_idx = 0; anim_t = 0.0; is_ball_flying = True; ball_history.clear()
            
            if event.key == pygame.K_7 and game_state == 0:
                universe_mode = "SLEEP_DEBT" if universe_mode == "GOOD_SLEEP" else "GOOD_SLEEP"
                print(f"[CHEAT] Universe swapped to: {universe_mode}")
                GAME_LAYOUT = generate_balanced_layout()
                target_nodes = random.choices(available_nodes, k=sequence_length) if universe_mode == "SLEEP_DEBT" else random.sample(available_nodes, sequence_length)
                target_colors = [GAME_LAYOUT[n] for n in target_nodes]

            if game_state == 2:
                pressed_node = None
                if event.key in KEY_NODE_MAP: pressed_node = KEY_NODE_MAP[event.key]
                elif hasattr(event, 'unicode') and event.unicode in available_nodes: pressed_node = event.unicode
                
                if pressed_node:
                    expected_color = target_colors[player_index]
                    actual_color = GAME_LAYOUT[pressed_node]
                    
                    if actual_color == expected_color and current_led_states[pressed_node] == True:
                        print(f"🎯 MATCH! Node {pressed_node} consumed.")
                        current_led_states[pressed_node] = False
                        send_led_command(ser, pressed_node, 'X')
                        
                        if universe_mode == "SLEEP_DEBT":
                            mutation_color = random.choice(['RED', 'WHITE'])
                            GAME_LAYOUT[pressed_node] = mutation_color
                            current_led_states[pressed_node] = True
                            print(f"⚠️ MUTATION! Node {pressed_node} mutated into Overload Color: {mutation_color}")
                            send_led_command(ser, pressed_node, mutation_color[0])
                        
                        player_index += 1
                        if player_index >= len(target_colors):
                            game_state = 3 
                            global_hardware_reset(ser)
                    else:
                        print("❌ LAPSE! Brain fatigue limit reached. Blocking hardware inputs.")
                        game_state = 4
                        for n in available_nodes: send_led_command(ser, n, 'R')

    # ==========================================
    # 🌊 高級 Apple 流體藝術渲染引擎
    # ==========================================
    screen.fill((10, 10, 15)) # 更加極致的深邃暗夜底色
    
    # 1. 題目展示期：彗星尾跡流體起飛動畫 (Neuron Flight Core)
    if game_state == 1 and is_ball_flying:
        active_node = target_nodes[flash_idx]
        active_color_name = target_colors[flash_idx]
        rgb = COLOR_RGB[active_color_name]
        target_pos = NODE_POSITIONS[active_node]
        
        anim_t += flight_speed
        if anim_t >= 1.0:
            anim_t = 1.0
            is_ball_flying = False
            current_led_states[active_node] = True
            send_led_command(ser, active_node, active_color_name[0])
            
            time.sleep(0.25) # 更輕柔的接棒喘息時間
            flash_idx += 1
            if flash_idx < len(target_colors):
                anim_t = 0.0
                is_ball_flying = True
                ball_history.clear()
            else:
                game_state = 2
                player_index = 0
        
        ball_current_pos[0] = int(CENTER_CORE_POS[0] + (target_pos[0] - CENTER_CORE_POS[0]) * anim_t)
        ball_current_pos[1] = int(CENTER_CORE_POS[1] + (target_pos[1] - CENTER_CORE_POS[1]) * anim_t)
        
        # 🌟 修正點 3：推入歷史記錄，並維持最多 8 幀的發光尾巴
        ball_history.append(tuple(ball_current_pos))
        if len(ball_history) > 8:
            ball_history.pop(0)
            
        # 🌟 繪製絲滑流體殘影尾巴（越前面的尾巴越淡、越小）
        for h_idx, pos in enumerate(ball_history):
            trail_alpha = int(140 * (h_idx / len(ball_history)))
            trail_radius = int(15 + 20 * (h_idx / len(ball_history)))
            draw_liquid_glass_sphere(screen, pos, trail_radius, rgb, base_alpha=trail_alpha)

        # 繪製最前端的超亮玻璃母體核心
        draw_liquid_glass_sphere(screen, ball_current_pos, 45, rgb, base_alpha=220)
        draw_liquid_glass_sphere(screen, ball_current_pos, 22, (255, 255, 255), base_alpha=180)

    # 2. 渲染中央神經元母體晶體 (Apple 玻璃核心)
    core_color = (20, 22, 32)
    core_text = "READY"
    if game_state == 0:
        # IDLE 階段：溫和的科技微光呼吸
        glow_radius = int(65 + pulse_factor * 12)
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, glow_radius, (110, 130, 180), base_alpha=50)
    elif game_state == 1:
        core_text = "" 
    elif game_state == 2:
        core_color = (35, 40, 55)
        core_text = "INPUT NOW"
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, int(70 + pulse_factor * 6), (0, 180, 255), base_alpha=40)
    elif game_state == 3:
        core_color = (15, 80, 35)
        core_text = "PASS"
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, 100, COLOR_RGB['GREEN'], base_alpha=120)
    elif game_state == 4:
        core_color = (110, 15, 15)
        core_text = "LAPSE"
        draw_liquid_glass_sphere(screen, CENTER_CORE_POS, 130, COLOR_RGB['RED'], base_alpha=180)

    # 繪製中央實體流體玻璃外框
    pygame.draw.circle(screen, core_color, CENTER_CORE_POS, 55)
    pygame.draw.circle(screen, (160, 175, 210), CENTER_CORE_POS, 57, 2) 
    
    if core_text != "":
        text_surface = font_core.render(core_text, True, (230, 235, 255))
        screen.blit(text_surface, (CENTER_CORE_POS[0] - text_surface.get_width()//2, CENTER_CORE_POS[1] - 11))

    # 3. 虛擬神經元外圍圈圈渲染
    for node, pos in NODE_POSITIONS.items():
        if game_state == 0:
            c_name = GAME_LAYOUT[node]
            draw_liquid_glass_sphere(screen, pos, 32, COLOR_RGB[c_name], base_alpha=65)
            pygame.draw.circle(screen, (60, 65, 85), pos, 34, 1)
        elif game_state == 2 and current_led_states[node]:
            c_name = GAME_LAYOUT[node]
            draw_liquid_glass_sphere(screen, pos, 38, COLOR_RGB[c_name], base_alpha=140)
            pygame.draw.circle(screen, (220, 230, 255), pos, 38, 2)
        else:
            pygame.draw.circle(screen, (30, 30, 40), pos, 25, 1)
            
        screen.blit(font_sub.render(node, True, (110, 110, 140)), (pos[0]-12, pos[1]-10))

    # 4. 頂層高階遮罩：大腦睡眠黑霧面紗
    if fog_alpha > 0 and game_state != 3:
        fog_surface = pygame.Surface(size, pygame.SRCALPHA)
        fog_surface.fill((8, 10, 22, fog_alpha)) 
        screen.blit(fog_surface, (0, 0))

    # 5. 文字 UI 指標渲染
    screen.blit(font_large.render("Adaptive Cognitive Evaluator", True, (215, 220, 245)), (50, 25))
    info_str = f"Universe: {universe_mode} | Sequence: {len(target_colors)} Steps"
    screen.blit(font_sub.render(info_str, True, (110, 110, 135)), (50, 75))
    if game_state == 2:
        progress_text = font_large.render(f"Progress Matrix: {player_index} / {len(target_colors)}", True, (255, 255, 255))
        screen.blit(progress_text, (240, 675))

    if game_state == 4:
        fail_overlay = pygame.Surface(size, pygame.SRCALPHA)
        fail_overlay.fill((230, 0, 30, int(35 + pulse_factor * 25)))
        screen.blit(fail_overlay, (0, 0))

    pygame.display.flip()
    clock.tick(60)

global_hardware_reset(ser)
if ser and ser.is_open: ser.close()
pygame.quit()
sys.exit()