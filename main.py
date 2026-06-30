import json
import os

from twitch_reward_sender import TwitchRewardSender

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
        
        return config
    except Exception as e:
        print(f"Ошибка при чтении config.json: {e}")
        exit(1)

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
            choice = int(input("Введите номер награды: "))
            if 1 <= choice <= len(sender.rewards):
                return sender.rewards[choice - 1]
            print("❌ Неверный номер награды")
        except ValueError:
            print("❌ Введите число")


def ask_send_count():
    """Спрашивает, сколько раз отправить награду."""
    while True:
        try:
            count = int(input("Сколько раз отправить награду: "))
            if count > 0:
                return count
            print("❌ Число должно быть больше нуля")
        except ValueError:
            print("❌ Введите число")


if __name__ == "__main__":
    config = load_config()
    
    OAUTH_TOKEN = config['OAUTH_TOKEN']
    
    streamer_name = input("Ввидите имя стримера: ")

    # Инициализация
    sender = TwitchRewardSender(OAUTH_TOKEN, streamer_name)
    if os.path.exists(os.path.join(sender.rewards_dir, f"{sender.streamer_name}.json")):
        sender.load_rewards_from_file()
    else:
        sender.fetch_channel_rewards()
        sender.save_rewards_to_file()

    try:
        while True:
            action_menu()
            action = input("Выберите действие: ")

            if action == '1':
                sender.fetch_channel_rewards()
                sender.save_rewards_to_file()
            elif action == '2':
                sender.list_available_rewards()
            elif action == '3':
                reward = choose_reward(sender)
                if reward is None:
                    continue

                count = ask_send_count()
                sender.send_reward(reward, count)
            elif action == 'x':
                print("Exit....")
                exit(0)
            else:
                action_menu()
    except KeyboardInterrupt:
        print("Exit....")
        exit(1)