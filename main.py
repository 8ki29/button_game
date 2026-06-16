import pygame
import serial
import threading
import sys
import time
import random
import math

class ESP32SerialReader:
    def __init__(self, port='/dev/cu.usbserial-210', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        # 【修正核心】改用 List 佇列，保證 A1 和 A2 同時進來時不會互相覆蓋！
        self.input_queue = [] 
        self.is_running = True
        self.lock = threading.Lock()
        
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=0.05)
            print(f"[INFO] Successfully connected to B1 on {self.port}")
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            sys.exit(1)

    def start_reading(self):
        thread = threading.Thread(target=self._read_loop, daemon=True)
        thread.start()

    def _read_loop(self):
        while self.is_running:
            if self.serial_port and self.serial_port.in_waiting > 0:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        with self.lock:
                            # 把所有讀到的按鈕訊號塞進隊伍裡排隊
                            self.input_queue.append(line)
                except Exception as e:
                    pass
            time.sleep(0.001)

    def pop_inputs(self):
        """一次性倒出目前排隊的所有按鈕訊號"""
        with self.lock:
            temp = list(self.input_queue)
            self.input_queue.clear()
            return temp

    def send_command(self, cmd_char):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(cmd_char.encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] Master write failed: {e}")

    def close(self):
        self.is_running = False
        if self.serial_port:
            self.send_command('X') 
            self.serial_port.close()

class MemoryGame:
    def __init__(self):
        pygame.init()
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Adaptive Cognitive Evaluator - Wireless Edition")
        
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.running = True
        self.sleep_score = 70  
        
        self.COLOR_BG_DEFAULT = (15, 15, 18)
        self.COLOR_BG_DISTORTED = (35, 30, 38) 
        self.current_bg = self.COLOR_BG_DEFAULT
        self.COLOR_WHITE = (240, 240, 242)
        
        self.COLORS_MAP = {
            "A1": {"name": "PURPLE", "rgb": (186, 85, 211), "pos": (250, 160)},
            "A2": {"name": "YELLOW", "rgb": (255, 215, 0),  "pos": (550, 160)},
            "B1": {"name": "GREEN",  "rgb": (0, 255, 128),  "pos": (200, 300)},
            "B2": {"name": "BLUE",   "rgb": (30, 144, 255), "pos": (600, 300)},
            "C1": {"name": "RED",    "rgb": (255, 50, 50),  "pos": (250, 440)},
            "C2": {"name": "WHITE",  "rgb": (240, 240, 255),"pos": (550, 440)}
        }
        
        self.CMD_MAP = {
            "A1": ('0', '1'), "A2": ('2', '3'),
            "B1": ('4', '5'), "B2": ('6', '7'),
            "C1": ('8', '9'), "C2": ('A', 'B')
        }
        
        self.glow_states = {key: {"radius": 0, "alpha": 0} for key in self.COLORS_MAP.keys()}
        self.max_glow_radius = 110
        
        self.STATE_START_SCREEN = 0
        self.STATE_GENERATE_SEQUENCE = 1
        self.STATE_FLASH_SEQUENCE = 2
        self.STATE_PLAYER_INPUT = 3
        self.STATE_GAME_OVER = 4
        self.game_state = self.STATE_START_SCREEN
        
        self.score = 0
        self.max_score = 5
        self.target_sequence = []  
        self.player_sequence = []  
        
        self.flash_index = 0
        self.flash_start_time = 0
        self.flash_duration = 1.2  
        self.flash_gap = 0.5       
        self.is_blank_period = False
        self.center_alpha = 0      
        
        self.is_in_cooldown = False
        self.cooldown_start_time = 0
        self.cooldown_duration = 1.0  
        self.active_cooldown_node = None 
        self.input_phase_initialized = False 
        
        self.fog_density = 0       
        self.glitch_active = False 
        self.flicker_active = False
        self.flicker_frequency = 0  
        self.frame_count = 0
        
        self.a1_last_pressed_time = 0
        self.a2_last_pressed_time = 0
        self.sync_window = 0.4  # 放寬時間窗至 0.4 秒，確保雙擊絕對能被判定！
        
        self.font_large = pygame.font.SysFont("Helvetica", 36)
        self.font_small = pygame.font.SysFont("Helvetica", 20)
        
        self.esp32 = ESP32SerialReader(port='/dev/cu.usbserial-210', baudrate=115200)

    def run(self):
        self.esp32.start_reading()
        while self.running:
            self.handle_events()
            self.update_game_logic()
            self.render()
            self.clock.tick(self.fps)
        self.cleanup()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update_game_logic(self):
        current_time = time.time()
        self.frame_count += 1
        
        # 倒出排隊中的所有硬體輸入
        hardware_inputs = self.esp32.pop_inputs()
        
        # 掃描這一個 Frame 裡所有進來的按鈕
        for inp in hardware_inputs:
            if inp == "A1": self.a1_last_pressed_time = current_time
            elif inp == "A2": self.a2_last_pressed_time = current_time
            
            # 答題階段的按鍵邏輯
            if not self.is_in_cooldown and self.game_state == self.STATE_PLAYER_INPUT:
                if inp in self.COLORS_MAP:
                    self.player_sequence.append(inp)
                    self.glow_states[inp]["radius"] = 45
                    self.glow_states[inp]["alpha"] = 200
                    
                    # 隔空無線關燈鎖定
                    self.esp32.send_command(self.CMD_MAP[inp][0])
                    
                    self.is_in_cooldown = True
                    self.cooldown_start_time = current_time
                    self.active_cooldown_node = inp
                    
                    # 檢查答案
                    current_step = len(self.player_sequence) - 1
                    if self.player_sequence[current_step] == self.target_sequence[current_step]:
                        if len(self.player_sequence) == len(self.target_sequence):
                            self.score = self.max_score
                            self.esp32.send_command('X') 
                            self.game_state = self.STATE_GAME_OVER
                    else:
                        self.score = current_step
                        self.esp32.send_command('X') 
                        self.game_state = self.STATE_GAME_OVER
                    break # 一個 Frame 只處理一個有效答題

        # 判定雙擊啟動/重置
        both_top_buttons_held = (current_time - self.a1_last_pressed_time < self.sync_window) and \
                                 (current_time - self.a2_last_pressed_time < self.sync_window)

        # 燈光動態擴散更新
        for key in self.glow_states:
            if self.glow_states[key]["alpha"] > 0:
                self.glow_states[key]["radius"] += 3
                self.glow_states[key]["alpha"] = max(0, self.glow_states[key]["alpha"] - 8)

        # 釋放冷卻重新亮燈
        if self.is_in_cooldown:
            if current_time - self.cooldown_start_time > self.cooldown_duration:
                self.esp32.send_command(self.CMD_MAP[self.active_cooldown_node][1])
                self.is_in_cooldown = False
                self.active_cooldown_node = None

        # --- 狀態機（FSM）管理 ---
        if self.game_state == self.STATE_START_SCREEN:
            self.current_bg = self.COLOR_BG_DEFAULT
            if both_top_buttons_held:
                self.a1_last_pressed_time = 0
                self.a2_last_pressed_time = 0
                self.score = 0
                self.is_in_cooldown = False
                self.input_phase_initialized = False
                self.esp32.send_command('X') 
                self.game_state = self.STATE_GENERATE_SEQUENCE
                time.sleep(0.4)

        elif self.game_state == self.STATE_GENERATE_SEQUENCE:
            all_keys = list(self.COLORS_MAP.keys())
            self.target_sequence = [random.choice(all_keys) for _ in range(self.max_score)]
            print(f"[GAME] Target Sequence: {[self.COLORS_MAP[k]['name'] for k in self.target_sequence]}")
            self.player_sequence = []
            self.flash_index = 0
            self.flash_start_time = current_time
            self.is_blank_period = False
            
            score_factor = self.sleep_score / 100.0
            self.flash_duration = 0.4 + (1.1 * score_factor)
            self.flash_gap = 0.3 + (0.3 * score_factor)
            self.fog_density = int((1.0 - score_factor) * 140)
            
            if self.sleep_score < 50:
                self.glitch_active = True
                self.flicker_active = True
                self.flicker_frequency = 4 if self.sleep_score < 25 else 8
            else:
                self.glitch_active = False
                self.flicker_active = False
                
            self.game_state = self.STATE_FLASH_SEQUENCE

        elif self.game_state == self.STATE_FLASH_SEQUENCE:
            elapsed = current_time - self.flash_start_time
            if self.flicker_active:
                if self.frame_count % self.flicker_frequency == 0:
                    self.current_bg = self.COLOR_BG_DISTORTED if self.current_bg == self.COLOR_BG_DEFAULT else self.COLOR_BG_DEFAULT
            else:
                self.current_bg = self.COLOR_BG_DEFAULT

            if self.flash_index < len(self.target_sequence):
                if not self.is_blank_period:
                    progress = elapsed / self.flash_duration
                    self.center_alpha = int(math.sin(progress * math.pi) * 255)
                    self.center_alpha = max(0, min(255, self.center_alpha))
                    if elapsed > self.flash_duration:
                        self.is_blank_period = True
                        self.flash_start_time = current_time
                        self.center_alpha = 0
                else:
                    self.center_alpha = 0
                    if elapsed > self.flash_gap:
                        self.is_blank_period = False
                        self.flash_index += 1
                        self.flash_start_time = current_time
            
            if self.flash_index >= len(self.target_sequence):
                self.current_bg = self.COLOR_BG_DEFAULT
                self.game_state = self.STATE_PLAYER_INPUT

        elif self.game_state == self.STATE_PLAYER_INPUT:
            if not self.input_phase_initialized:
                self.esp32.send_command('Y') # 唰地一聲無線全亮！
                self.input_phase_initialized = True

        elif self.game_state == self.STATE_GAME_OVER:
            if both_top_buttons_held:
                self.a1_last_pressed_time = 0
                self.a2_last_pressed_time = 0
                self.game_state = self.STATE_START_SCREEN
                time.sleep(0.4)

    def draw_transparent_circle(self, color, alpha, center, radius, width=0):
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*color, alpha), (radius, radius), radius, width)
        self.screen.blit(surface, (center[0] - radius, center[1] - radius))

    def render(self):
        self.screen.fill(self.current_bg)
        
        for key, data in self.COLORS_MAP.items():
            pos = data["pos"]
            rgb = data["rgb"]
            self.draw_transparent_circle(rgb, 45, pos, 45, width=3)
            self.draw_transparent_circle(rgb, 15, pos, 42)
            
        self.draw_transparent_circle((200, 200, 200), 30, (400, 300), 65, width=2)

        for key, glow in self.glow_states.items():
            if glow["alpha"] > 0 and glow["radius"] < self.max_glow_radius:
                pos = self.COLORS_MAP[key]["pos"]
                rgb = self.COLORS_MAP[key]["rgb"]
                self.draw_transparent_circle(rgb, glow["alpha"], pos, glow["radius"], width=4)

        if self.game_state == self.STATE_FLASH_SEQUENCE and not self.is_blank_period:
            if self.flash_index < len(self.target_sequence):
                active_key = self.target_sequence[self.flash_index]
                target_rgb = self.COLORS_MAP[active_key]["rgb"]
                self.draw_transparent_circle(target_rgb, self.center_alpha, (400, 300), 60)

        txt_sleep_info = self.font_small.render(f"System Profile: Sleep Score [{self.sleep_score}]", True, (120, 120, 130))
        self.screen.blit(txt_sleep_info, (20, 20))
        
        if self.game_state == self.STATE_PLAYER_INPUT and self.is_in_cooldown:
            txt_lock = self.font_small.render("[HARDWARE LOCKOUT - RE-ARMING PIPELINE]", True, (255, 100, 100))
            self.screen.blit(txt_lock, (240, 540))

        if self.game_state == self.STATE_START_SCREEN:
            txt_title = self.font_large.render("Cognitive Evaluator (Wireless Standard)", True, self.COLOR_WHITE)
            txt_prompt = self.font_small.render("Press Top-Left (A1) & Top-Right (A2) to initialize", True, self.COLOR_WHITE)
            self.screen.blit(txt_title, (160, 220))
            self.screen.blit(txt_prompt, (200, 320))
            
        elif self.game_state == self.STATE_FLASH_SEQUENCE:
            txt_watch = self.font_large.render("Observe Sequence", True, self.COLOR_WHITE)
            self.screen.blit(txt_watch, (280, 220))
            
        elif self.game_state == self.STATE_PLAYER_INPUT:
            txt_repeat = self.font_large.render("Replicate Mapped Nodes", True, self.COLOR_WHITE)
            txt_count = self.font_small.render(f"Progress Matrix: {len(self.player_sequence)} / {self.max_score}", True, self.COLOR_WHITE)
            self.screen.blit(txt_repeat, (250, 220))
            self.screen.blit(txt_count, (330, 320))
            
        elif self.game_state == self.STATE_GAME_OVER:
            msg = "EVALUATION OPTIMAL" if self.score == self.max_score else "EVALUATION TERMINATED"
            txt_status = self.font_large.render(msg, True, self.COLOR_WHITE)
            self.screen.blit(txt_status, (240 if self.score == self.max_score else 225, 200))
            
        pygame.display.flip()

    def cleanup(self):
        self.esp32.close()
        pygame.quit()

if __name__ == "__main__":
    game = MemoryGame()
    game.run()