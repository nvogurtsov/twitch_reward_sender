import json
import os
import sys
from pathlib import Path

from twitch_reward_sender import TwitchRewardSender

# ============== ИСПОЛЬЗОВАНИЕ ==============

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.json"


def load_config():
    """Загружает конфигурацию из config.json."""
    if not CONFIG_PATH.exists():
        print(f"Ошибка: Файл {CONFIG_PATH} не найден!")
        print("Создайте config.json на основе config.example.json")
        sys.exit(1)

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Ошибка при чтении config.json: {e}")
        sys.exit(1)

    if not isinstance(config, dict):
        print("Ошибка: Файл config.json должен содержать JSON-объект")
        sys.exit(1)

    oauth_token = config.get("OAUTH_TOKEN")
    if not isinstance(oauth_token, str) or not oauth_token.strip() or oauth_token == "twitch-oauth-token-here":
        print("Ошибка: Укажите реальный OAUTH_TOKEN в config.json!")
        sys.exit(1)

    return config

def action_menu():
    actions = {
        1: "Загрузить/обновить награды",
        2: "Вывести список наград",
        3: "Отправить награды",
        "x": "Exit"
    }
    print("Выберите действие")

    for k, v in actions.items():
        print(f"  {k}: {v}")


def choose_reward(sender):
    """Выбирает награду из списка и возвращает её."""
    if not sender.rewards:
        print("❌ Список наград пустой")
        return None

    sender.list_available_rewards()

    while True:
        try:
            choice_text = input("Введите номер награды: ").strip()
            if not choice_text:
                print("❌ Введите номер награды")
                continue
            choice = int(choice_text)
            if 1 <= choice <= len(sender.rewards):
                return sender.rewards[choice - 1]
            print("❌ Неверный номер награды")
        except ValueError:
            print("❌ Введите число")


def ask_send_count():
    """Спрашивает, сколько раз отправить награду."""
    while True:
        try:
            count_text = input("Сколько раз отправить награду: ").strip()
            if not count_text:
                print("❌ Введите число")
                continue
            count = int(count_text)
            if count > 0:
                return count
            print("❌ Число должно быть больше нуля")
        except ValueError:
            print("❌ Введите число")


def boot_sender() -> int:
    config = load_config()
    oauth_token = config["OAUTH_TOKEN"]

    streamer_name = input("Ввидите имя стримера: ").strip()
    if not streamer_name:
        print("❌ Имя стримера не может быть пустым")
        return 1

    sender = TwitchRewardSender(oauth_token, streamer_name)
    reward_file = sender.rewards_dir / f"{sender.streamer_name}.json"

    if reward_file.exists():
        sender.load_rewards_from_file()
    else:
        if sender.fetch_channel_rewards() and sender.rewards:
            sender.save_rewards_to_file()

    try:
        while True:
            action_menu()
            action = input("Выберите действие: ").strip()

            if action == "1":
                if sender.fetch_channel_rewards():
                    sender.save_rewards_to_file()
            elif action == "2":
                sender.list_available_rewards()
            elif action == "3":
                reward = choose_reward(sender)
                if reward is None:
                    continue

                count = ask_send_count()
                success, response = sender.send_reward(reward, count)
                if success:
                    print("✅ Награды отправлены")
                elif response is not None:
                    print("❌ Не удалось отправить награды. Подробнее в ответе Twitch.")
            elif action == "x":
                print("Exit....")
                return 0
            else:
                print("❌ Неверная команда")
    except KeyboardInterrupt:
        print("Exit....")
        return 1


if __name__ == "__main__":
    sys.exit(boot_sender())