# core.py - TRULY FINAL VERSION

import socket
import threading
import json
import uuid
import time
import ollama

class Node:
    def __init__(self, host, port, peers, app_interface):
        self.host = host
        self.port = port
        self.peers = peers
        self.app = app_interface
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []
        self.lock = threading.Lock()
        self.seen_messages = set()

    def start_networking(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.app.log_message(f"Node listening on {self.host}:{self.port}")

        listen_thread = threading.Thread(target=self.listen_for_connections, daemon=True)
        listen_thread.start()

        connect_thread = threading.Thread(target=self.connect_to_peers, daemon=True)
        connect_thread.start()

    def listen_for_connections(self):
        while True:
            try:
                conn, addr = self.socket.accept()
                self.app.log_message(f"Accepted connection from {addr}")
                with self.lock:
                    self.connections.append(conn)
                handler_thread = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                handler_thread.start()
            except Exception:
                break

    def connect_to_peers(self):
        time.sleep(1)
        for peer_port in self.peers:
            if not self.app.is_running:
                break
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((self.host, peer_port))
                self.app.log_message(f"Successfully connected to {self.host}:{peer_port}")
                with self.lock:
                    self.connections.append(peer_socket)
                handler_thread = threading.Thread(target=self.handle_client, args=(peer_socket, (self.host, peer_port)), daemon=True)
                handler_thread.start()
            except Exception as e:
                self.app.log_message(f"[WARNING] Could not connect to peer {peer_port}: {e}")

    def handle_client(self, conn, addr):
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                message_packet = json.loads(data.decode('utf-8'))
                message_id = message_packet['id']
                message_content = message_packet['content']

                with self.lock:
                    if message_id in self.seen_messages:
                        continue
                    self.seen_messages.add(message_id)

                if message_content.startswith('!sos'):
                    self.app.log_message(f"[AI] Received SOS command. Processing...")
                    ai_thread = threading.Thread(target=self._process_sos_command, args=(message_content,), daemon=True)
                    ai_thread.start()
                elif message_content == '!quit':
                    self.app.log_message(f"[SYSTEM] Quit command received. Shutting down.")
                    self.app.call_from_thread(self.app.exit)
                else:
                    self.app.log_message(f"[RECV] ({message_id[:4]}): {message_content}")
                    self.broadcast(message_packet, origin_conn=conn)
            except Exception:
                break

        with self.lock:
            if conn in self.connections:
                self.connections.remove(conn)
        conn.close()
        self.app.log_message(f"Connection with {addr} closed.")

    def _process_sos_command(self, sos_content: str):
        try:
            prompt = sos_content[5:]
            system_prompt = "You are a rescue coordinator AI. Your task is to receive a distress message, analyze it, and convert it into a structured JSON object. The JSON object must have keys for 'priority', 'summary', and 'first_aid'. Respond ONLY with the JSON object."

            response = ollama.chat(
                model='gemma:2b',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ]
            )

            ai_response_string = response['message']['content']
            
            try:
                clean_json_string = ai_response_string.strip().replace('```json', '').replace('```', '')
                ai_json_object = json.loads(clean_json_string)
                formatted_content = json.dumps(ai_json_object, indent=4)
            except json.JSONDecodeError:
                formatted_content = ai_response_string

            new_message_packet = {
                "id": str(uuid.uuid4()),
                "content": formatted_content
            }

            with self.lock:
                self.seen_messages.add(new_message_packet['id'])
            
            self.app.log_message(f"[AI RESULT] ({new_message_packet['id'][:4]}): \n{formatted_content}")
            self.app.log_message(f"[AI] Task complete. Broadcasting smart beacon.")
            self.broadcast(new_message_packet)

        except Exception as e:
            self.app.log_message(f"[AI ERROR] Could not process command: {e}")

    def broadcast(self, message_packet, origin_conn=None):
        with self.lock:
            for conn in self.connections:
                if conn != origin_conn:
                    try:
                        conn.sendall(json.dumps(message_packet).encode('utf-8'))
                    except Exception:
                        pass

    def submit_message(self, content):
        """Called by the UI to create and broadcast a user's message."""
        message_packet = {"id": str(uuid.uuid4()), "content": content}
        with self.lock:
            self.seen_messages.add(message_packet['id'])
        self.broadcast(message_packet)