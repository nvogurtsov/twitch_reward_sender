import json
import os
import sys
from pathlib import Path

from twitch_reward_sender import TwitchRewardSender

# ============== ИСПОЛЬЗОВАНИЕ ==============

if getattr(sys, "frozen", False):
    CONFIG_DIR = Path(sys.executable).resolve().parent
else:
    CONFIG_DIR = Path(__file__).resolve().parent

CONFIG_PATH = CONFIG_DIR / "config.json"


def prompt_for_token() -> str:
    while True:
        token = input("Введите токен авторизации Twitch: ").strip()
        if token:
            return token
        print("❌ Токен не может быть пустым")


def save_config(config):
    try:
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Ошибка сохранения config.json: {e}")


"""Загружает конфигурацию из config.json."""
def load_config():
    config = {}
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"❌ Ошибка при чтении config.json: {e}")
            print("Будет предложено ввести OAUTH_TOKEN заново.")

    oauth_token = config.get("OAUTH_TOKEN")

    if not isinstance(oauth_token, str) or not oauth_token.strip():
        oauth_token = prompt_for_token()
        config["OAUTH_TOKEN"] = oauth_token
        if not save_config(config):
            sys.exit(1)

    return config


"""Выводит меню действий"""
def action_menu(point_balance):
    actions = {
        1: "Загрузить/обновить награды",
        2: "Вывести список наград",
        3: "Отправить награды",
        4: "Отправить сообщение в чат",
        "x": "Exit"
    }
    print(f"Кол-во баллов: {point_balance}")
    print("Выберите действие")

    for k, v in actions.items():
        print(f"  {k}: {v}")


"""Выбирает награду из списка и возвращает её."""
def choose_reward(sender):
    if not sender.rewards:
        sender.fetch_channel_rewards()

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


"""Спрашивает, сколько раз отправить наград или сообщение, и возвращает число."""
def ask_send_count():
    while True:
        try:
            count_text = input("Сколько раз отправить: ").strip()
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

    # reward_file = sender.rewards_dir / f"{sender.streamer_name}.json"
    # if reward_file.exists():
    #     sender.load_rewards_from_file()

    if sender.fetch_channel_rewards() and sender.rewards:
        sender.save_rewards_to_file()

    try:
        while True:
            action_menu(sender.point_balance)
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
                success = sender.send_reward(reward, count)
                if success:
                    print("✅ Награды отправлены")
            elif action == "4":
                message = input("Введите текст сообщения: ").strip()
                if not message:
                    print("❌ Сообщение не может быть пустым")
                    continue

                count = ask_send_count()
                success = sender.send_chat_message(message, count)
                if success:
                    print("✅ Сообщения отправлены")
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
