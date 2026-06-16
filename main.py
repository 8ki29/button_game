import pygame
import serial
import threading
import sys
import time
import random
import math

class ESP32SerialReader:
    """Handles bidirectional serial communication with the ESP32."""
    def __init__(self, port='/dev/cu.usbserial-210', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        self.latest_input = None
        self.is_running = True
        
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"[INFO] Successfully connected to ESP32 on {self.port}")
        except Exception as e:
            print(f"[ERROR] Failed to connect to ESP32: {e}")
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
                        self.latest_input = line
                except Exception as e:
                    print(f"[WARNING] Error reading serial data: {e}")

    def get_latest_input(self):
        temp = self.latest_input
        self.latest_input = None
        return temp

    def send_command(self, cmd_char):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(cmd_char.encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] Master write pipeline failed: {e}")

    def close(self):
        self.is_running = False
        if self.serial_port:
            self.send_command('X')
            self.serial_port.close()


class MemoryGame:
    """
    Advanced Cognitive Evaluator.
    Implements hardware visual exclusion, keeping physical LEDs OFF during display phase,
    lighting both up during input phase, and triggering a strict 1-second system cooldown on press.
    """
    def __init__(self):
        pygame.init()
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Adaptive Cognitive Evaluator - Cooldown Edition")
        
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.running = True
        
        # --- ADJUSTABLE PARAMETER FOR TESTING ---
        self.sleep_score = 75  
        # ----------------------------------------
        
        self.COLOR_BG_DEFAULT = (15, 15, 18)
        self.COLOR_BG_DISTORTED = (35, 30, 38) 
        self.current_bg = self.COLOR_BG_DEFAULT
        self.COLOR_WHITE = (240, 240, 242)
        
        self.RGB_GREEN = (0, 255, 128)  
        self.RGB_BLUE = (0, 191, 255)   
        self.RGB_CENTER = (200, 200, 200)
        
        # Game States
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
        
        # Cooldown & Visual Exclusion System States
        self.is_in_cooldown = False
        self.cooldown_start_time = 0
        self.cooldown_duration = 1.0  # Strict 1-second cooldown for buttons and LEDs
        self.input_phase_initialized = False # Flag to turn both LEDs ON once when entering input state
        
        self.flicker_active = False
        self.flicker_frequency = 0  
        self.frame_count = 0
        
        self.left_glow_radius = 0
        self.left_glow_alpha = 0
        self.right_glow_radius = 0
        self.right_glow_alpha = 0
        self.max_glow_radius = 120  
        
        self.b1_last_pressed_time = 0
        self.b2_last_pressed_time = 0
        self.sync_window = 0.2  
        
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
        hardware_input = self.esp32.get_latest_input()
        current_time = time.time()
        self.frame_count += 1
        
        input_triggered = None
        
        # Intercept inputs only if the system is NOT locked down by a cooldown
        if not self.is_in_cooldown and self.game_state == self.STATE_PLAYER_INPUT:
            if hardware_input == "B1":    # Left Pressed (Green)
                input_triggered = "GREEN"
                self.b1_last_pressed_time = current_time
                self.left_glow_radius = 50
                self.left_glow_alpha = 200
                
                # Turn OFF physical Green LED instantly on press and start cooldown
                self.esp32.send_command('g')
                self.is_in_cooldown = True
                self.cooldown_start_time = current_time
                
            elif hardware_input == "B2":  # Right Pressed (Blue)
                input_triggered = "BLUE"
                self.b2_last_pressed_time = current_time
                self.right_glow_radius = 50
                self.right_glow_alpha = 200
                
                # Turn OFF physical Blue LED instantly on press and start cooldown
                self.esp32.send_command('b')
                self.is_in_cooldown = True
                self.cooldown_start_time = current_time
        
        # Global tracker for synchronous start triggers (usable on menu and game over screens)
        if (self.game_state == self.STATE_START_SCREEN or self.game_state == self.STATE_GAME_OVER):
            if hardware_input == "B1": self.b1_last_pressed_time = current_time
            elif hardware_input == "B2": self.b2_last_pressed_time = current_time
            
        both_buttons_held = (current_time - self.b1_last_pressed_time < self.sync_window) and \
                             (current_time - self.b2_last_pressed_time < self.sync_window)

        # Handle screen visual glow animations
        if self.left_glow_alpha > 0:
            self.left_glow_radius += 3  
            self.left_glow_alpha = max(0, self.left_glow_alpha - 8)  
        if self.right_glow_alpha > 0:
            self.right_glow_radius += 3
            self.right_glow_alpha = max(0, self.right_glow_alpha - 8)

        # --- FSM STATE LOGIC ---
        if self.game_state == self.STATE_START_SCREEN:
            self.current_bg = self.COLOR_BG_DEFAULT
            if both_buttons_held:
                self.b1_last_pressed_time = 0
                self.b2_last_pressed_time = 0
                self.score = 0
                self.is_in_cooldown = False
                self.input_phase_initialized = False
                self.esp32.send_command('X') # Ensure LEDs are completely OFF during initialization
                self.game_state = self.STATE_GENERATE_SEQUENCE
                time.sleep(0.4)

        elif self.game_state == self.STATE_GENERATE_SEQUENCE:
            self.target_sequence = [random.choice(["BLUE", "GREEN"]) for _ in range(self.max_score)]
            print(f"[GAME] Target Sequence: {self.target_sequence}")
            self.player_sequence = []
            self.flash_index = 0
            self.flash_start_time = current_time
            self.is_blank_period = False
            
            # Difficulty calculations
            score_factor = self.sleep_score / 100.0
            self.flash_duration = 0.4 + (1.1 * score_factor)
            self.flash_gap = 0.3 + (0.3 * score_factor)
            
            if self.sleep_score < 50:
                self.flicker_active = True
                self.flicker_frequency = 4 if self.sleep_score < 25 else 8
            else:
                self.flicker_active = False
                
            self.game_state = self.STATE_FLASH_SEQUENCE

        elif self.game_state == self.STATE_FLASH_SEQUENCE:
            elapsed = current_time - self.flash_start_time
            
            # Physical LEDs are kept forced OFF ('X') during the entire display phase
            # Screen noise flickering for fatigue emulation
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
            # Step A: Initialize Input Phase - Turn BOTH physical LEDs ON once
            if not self.input_phase_initialized:
                self.esp32.send_command('G')
                self.esp32.send_command('B')
                self.input_phase_initialized = True
                print("[SYS] Input Mode Active: Both physical indicators illuminated.")

            # Step B: Cooldown Management Loop
            if self.is_in_cooldown:
                if current_time - self.cooldown_start_time > self.cooldown_duration:
                    # Cooldown ended! Re-illuminate both indicators and unlock buttons
                    self.esp32.send_command('G')
                    self.esp32.send_command('B')
                    self.is_in_cooldown = False
                    print("[SYS] Cooldown expired. Peripheral locks released.")

            # Step C: Validate user input history sequence
            if input_triggered:
                self.player_sequence.append(input_triggered)
                current_step = len(self.player_sequence) - 1
                
                if self.player_sequence[current_step] == self.target_sequence[current_step]:
                    if len(self.player_sequence) == len(self.target_sequence):
                        self.score = self.max_score
                        self.esp32.send_command('X') # Extinguish everything on success
                        self.game_state = self.STATE_GAME_OVER
                else:
                    self.score = current_step
                    self.esp32.send_command('X') # Extinguish everything on failure
                    self.game_state = self.STATE_GAME_OVER

        elif self.game_state == self.STATE_GAME_OVER:
            if both_buttons_held:
                self.b1_last_pressed_time = 0
                self.b2_last_pressed_time = 0
                self.game_state = self.STATE_START_SCREEN
                time.sleep(0.4)

    def draw_transparent_circle(self, color, alpha, center, radius, width=0):
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*color, alpha), (radius, radius), radius, width)
        self.screen.blit(surface, (center[0] - radius, center[1] - radius))

    def render(self):
        self.screen.fill(self.current_bg)
        
        # 1. Render Ambient Background Layout Buttons
        self.draw_transparent_circle(self.RGB_GREEN, 40, (220, 300), 50, width=3)
        self.draw_transparent_circle(self.RGB_GREEN, 15, (220, 300), 47)
        self.draw_transparent_circle(self.RGB_BLUE, 40, (580, 300), 50, width=3)
        self.draw_transparent_circle(self.RGB_BLUE, 15, (580, 300), 47)
        self.draw_transparent_circle(self.RGB_CENTER, 30, (400, 300), 65, width=2)

        # 2. Render Dynamic Light Leaks
        if self.left_glow_alpha > 0 and self.left_glow_radius < self.max_glow_radius:
            self.draw_transparent_circle(self.RGB_GREEN, self.left_glow_alpha, (220, 300), self.left_glow_radius, width=4)
        if self.right_glow_alpha > 0 and self.right_glow_radius < self.max_glow_radius:
            self.draw_transparent_circle(self.RGB_BLUE, self.right_glow_alpha, (580, 300), self.right_glow_radius, width=4)

        # 3. Render Center Flashing Color Display
        if self.game_state == self.STATE_FLASH_SEQUENCE and not self.is_blank_period:
            if self.flash_index < len(self.target_sequence):
                active_color_str = self.target_sequence[self.flash_index]
                target_rgb = self.RGB_BLUE if active_color_str == "BLUE" else self.RGB_GREEN
                self.draw_transparent_circle(target_rgb, self.center_alpha, (400, 300), 60)

        # 4. UI Text Overlay Processing
        txt_sleep_info = self.font_small.render(f"System Load Profile: Sleep Score [{self.sleep_score}]", True, (120, 120, 130))
        self.screen.blit(txt_sleep_info, (20, 20))
        
        # Cooldown UI Feedback lock notification
        if self.game_state == self.STATE_PLAYER_INPUT and self.is_in_cooldown:
            txt_lock = self.font_small.render("[PERIPHERAL COOLDOWN ACTIVE - CHANNELS LOCKED]", True, (255, 100, 100))
            self.screen.blit(txt_lock, (220, 530))

        if self.game_state == self.STATE_START_SCREEN:
            txt_title = self.font_large.render("Cognitive Skill Evaluator", True, self.COLOR_WHITE)
            txt_prompt = self.font_small.render("Press BOTH physical buttons to initialize test", True, self.COLOR_WHITE)
            self.screen.blit(txt_title, (240, 120))
            self.screen.blit(txt_prompt, (235, 480))
            
        elif self.game_state == self.STATE_FLASH_SEQUENCE:
            txt_watch = self.font_large.render("Observe the Sequence", True, self.COLOR_WHITE)
            self.screen.blit(txt_watch, (260, 120))
            
        elif self.game_state == self.STATE_PLAYER_INPUT:
            txt_repeat = self.font_large.render("Replicate Inputs from Memory", True, self.COLOR_WHITE)
            txt_count = self.font_small.render(f"Step Tracker: {len(self.player_sequence)} / {self.max_score}", True, self.COLOR_WHITE)
            self.screen.blit(txt_repeat, (210, 120))
            self.screen.blit(txt_count, (340, 480))
            
        elif self.game_state == self.STATE_GAME_OVER:
            msg = "PERFORMANCE OPTIMAL" if self.score == self.max_score else "EVALUATION TERMINATED"
            txt_status = self.font_large.render(msg, True, self.COLOR_WHITE)
            txt_final = self.font_small.render(f"Calculated Score metrics: {self.score} / {self.max_score}", True, self.COLOR_WHITE)
            txt_restart = self.font_small.render("Synchronize BOTH buttons to restart system", True, self.COLOR_WHITE)
            
            self.screen.blit(txt_status, (230 if self.score == self.max_score else 220, 120))
            self.screen.blit(txt_final, (300, 290))
            self.screen.blit(txt_restart, (245, 480))
            
        pygame.display.flip()

    def cleanup(self):
        self.esp32.close()
        pygame.quit()

if __name__ == "__main__":
    game = MemoryGame()
    game.run()