import requests
import json
import uuid
import os

class TwitchRewardSender:
    def __init__(self, oauth_token, streamer_name):
        self.base_url = "https://gql.twitch.tv/gql"
        self.oauth_token = oauth_token.strip() if isinstance(oauth_token, str) else ""
        self.streamer_name = streamer_name.strip() if isinstance(streamer_name, str) else ""
        self.channel_id = None
        self.rewards_dir = os.path.abspath(os.path.join(os.getcwd(), 'rewards'))
        self.rewards = []
        
        self.headers = {
            'authorization': self.oauth_token
        } if self.oauth_token else {}
        
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

        if not self.oauth_token:
            print("❌ OAUTH_TOKEN не указан — пропускаем получение наград")
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
                
            try:
                data = response.json()
            except ValueError as e:
                print(f"❌ Ошибка разбора ответа сервера: {e}")
                return None
            
            # Извлекаем community id и rewards
            try:
                if not isinstance(data, list) or not data:
                    print("❌ Сервер вернул пустой или невалидный ответ")
                    return None

                community = data[0].get('data', {}).get('community')
                if not isinstance(community, dict):
                    print("❌ В ответе Twitch нет данных о community")
                    return None

                channel_id = community.get('id')
                if not channel_id:
                    print("❌ Не удалось определить ID канала")
                    return None
                self.channel_id = channel_id

                channel = community.get('channel', {})
                if not isinstance(channel, dict):
                    channel = {}
                community_points_settings = channel.get('communityPointsSettings', {})
                if not isinstance(community_points_settings, dict):
                    community_points_settings = {}
                
                # Получаем кастомные награды
                custom_rewards = community_points_settings.get('customRewards', [])
                if not isinstance(custom_rewards, list):
                    custom_rewards = []
                
                print(f"✅ Получено {len(custom_rewards)} кастомных наград для канала {self.streamer_name} (ID: {channel_id})")
                
                # Формируем структуру для сохранения
                rewards_list = []
                for reward in custom_rewards:
                    if not isinstance(reward, dict):
                        continue
                    if reward.get('isEnabled', False):
                        cost = reward.get('cost', 0)
                        try:
                            cost = int(cost)
                        except (TypeError, ValueError):
                            cost = 0
                        rewards_list.append({
                            "id": reward.get('id'),
                            "title": reward.get('title') or 'Без названия',
                            "prompt": reward.get('prompt') or '',
                            "cost": cost
                        })

                self.rewards = rewards_list
                self._sort_rewards_by_cost()

            except (KeyError, IndexError, TypeError) as e:
                print(f"❌ Ошибка парсинга ответа: {e}")
                print(f"Ответ: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ Исключение при запросе наград: {e}")
            return None
    
    def _sort_rewards_by_cost(self):
        """Сортирует список наград по стоимости в порядке возрастания."""
        valid_rewards = []
        for reward in self.rewards:
            if not isinstance(reward, dict):
                continue
            cost = reward.get('cost', 0)
            try:
                cost = int(cost)
            except (TypeError, ValueError):
                cost = 0
            valid_rewards.append({
                "id": reward.get('id'),
                "title": reward.get('title') or 'Без названия',
                "prompt": reward.get('prompt') or '',
                "cost": cost
            })
        self.rewards = sorted(valid_rewards, key=lambda reward: reward.get('cost', 0))

    def save_rewards_to_file(self):
        """Сохраняет награды в JSON-файл с именем стримера"""
        if not self.streamer_name:
            print("❌ Невозможно сохранить награды: не указано имя стримера")
            return False

        if not self._create_rewards_directory():
            return False

        filename = f"{self.streamer_name}.json"
        filepath = os.path.join(self.rewards_dir, filename)

        rewards_data = {
            "streamer": self.streamer_name,
            "id": self.channel_id,
            "rewards": self.rewards if isinstance(self.rewards, list) else []
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
        if not self.streamer_name:
            print("❌ Невозможно загрузить награды: не указано имя стримера")
            return None
        
        filepath = os.path.join(self.rewards_dir, f"{self.streamer_name}.json")
        
        if not os.path.exists(filepath):
            print(f"❌ Файл не найден: {filepath}")
            return None
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            return None

        if not isinstance(data, dict):
            print("❌ Файл наград имеет некорректный формат")
            return None

        rewards = data.get('rewards', [])
        if not isinstance(rewards, list):
            print("❌ В файле наград отсутствует список rewards")
            return None

        self.channel_id = data.get('id')
        self.rewards = rewards
        self._sort_rewards_by_cost()
        return True

    def list_available_rewards(self):
        """Выводит список доступных наград в удобном формате."""
        if not isinstance(self.rewards, list):
            self.rewards = []

        if len(self.rewards) == 0:
            print("❌ Список наград пустой")
            return

        titles = []
        for reward in self.rewards:
            if isinstance(reward, dict):
                titles.append(reward.get('title') or 'Без названия')
            else:
                titles.append('Без названия')
        title_width = max(len('Название'), *(len(title) for title in titles))

        print("\n📋 Доступные награды:")
        print(f"{'№':<3} {'Название':<{title_width}} {'Стоимость':>10}")
        print(f"{'-' * 3} {'-' * title_width} {'-' * 10}")
        for i, reward in enumerate(self.rewards, 1):
            if not isinstance(reward, dict):
                continue
            title = reward.get('title') or 'Без названия'
            cost = reward.get('cost', 0)
            try:
                cost = int(cost)
            except (TypeError, ValueError):
                cost = 0
            print(f"{i:<3} {title:<{title_width}} {cost:>10}")
        
    def send_reward(self, reward, count):
        if not isinstance(reward, dict):
            print("❌ Невалидная награда")
            return False, None

        required_fields = ['id', 'title', 'prompt', 'cost']
        missing_fields = [field for field in required_fields if field not in reward]
        if missing_fields:
            print(f"❌ Награда не содержит обязательных полей: {', '.join(missing_fields)}")
            return False, None

        if not self.channel_id:
            print("❌ Не удалось определить channel_id для отправки награды")
            return False, None

        if not isinstance(count, int) or count <= 0:
            print("❌ Количество отправок должно быть положительным числом")
            return False, None

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
                        "rewardID": reward["id"],
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
                    try:
                        result = response.json()
                    except ValueError as e:
                        print(f"❌ Ошибка разбора ответа при отправке награды: {e}")
                        return False, None
                    continue
                else:
                    print(f"  Ошибка: {response.text[:200]}")
                    return False, None
                    
            except Exception as e:
                print(f"  Исключение: {str(e)}")
                return False, None

        return True, None