import requests
import json
import uuid
import os

class TwitchRewardSender:
    def __init__(self, oauth_token, streamer_name):
        self.base_url = "https://gql.twitch.tv/gql"
        self.oauth_token = oauth_token
        self.streamer_name = streamer_name
        self.channel_id = None
        self.rewards_dir = 'rewards'
        self.rewards = []
        
        self.headers = {
            'authorization': oauth_token
        }
        
    def generate_transaction_id(self):
        """Генерирует уникальный ID транзакции"""
        return str(uuid.uuid4()).replace('-', '')

    def _create_rewards_directory(self):
        """Создает директорию rewards, если она не существует"""
        try:
            if not os.path.exists(self.rewards_dir):
                os.makedirs(self.rewards_dir)
            return True
        except Exception as e:
            print(f"❌ Ошибка создания директории {self.rewards_dir}: {e}")
            return False


    def fetch_channel_rewards(self):
        """Получает все доступные награды канала через ChannelPointsContext"""
        if not self.streamer_name:
            print("⚠️ streamer_name не указан — пропускаем получение наград")
            return None
            
        payload = [{
            "operationName": "ChannelPointsContext",
            "variables": {
                "channelLogin": self.streamer_name,
                "includeGoalTypes": ["CREATOR", "BOOST"]
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "7fe050e3761eb2cf258d70ee1a21cbd76fa8cf3d7e7b12fc437e7029d446b5e3"
                }
            }
        }]
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"❌ Ошибка получения наград: {response.status_code}")
                return None
                
            data = response.json()
            
            # Извлекаем community id и rewards
            try:
                community = data[0]['data']['community']
                channel_id = community['id']
                self.channel_id = channel_id

                channel = community.get('channel', {})
                community_points_settings = channel.get('communityPointsSettings', {})
                
                # Получаем кастомные награды
                custom_rewards = community_points_settings.get('customRewards', [])
                
                # Также можно получить автоматические награды, если нужно
                automatic_rewards = community_points_settings.get('automaticRewards', [])
                
                print(f"✅ Получено {len(custom_rewards)} кастомных наград для канала {self.streamer_name} (ID: {channel_id})")
                
                # Формируем структуру для сохранения
                rewards_list = []
                for reward in custom_rewards:
                    if reward.get('isEnabled', False):
                        rewards_list.append({
                            "id": reward.get('id'),
                            "title": reward.get('title'),
                            "prompt": reward.get('prompt'),
                            "cost": reward.get('cost')
                        })

                self.rewards = rewards_list

                
            except (KeyError, IndexError, TypeError) as e:
                print(f"❌ Ошибка парсинга ответа: {e}")
                print(f"Ответ: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ Исключение при запросе наград: {e}")
            return None
    
    def save_rewards_to_file(self):
        """Сохраняет награды в JSON-файл с именем стримера"""

        self._create_rewards_directory()

        filename = f"{self.streamer_name}.json"
        filepath = os.path.join(self.rewards_dir, filename)

        rewards_data = {
            "streamer": self.streamer_name,
            "id": self.channel_id,
            "rewards": self.rewards
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(rewards_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения файла: {e}")
            return False

    def load_rewards_from_file(self):
        """Загружает награды из JSON-файла в директории rewards"""
        
        filepath = os.path.join(self.rewards_dir, f"{self.streamer_name}.json")
        
        if not os.path.exists(filepath):
            print(f"❌ Файл не найден: {filepath}")
            return None
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.rewards = data['rewards']
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            return None

    def list_available_rewards(self):
        """Выводит список доступных наград"""
        if len(self.rewards) == 0:
            print("❌ Список наград пустой")
            return

        for i, reward in enumerate(self.rewards, 1):
            print(f"{i:2}. Название: {reward['title']}, стоимость: {reward['cost']}")
        
    def send_reward(self, reward, count):
        for _ in range(count):
            transaction_id = self.generate_transaction_id()
            
            payload = [{
                "operationName": "RedeemCustomReward",
                "variables": {
                    "input": {
                        "channelID": str(self.channel_id),
                        "cost": reward["cost"],
                        "pricingType": "POINTS",
                        "prompt": reward["prompt"],
                        "rewardID": reward["reward_id"],
                        "title": reward["title"],
                        "transactionID": transaction_id
                    }
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "d56249a7adb4978898ea3412e196688d4ac3cea1c0c2dfd65561d229ea5dcc42"
                    }
                }
            }]
            
            try:
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return True, result
                else:
                    print(f"  Ошибка: {response.text[:200]}")
                    return False, None
                    
            except Exception as e:
                print(f"  Исключение: {str(e)}")
                return False, None