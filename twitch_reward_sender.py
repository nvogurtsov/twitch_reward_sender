import json
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "https://gql.twitch.tv/gql"
HASH_CHANNEL_POINTS_CONTEXT = "7fe050e3761eb2cf258d70ee1a21cbd76fa8cf3d7e7b12fc437e7029d446b5e3"
HASH_REDEEM_CUSTOM_REWARD = "d56249a7adb4978898ea3412e196688d4ac3cea1c0c2dfd65561d229ea5dcc42"


class TwitchRewardSender:
    def __init__(self, oauth_token, streamer_name):
        self.base_url = BASE_URL
        self.oauth_token = oauth_token.strip()
        self.streamer_name = streamer_name.strip()
        self.channel_id = None
        self.rewards_dir = Path.cwd() / "rewards"
        self.rewards = []
        self.point_balance = None

        self.headers = {
            "authorization": self.oauth_token
        }

    """Генерирует уникальный ID транзакции."""
    def generate_transaction_id(self):
        return str(uuid.uuid4()).replace("-", "")

    """Нормализует структуру награды и приводит стоимость к числу."""
    def _normalize_reward(self, reward):

        cost = reward.get("cost", 0)
 
        return {
            "id": reward.get("id"),
            "title": reward.get("title"),
            "prompt": reward.get("prompt"),
            "cost": cost,
        }

    """Создает директорию rewards, если она не существует."""
    def _create_rewards_directory(self):
        try:
            self.rewards_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"❌ Ошибка создания директории {self.rewards_dir}: {e}")
            return False

    """Получает все доступные награды канала через ChannelPointsContext."""
    def fetch_channel_rewards(self):

        payload = [{
            "operationName": "ChannelPointsContext",
            "variables": {
                "channelLogin": self.streamer_name,
                "includeGoalTypes": ["CREATOR", "BOOST"]
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": HASH_CHANNEL_POINTS_CONTEXT
                }
            }
        }]

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10,
            )

            if response.status_code != 200:
                print(f"❌ Ошибка получения наград: {response.status_code}")
                return False

            try:
                data = response.json()
            except ValueError as e:
                print(f"❌ Ошибка разбора ответа сервера: {e}")
                return False

            community = data[0].get("data", {}).get("community")

            channel_id = community.get("id")

            self.channel_id = channel_id

            channel = community.get("channel", {})
            community_points_settings = channel.get("communityPointsSettings", {})

            self.point_balance = int(channel["self"]["communityPoints"]["balance"])

            custom_rewards = community_points_settings.get("customRewards", [])

            print(f"✅ Получено {len(custom_rewards)} кастомных наград для канала {self.streamer_name}")

            rewards_list = []
            for reward in custom_rewards:
                if not reward.get("isEnabled", False):
                    continue

                rewards_list.append(self._normalize_reward(reward))

            self.rewards = rewards_list
            self.rewards.sort(key=lambda r: r.get("cost", 0))
            return True

        except Exception as e:
            print(f"❌ Исключение при запросе наград: {e}")
            return False

    """Сохраняет награды в JSON-файл с именем стримера."""
    def save_rewards_to_file(self):

        if not self._create_rewards_directory():
            return False

        filepath = self.rewards_dir / f"{self.streamer_name}.json"
        rewards_data = {
            "streamer": self.streamer_name,
            "id": self.channel_id,
            "rewards": self.rewards,
        }

        try:
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(rewards_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения файла: {e}")
            return False

    """Загружает награды из JSON-файла в директории rewards."""
    def load_rewards_from_file(self):

        filepath = self.rewards_dir / f"{self.streamer_name}.json"
        if not filepath.exists():
            print(f"❌ Файл не найден: {filepath}")
            return False

        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            return False

        if not isinstance(data, dict):
            print("❌ Файл наград имеет некорректный формат")
            return False

        rewards = data.get("rewards", [])

        self.channel_id = data.get("id")
        self.rewards = rewards
        self.rewards.sort(key=lambda r: r.get("cost", 0))
        return True

    """Выводит список доступных наград в удобном формате."""
    def list_available_rewards(self):

        if not self.rewards:
            print("❌ Список наград пустой")
            return

        titles = [reward.get("title") for reward in self.rewards]
        title_width = max(len("Название"), *(len(title) for title in titles))

        print("\n📋 Доступные награды:")
        print(f"{'№':<3} {'Название':<{title_width}} {'Стоимость':>10}")
        print(f"{'-' * 3} {'-' * title_width} {'-' * 10}")
        for index, reward in enumerate(self.rewards, 1):
            title = reward.get("title")
            cost = reward.get("cost", 0)
            print(f"{index:<3} {title:<{title_width}} {cost:>10}")

    def send_reward(self, reward, count):

        for _ in range(count):
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
                        "transactionID": self.generate_transaction_id(),
                    }
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": HASH_REDEEM_CUSTOM_REWARD,
                    }
                },
            }]

            try:
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=10,
                )

                if response.status_code != 200:
                    print(f"❌ Ошибка отправки награды: {response.status_code}")
                    print(f"  {response.text[:200]}")
                    return False

            except Exception as e:
                print(f"❌ Исключение при отправке награды: {e}")
                return False

        return True

    def send_chat_message(self, message, count):

        for _ in range(count):
            payload = [{
                "operationName": "sendChatMessage",
                "variables": {
                    "input": {
                        "channelID": str(self.channel_id),
                        "message": message,
                        "nonce": self.generate_transaction_id(),
                        "replyParentMessageID": None,
                    }
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "0435464292cf380ed4b3d905e4edcb73078362e82c06367a5b2181c76c822fa2",
                    }
                },
            }]

            try:
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=10,
                )

                if response.status_code != 200:
                    print(f"❌ Ошибка отправки сообщения: {response.status_code}")
                    print(f"  {response.text[:200]}")
                    return False

                try:
                    result = response.json()
                except ValueError as e:
                    print(f"❌ Ошибка разбора ответа при отправке сообщения: {e}")
                    return False

                drop_reason = result[0].get("data", {}).get("sendChatMessage", {}).get("dropReason")

                if drop_reason:
                    print(f"❌ Сообщение отброшено: {drop_reason}")
                    return False

            except Exception as e:
                print(f"❌ Исключение при отправке сообщения: {e}")
                return False

            time.sleep(0.2)

        return True