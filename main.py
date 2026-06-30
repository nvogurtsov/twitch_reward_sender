import requests
import json
import uuid
import os
import time


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
                print(f"✅ Получено {len(automatic_rewards)} автоматических наград")
                
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

                return {
                    "streamer": self.streamer_name,
                    "id": channel_id,
                    "rewards": rewards_list
                }
                
            except (KeyError, IndexError, TypeError) as e:
                print(f"❌ Ошибка парсинга ответа: {e}")
                print(f"Ответ: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ Исключение при запросе наград: {e}")
            return None
    
    def save_rewards_to_file(self, rewards_data):
        """Сохраняет награды в JSON-файл с именем стримера"""
        if not rewards_data:
            return False

        self._create_rewards_directory()

        filename = f"{self.streamer_name}.json"
        filepath = os.path.join(self.rewards_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(rewards_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения файла: {e}")
            return False

    def load_rewards_from_file(self, filename):
        """Загружает награды из JSON-файла в директории rewards"""

        if not filename:
            print("Пустое имя стримера")
            return None
        
        filepath = os.path.join(self.rewards_dir, f"{filename}.json")
        
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
            print(f"{i:2}. {reward['title']}: {reward['cost']}")        
        
    
    def send_reward_old(self, reward_id, title, cost=200, prompt=None):
        if not self.channel_id:
            print("❌ Ошибка: channel_id не установлен. Сначала вызовите fetch_channel_rewards()")
            return False, None
            
        transaction_id = self.generate_transaction_id()
        
        payload = [{
            "operationName": "RedeemCustomReward",
            "variables": {
                "input": {
                    "channelID": str(self.channel_id),
                    "cost": cost,
                    "pricingType": "POINTS",
                    "prompt": prompt,
                    "rewardID": reward_id,
                    "title": title,
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
                print(f"  Успех!")
                return True, result
            else:
                print(f"  Ошибка: {response.text[:200]}")
                return False, None
                
        except Exception as e:
            print(f"  Исключение: {str(e)}")
            return False, None

    def send_reward(self, title, count):
        for _ in range(count):
            transaction_id = self.generate_transaction_id()
            
            payload = [{
                "operationName": "RedeemCustomReward",
                "variables": {
                    "input": {
                        "channelID": str(self.channel_id),
                        "cost": cost,
                        "pricingType": "POINTS",
                        "prompt": prompt,
                        "rewardID": reward_id,
                        "title": title,
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
                    print(f"  Успех!")
                    return True, result
                else:
                    print(f"  Ошибка: {response.text[:200]}")
                    return False, None
                    
            except Exception as e:
                print(f"  Исключение: {str(e)}")
                return False, None


# ============== ИСПОЛЬЗОВАНИЕ ==============

def load_config():
    """Загружает конфигурацию из config.json"""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"Ошибка: Файл {config_path} не найден!")
        print("Создайте config.json на основе config.example.json")
        exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Проверяем наличие токена
        if not config.get('OAUTH_TOKEN') or config['OAUTH_TOKEN'] == "twitch-oauth-token-here":
            print("Ошибка: Укажите реальный OAUTH_TOKEN в config.json!")
            exit(1)

        # ИСПРАВЛЕНО - правильная проверка STREAMER_NAME
        if not config.get('STREAMER_NAME') or config['STREAMER_NAME'] == "streamer-name-here":
            print("Ошибка: В config.json должен быть указан STREAMER_NAME")
            exit(1)
        
        return config
    except Exception as e:
        print(f"Ошибка при чтении config.json: {e}")
        exit(1)


def main():
    config = load_config()
    
    OAUTH_TOKEN = config['OAUTH_TOKEN']
    STREAMER_NAME = config['STREAMER_NAME']
    
    # Инициализация
    sender = TwitchRewardSender(OAUTH_TOKEN, STREAMER_NAME)

    # === Получение наград (обязательно перед отправкой) ===
    # rewards_data = sender.fetch_channel_rewards()
    # if rewards_data:
    #     sender.save_rewards_to_file(rewards_data)
    #     print(f"📋 Найдены награды: {len(rewards_data['rewards'])}")
    # else:
    #     print("❌ Не удалось получить награды")
    #     return

    sender.load_rewards_from_file(STREAMER_NAME)
    sender.list_available_rewards()

    # Отправка наград
    sender.send_reward(1, 5)
    #     if sender.channel_id == "510819602":
    #         sender.send_reward(reward_id='346cf41e-c202-4300-a2f6-4e0527a82063', title='хи-хи', cost=200)
    #         # sender.send_reward(reward_id='148c57a6-1c36-4834-80e4-5f3d92bb260b', title='LEROLEROLERO', cost=500)
    #     elif sender.channel_id == "109840796":
    #         sender.send_reward(reward_id='e00e1d4e-62cd-4502-9896-7756d41e938e', title='!Боже_мой', prompt='Да боже мой, да всем насрать', cost=300)
    #         # sender.send_reward(reward_id='8ac974de-1e97-44b1-803b-b325faa79c0c', title='!Где_враги', prompt='НУУУУ ГДЕ ВРАГИ ?', cost=300)
    #         # sender.send_reward(reward_id='05e51e18-62e3-4cd6-bd16-68df1b56a70f', title='Жопа_горит', prompt='я горю, жопа горит', cost=500)
    #         # sender.send_reward(reward_id='846f3e3c-755a-49d3-947d-bd7fd28c008b', title='Гомельский_пёсель', cost=666)
    #     elif sender.channel_id == "712034229":
    #         # sender.send_reward(reward_id='5db8136e-dc36-4e08-95e4-32a39e4a6f4d', title='бесплатно', prompt='юзать когда бесплатно', cost=1)
    #         sender.send_reward(reward_id='e3e8c1cb-0166-4435-a0aa-ea5fff40a63c', title='спинер)', cost=300)


if __name__ == "__main__":
    main()