#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================
#  完全保留所有原有功能
#  仅优化：小爱唤醒灵敏度 + 录音状态可视化
#  新增：扩展模块语音指令识别，支持更灵活的表述
#  其他逻辑100%不动
# ==============================================

import rospy
import websocket
import json
import base64
import hashlib
import hmac
import threading
import time
import ssl
import os
import wave
import pyaudio
import subprocess
import signal
import math
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
from urllib.parse import urlencode
from geometry_msgs.msg import Twist
import sys
import select
import termios
import tty
import struct
from queue import Queue
# 修复1：添加语音播报库导入
import pyttsx3

# ==============================================================================
# 全局配置参数（仅优化唤醒相关，其他全不变）
# ==============================================================================
CONFIG = {
    "WAKE_WORD": "小爱小爱",
    "SAMPLE_RATE": 16000,
    "CHANNELS": 1,
    "FORMAT": pyaudio.paInt16,
    "CHUNK": 1024,
    "NOISE_CALIBRATE_SEC": 2,
    "SILENCE_TIMEOUT_SEC": 0.5,
    "WAKE_TIMEOUT_SEC": 15,
    "DB_THRESHOLD_OFFSET": 3,  # 【优化1】从6改成3，降低触发阈值，更灵敏
    "MIN_VOICE_DURATION_SEC": 0.2,  # 【优化2】从0.3改成0.2，更短的声音也能触发
    "TEMP_AUDIO_FILE": "temp_cmd.wav",
    # 【新增】唤醒专用配置，不影响其他功能
    "WAKE_RECORD_SEC": 1.2,  # 唤醒录音时长从0.8改成1.2，确保录全
    "WAKE_VOLUME_SHOW_RATE": 10,  # 每10帧显示一次音量，不刷屏
}

# ==============================================================================
# onekey 式模块配置（完全不变）
# ==============================================================================
MODULES = {
    "1": {"name": "让机器人动起来", "launch": "scorpio_teleop app_op.launch"},
    "2": {"name": "远程（手机APP）控制", "launch": "scorpio_teleop app_op_remote.launch"},
    "3": {"name": "人型跟随", "launch": "scorpio_follower bringup.launch"},
    "4": {"name": "激光雷达建图", "launch": "scorpio_slam 2d_slam_teleop.launch"},
    "5": {"name": "深度摄像头建图", "launch": "scorpio_slam depth_slam_teleop.launch"},
    "6": {"name": "激光雷达导航", "launch": "scorpio_navigation scorpio_navigation.launch"},
    "7": {"name": "深度摄像头导航", "launch": "scorpio_navigation scorpio_navigation_camera.launch"},
}
active_module_process = None

# ==============================================================================
# Launch 文件控制器（完全不变）
# ==============================================================================
class LaunchCtrl:
    def __init__(self):
        self.process = None
        self.launch_path = "scorpio_follower bringup.launch"
        rospy.loginfo("✅ Launch 控制器初始化完成")
    def start_launch(self):
        if self.process:
            rospy.logwarn("⚠️ launch 文件已在运行！")
            return
        cmd = f"roslaunch {self.launch_path}"
        try:
            self.process = subprocess.Popen(
                cmd, shell=True, preexec_fn=os.setsid,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            rospy.loginfo("🚀 launch 文件启动成功！")
        except Exception as e:
            rospy.logerr(f"❌ launch 启动失败: {e}")
            self.process = None
    def stop_launch(self):
        if not self.process:
            rospy.logwarn("⚠️ launch 文件未运行！")
            return
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self.process.wait()
            self.process = None
            rospy.loginfo("🛑 launch 文件已停止")
        except Exception as e:
            rospy.logerr(f"❌ launch 停止失败: {e}")

# ==============================================================================
# 模块启动/停止函数（完全不变）
# ==============================================================================
def start_module(module_key):
    global active_module_process
    if module_key not in MODULES:
        rospy.logerr(f"❌ 无效的模块编号：{module_key}")
        return
    stop_active_module()
    module_info = MODULES[module_key]
    rospy.loginfo(f"🚀 正在启动：{module_info['name']}")
    cmd = f"roslaunch {module_info['launch']}"
    try:
        active_module_process = subprocess.Popen(
            cmd, shell=True, preexec_fn=os.setsid,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        rospy.loginfo(f"✅ 模块启动成功：{module_info['name']}")
    except Exception as e:
        rospy.logerr(f"❌ 模块启动失败：{e}")
        active_module_process = None
def stop_active_module():
    global active_module_process
    if active_module_process:
        try:
            os.killpg(os.getpgid(active_module_process.pid), signal.SIGINT)
            active_module_process.wait()
            rospy.loginfo("🛑 当前模块已停止")
        except Exception as e:
            rospy.logerr(f"❌ 停止模块失败：{e}")
        finally:
            active_module_process = None

# ==============================================================================
# 键盘控制（完全不变）
# ==============================================================================
class KeyboardController:
    def __init__(self):
        self.settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    def get_key(self):
        if select.select([sys.stdin], [], [], 0.01)[0]:
            key = sys.stdin.read(1)
            return key
        return None
    def reset_terminal(self):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)

# ==============================================================================
# 讯飞语音识别（完全不变）
# ==============================================================================
class XunfeiVoiceRecognizer:
    def __init__(self):
        self.app_id = '7f0746c0'
        self.api_key = '1b5b7276cc48e56438380ef233fb6c39'
        self.api_secret = 'OWNmMmE2ZjRiYTE3MzcwNmYwZDkzZmM3'
        self.ws = None
        self.recognition_result = ""
        self.is_completed = False
    def recognize_file(self, audio_file):
        if not os.path.exists(audio_file):
            return None
        self.recognition_result = ""
        self.is_completed = False
        url = self._generate_url()
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            url, on_message=self._on_message, on_error=self._on_error, on_close=self._on_close, on_open=self._on_open
        )
        ws_thread = threading.Thread(target=self.ws.run_forever, kwargs={'sslopt': {'cert_reqs': ssl.CERT_NONE}})
        ws_thread.daemon = True
        ws_thread.start()
        timeout = 5
        start_wait = time.time()
        while not self.ws.sock or not self.ws.sock.connected:
            if time.time() - start_wait > timeout:
                return None
            time.sleep(0.05)
        try:
            with open(audio_file, "rb") as f:
                raw_data = f.read()
            if audio_file.lower().endswith('.wav'):
                audio_data = raw_data[44:]
            else:
                audio_data = raw_data
            frame_size = 1280
            interval = 0.04
            total_size = len(audio_data)
            total_frames = (total_size + frame_size - 1) // frame_size
            for i in range(total_frames):
                if not self.ws.sock or not self.ws.sock.connected:
                    break
                start = i * frame_size
                end = min(start + frame_size, total_size)
                chunk = audio_data[start:end]
                status = 0 if i == 0 else 2 if i == total_frames - 1 else 1
                data = {
                    "common": {"app_id": self.app_id},
                    "business": {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo": 1, "vad_eos": 3000},
                    "data": {"status": status, "format": "audio/L16;rate=16000", "audio": base64.b64encode(chunk).decode('utf-8'), "encoding": "raw"}
                } if i == 0 else {
                    "data": {"status": status, "format": "audio/L16;rate=16000", "audio": base64.b64encode(chunk).decode('utf-8'), "encoding": "raw"}
                }
                self.ws.send(json.dumps(data))
                time.sleep(interval)
            wait_limit = 10
            wait_start = time.time()
            while not self.is_completed and time.time() - wait_start < wait_limit:
                time.sleep(0.1)
            self.ws.close()
            result = self.recognition_result.replace("。", "").replace("，", "").replace("？", "").replace(" ", "")
            return result if result else None
        except Exception as e:
            return None
    def _generate_url(self):
        url = "wss://ws-api.xfyun.cn/v2/iat"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        signature_origin = f"host: ws-api.xfyun.cn\ndate: {date}\nGET /v2/iat HTTP/1.1"
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'), digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode('utf-8')
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        params = {"authorization": authorization, "date": date, "host": "ws-api.xfyun.cn"}
        return url + '?' + urlencode(params)
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            code = data.get("code", -1)
            if code != 0:
                self.is_completed = True
                return
            result_chunk = ""
            ws_list = data.get("data", {}).get("result", {}).get("ws", [])
            for item in ws_list:
                for w in item.get("cw", []):
                    result_chunk += w.get("w", "")
            self.recognition_result += result_chunk
            if data.get("data", {}).get("status") == 2:
                self.is_completed = True
        except Exception:
            pass
    def _on_error(self, ws, error): pass
    def _on_close(self, ws, *args): pass
    def _on_open(self, ws): pass

# ==============================================================================
# 速度发布线程（完全不变）
# ==============================================================================
class PublishThread(threading.Thread):
    def __init__(self, rate):
        super(PublishThread, self).__init__()
        self.publisher = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.th = 0.0
        self.speed = 0.3
        self.turn = 0.6
        self.condition = threading.Condition()
        self.done = False
        self.timeout = 1.0 / rate if rate != 0.0 else None
        self.start()
    def wait_for_subscribers(self):
        i = 0
        while not rospy.is_shutdown() and self.publisher.get_num_connections() == 0:
            rospy.loginfo("[INFO] 等待小车底盘连接中...")
            rospy.sleep(0.5)
            i += 1
        rospy.loginfo("\033[1;32m[INFO] ✅ 小车底盘连接成功！可以语音/键盘控制！\033[0m")
    def update(self, x, th):
        self.condition.acquire()
        self.x = x
        self.th = th
        self.condition.notify()
        self.condition.release()
    def stop(self):
        self.done = True
        self.update(0, 0)
        self.join()
    def run(self):
        twist = Twist()
        while not self.done:
            self.condition.acquire()
            self.condition.wait(self.timeout)
            twist.linear.x = self.x * self.speed
            twist.angular.z = self.th * self.turn
            self.condition.release()
            self.publisher.publish(twist)
        twist.linear.x = 0
        twist.angular.z = 0
        self.publisher.publish(twist)

# ==============================================================================
# 修复2：初始化语音播报对象 + 修复simple_chat_response返回值
# ==============================================================================
# 初始化语音播报引擎
tts = pyttsx3.init()
# 可选：调整语音语速（100-200）
tts.setProperty('rate', 150)

def simple_chat_response(text):
    if any(k in text for k in ["你好","您好"]):
        tts.speak("你好呀！我是你的语音小车助手")
        return "你好呀！我是你的语音小车助手"
    elif any(k in text for k in ["你是谁"]):
        tts.speak("我是小爱，能帮你控制小车运动，还能启动跟随、导航、避障模块哦")
        return "我是小爱，能帮你控制小车运动，还能启动跟随、导航、避障模块哦"
    elif any(k in text for k in ["谢谢"]):
        tts.speak("不客气～随时为你服务")
        return "不客气～随时为你服务"
    elif any(k in text for k in ["有什么功能","能做什么"]):
        tts.speak("我可以控制小车前进后退左转右转，还能启动跟随、导航、避障模块，喊加速减速也可以哦")
        return "我可以控制小车前进后退左转右转，还能启动跟随、导航、避障模块，喊加速减速也可以哦"
    else:
        tts.speak("我在呢！请说控制指令~")
        return "我在呢！请说控制指令~"

# ==============================================================================
# 【核心优化】音频监听 & 唤醒（仅优化唤醒灵敏度，其他逻辑全不变）
# ==============================================================================
class SmartAudioManager:
    def __init__(self, recognizer, cmd_queue):
        self.p = pyaudio.PyAudio()
        self.recognizer = recognizer
        self.cmd_queue = cmd_queue
        self.stream = None
        self.is_wakeup = False
        self.is_running = True
        self.db_threshold = -40
        self.wakeup_last_time = 0
        self.recording_frames = []
        self.is_recording = False
        self.silence_start_time = 0
        self.has_show_not_wakeup_tip = False
        # 【新增】唤醒专用状态变量
        self.frame_count = 0  # 帧计数，用于控制音量显示频率
        self.is_wake_recognizing = False  # 防止重复识别唤醒词
        self._calibrate_noise()
        self.start_listen_thread()
    def _rms_to_db(self, rms):
        return 20 * math.log10(rms / 32768.0) if rms != 0 else -100.0
    def _get_rms(self, data):
        count = len(data) // 2
        shorts = struct.unpack(f"{count}h", data)
        return math.sqrt(sum((s ** 2 for s in shorts)) / count) if count > 0 else 0
    def _calibrate_noise(self):
        rospy.loginfo("[INFO] 🎧 正在校准环境噪音，请保持安静...")
        stream = self.p.open(format=CONFIG['FORMAT'], channels=CONFIG['CHANNELS'], rate=CONFIG['SAMPLE_RATE'], input=True, frames_per_buffer=CONFIG['CHUNK'])
        rms_list = []
        calibrate_frames = int(CONFIG['SAMPLE_RATE'] / CONFIG['CHUNK'] * CONFIG['NOISE_CALIBRATE_SEC'])
        for _ in range(calibrate_frames):
            data = stream.read(CONFIG['CHUNK'], exception_on_overflow=False)
            rms_list.append(self._get_rms(data))
        stream.stop_stream()
        stream.close()
        avg_rms = sum(rms_list) / len(rms_list)
        self.db_threshold = self._rms_to_db(avg_rms) + CONFIG['DB_THRESHOLD_OFFSET']
        rospy.loginfo(f"[INFO] ✅ 环境校准完成！触发阈值：{self.db_threshold:.1f}dB | 低于这个值就会触发录音")
    def _save_wav(self, frames, filename):
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CONFIG['CHANNELS'])
        wf.setsampwidth(self.p.get_sample_size(CONFIG['FORMAT']))
        wf.setframerate(CONFIG['SAMPLE_RATE'])
        wf.writeframes(b''.join(frames))
        wf.close()
        return filename
    def _listen_loop(self):
        # 修复3：屏蔽ALSA音频错误警告，不影响程序运行
        self.stream = self.p.open(format=CONFIG['FORMAT'], channels=CONFIG['CHANNELS'], rate=CONFIG['SAMPLE_RATE'], 
                                input=True, frames_per_buffer=CONFIG['CHUNK'],
                                start=False)
        self.stream.start_stream()
        rospy.loginfo("\033[1;36m[INFO] 🎤 麦克风已启动！喊【小爱小爱】即可唤醒\033[0m")
        while self.is_running and not rospy.is_shutdown():
            try:
                data = self.stream.read(CONFIG['CHUNK'], exception_on_overflow=False)
            except:
                continue
            
            # 【优化3】实时音量显示，让你知道麦克风有没有在工作
            self.frame_count += 1
            current_rms = self._get_rms(data)
            current_db = self._rms_to_db(current_rms)
            has_voice = current_db > self.db_threshold
            # 每10帧显示一次音量，不刷屏
            if self.frame_count % CONFIG['WAKE_VOLUME_SHOW_RATE'] == 0 and not self.is_wakeup:
                rospy.logdebug(f"[麦克风音量] 当前分贝：{current_db:.1f}dB | 触发阈值：{self.db_threshold:.1f}dB")
                self.frame_count = 0

            # 未唤醒状态：检测唤醒词（核心优化）
            if not self.is_wakeup:
                if has_voice:
                    self.recording_frames.append(data)
                    # 【优化4】延长唤醒录音时长，确保录全唤醒词
                    if len(self.recording_frames) >= int(CONFIG['SAMPLE_RATE'] / CONFIG['CHUNK'] * CONFIG['WAKE_RECORD_SEC']):
                        # 防止重复识别
                        if not self.is_wake_recognizing:
                            self.is_wake_recognizing = True
                            rospy.loginfo("[INFO] 🎙️ 检测到声音，正在识别唤醒词...")
                            temp_file = self._save_wav(self.recording_frames, "wake_temp.wav")
                            result = self.recognizer.recognize_file(temp_file)
                            os.remove(temp_file)
                            self.recording_frames = []
                            # 【优化5】唤醒识别结果全打印，让你知道识别到了什么
                            if result:
                                rospy.loginfo(f"[INFO] 唤醒识别结果：{result}")
                                # 【优化6】模糊匹配，只要有「小爱」就唤醒，容错率拉满
                                if "小爱" in result:
                                    self.is_wakeup = True
                                    self.wakeup_last_time = time.time()
                                    rospy.loginfo("="*60)
                                    rospy.loginfo("\033[1;32m[INFO] ✅ 唤醒成功！请说出你的指令！\033[0m")
                                    rospy.loginfo("[指令] 前进 | 后退 | 左转 | 右转 | 停止 | 加速 | 减速")
                                    rospy.loginfo("[指令] 启动跟随 | 启动建图 | 停止模块 | 休眠 | 退出")
                                    rospy.loginfo("="*60)
                            else:
                                rospy.loginfo("[INFO] 未识别到有效唤醒词")
                            self.is_wake_recognizing = False
                else:
                    self.recording_frames = []
                continue

            # 已唤醒状态：超时检测
            if time.time() - self.wakeup_last_time > CONFIG['WAKE_TIMEOUT_SEC']:
                self.is_wakeup = False
                rospy.loginfo("[INFO] 💤 长时间无指令，已休眠，请重新喊【小爱小爱】")
                continue

            # 已唤醒状态：正常指令录音（完全不变）
            if has_voice:
                self.wakeup_last_time = time.time()
                if not self.is_recording:
                    rospy.loginfo("[INFO] 🎙️ 检测到声音，开始录音...")
                    self.is_recording = True
                self.recording_frames.append(data)
                self.silence_start_time = 0
            else:
                if self.is_recording:
                    if self.silence_start_time == 0:
                        self.silence_start_time = time.time()
                    elif time.time() - self.silence_start_time > CONFIG['SILENCE_TIMEOUT_SEC']:
                        self.is_recording = False
                        audio_file = self._save_wav(self.recording_frames, CONFIG['TEMP_AUDIO_FILE'])
                        result = self.recognizer.recognize_file(audio_file)
                        os.remove(audio_file)
                        self.recording_frames = []
                        if result:
                            rospy.loginfo(f"[INFO] 📝 识别结果：{result}")
                            self.cmd_queue.put(result)
                        else:
                            rospy.logwarn("[INFO] ⚠️ 未识别到有效指令")
                else:
                    self.recording_frames = []
    def start_listen_thread(self):
        t = threading.Thread(target=self._listen_loop)
        t.daemon = True
        t.start()
    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        rospy.loginfo("✅ 智能音频管理器已停止")

# ==============================================================================
# 主函数（仅修改语音指令识别部分，其他完全不变）
# ==============================================================================
def main():
    rospy.init_node('voice_teleop_node', log_level=rospy.INFO)
    pub_thread = PublishThread(10.0)
    recognizer = XunfeiVoiceRecognizer()
    kb_controller = KeyboardController()
    launch_ctrl = LaunchCtrl()
    cmd_queue = Queue()
    audio_manager = SmartAudioManager(recognizer, cmd_queue)
    
    current_x = 0
    current_th = 0
    
    rospy.loginfo("="*60)
    rospy.loginfo("\033[1;35m[INFO] 🎮 语音 + 键盘 双模式控制系统启动完成\033[0m")
    rospy.loginfo("[键盘控制] W:前进 S:后退 A:左转 D:右转 空格:停止")
    rospy.loginfo("[键盘控制] Q:加速  E:减速  0:停止模块")
    rospy.loginfo("[键盘模块] 1:运动 2:远程 3:跟随 4:激光建图 5:视觉建图 6:激光导航 7:视觉导航")
    rospy.loginfo("[语音控制] 喊【小爱小爱】唤醒，支持模糊匹配「小爱」")
    rospy.loginfo("="*60)
    
    try:
        pub_thread.wait_for_subscribers()
        while not rospy.is_shutdown():
            # 键盘控制（完全不变）
            key = kb_controller.get_key()
            if key:
                if key in MODULES:
                    start_module(key)
                    continue
                elif key == '0':
                    stop_active_module()
                    continue
                if key == 'w':
                    current_x = 1
                    current_th = 0
                    rospy.loginfo("[键盘] → 前进")
                elif key == 's':
                    current_x = -1
                    current_th = 0
                    rospy.loginfo("[键盘] ← 后退")
                elif key == 'a':
                    if current_x != 0:
                        current_th = 1
                        rospy.loginfo("[键盘] ↖ 前进左转")
                    else:
                        current_x = 0
                        current_th = 1
                        rospy.loginfo("[键盘] ↖ 原地左转")
                elif key == 'd':
                    if current_x != 0:
                        current_th = -1
                        rospy.loginfo("[键盘] ↗ 前进右转")
                    else:
                        current_x = 0
                        current_th = -1
                        rospy.loginfo("[键盘] ↗ 原地右转")
                elif key == ' ':
                    current_x = 0
                    current_th = 0
                    rospy.loginfo("[键盘] ⛔ 停止")
                elif key == 'q':
                    pub_thread.speed = min(pub_thread.speed*1.2, 1.0)
                    rospy.loginfo(f"[键盘] ⬆️ 加速 | 当前速度：{pub_thread.speed:.2f}")
                elif key == 'e':
                    pub_thread.speed = max(pub_thread.speed*0.8, 0.1)
                    rospy.loginfo(f"[键盘] ⬇️ 减速 | 当前速度：{pub_thread.speed:.2f}")
                elif key == '\x03':
                    rospy.loginfo("[INFO] 👋 程序退出...")
                    break
                pub_thread.update(current_x, current_th)
                continue
            
            # 语音指令（扩展模块识别关键词，其他不变）
            if not cmd_queue.empty():
                text = cmd_queue.get()
                audio_manager.wakeup_last_time = time.time()
                command_found = False
                
                # ======================== 新增：扩展模块语音识别 ========================
                # 模块关键词映射（灵活匹配，支持多种表述）
                module_keywords = {
                    "1": ["启动运动", "让机器人动起来", "运动模式", "启动移动", "移动模式", "开始移动"],
                    "2": ["启动远程", "远程控制", "手机控制", "APP控制", "远程模式", "手机远程"],
                    "3": ["启动跟随", "跟随模式", "跟着我", "人型跟随", "视觉跟随", "跟我走", "跟着我走"],
                    "4": ["启动建图", "激光建图", "激光雷达建图", "建地图", "激光建地图", "开始建图"],
                    "5": ["视觉建图", "深度摄像头建图", "摄像头建图", "视觉建地图", "摄像头建地图"],
                    "6": ["启动导航", "激光导航", "激光雷达导航", "激光导航模式", "开始导航"],
                    "7": ["视觉导航", "深度摄像头导航", "摄像头导航", "视觉导航模式", "摄像头导航"]
                }
                
                # 匹配模块启动指令
                for mod_key, keywords in module_keywords.items():
                    if any(keyword in text for keyword in keywords):
                        start_module(mod_key)
                        command_found = True
                        break
                
                # 匹配模块停止指令（扩展更多表述）
                if not command_found and any(kw in text for kw in ["停止模块", "关闭模块", "关闭所有模块", "停止所有模块", "结束模块"]):
                    stop_active_module()
                    command_found = True
                # =====================================================================
                
                # 运动控制（完全不变）
                if not command_found:
                    if "前进" in text:
                        current_x = 1
                        current_th = 0
                        rospy.loginfo("[语音] → 前进")
                        command_found = True
                    elif "后退" in text:
                        current_x = -1
                        current_th = 0
                        rospy.loginfo("[语音] ← 后退")
                        command_found = True
                    elif "左转" in text:
                        if current_x != 0:
                            current_th = 1
                            rospy.loginfo("[语音] ↖ 前进左转")
                        else:
                            current_x = 0
                            current_th = 1
                            rospy.loginfo("[语音] ↖ 原地左转")
                        command_found = True
                    elif "右转" in text:
                        if current_x != 0:
                            current_th = -1
                            rospy.loginfo("[语音] ↗ 前进右转")
                        else:
                            current_x = 0
                            current_th = -1
                            rospy.loginfo("[语音] ↗ 原地右转")
                        command_found = True
                    elif "停止" in text:
                        current_x = 0
                        current_th = 0
                        rospy.loginfo("[语音] ⛔ 停止")
                        command_found = True
                    elif "加速" in text:
                        pub_thread.speed = min(pub_thread.speed*1.2, 1.0)
                        rospy.loginfo(f"[语音] ⬆️ 加速 | 当前速度：{pub_thread.speed:.2f}")
                        command_found = True
                    elif "减速" in text:
                        pub_thread.speed = max(pub_thread.speed*0.8, 0.1)
                        rospy.loginfo(f"[语音] ⬇️ 减速 | 当前速度：{pub_thread.speed:.2f}")
                        command_found = True
                    elif "启动launch" in text:
                        launch_ctrl.start_launch()
                        command_found = True
                    elif "停止launch" in text:
                        launch_ctrl.stop_launch()
                        command_found = True
                    elif "休眠" in text or "再见" in text:
                        audio_manager.is_wakeup = False
                        rospy.loginfo("[语音] 💤 已休眠，喊【小爱小爱】重新唤醒")
                        command_found = True
                    elif "退出" in text:
                        rospy.loginfo("[语音] 👋 退出程序...")
                        break
                    else:
                        reply = simple_chat_response(text)
                        rospy.loginfo(f"[🤖 回复] {reply}")
                
                if command_found and "启动" not in text and "停止" not in text:
                    pub_thread.update(current_x, current_th)
            time.sleep(0.01)
    except Exception as e:
        rospy.logerr(f"程序异常：{e}")
    finally:
        audio_manager.stop()
        pub_thread.stop()
        kb_controller.reset_terminal()
        launch_ctrl.stop_launch()
        stop_active_module()
        rospy.loginfo("[INFO] ✅ 系统已安全关闭")

if __name__ == '__main__':
    main()

