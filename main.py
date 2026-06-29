import requests
import json
import uuid
from datetime import datetime

class TwitchRewardSender:
    def __init__(self, oauth_token, channel_id):

        self.base_url = "https://gql.twitch.tv/gql"
        self.oauth_token = oauth_token
        self.channel_id = channel_id
        
        # Заголовки из вашего запроса
        self.headers = {
            'authorization': oauth_token
        }
        
    def generate_transaction_id(self):
        """Генерирует уникальный ID транзакции"""
        return str(uuid.uuid4()).replace('-', '')
    
    def send_reward(self, reward_id, title, cost=200, prompt=None):

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
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Отправка: {title}")
            print(f"  Transaction ID: {transaction_id}")
            print(f"  Статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return True, result
            else:
                print(f"  Ошибка: {response.text[:200]}")
                return False, None
                
        except Exception as e:
            print(f"  Исключение: {str(e)}")
            return False, None

# ============== ИСПОЛЬЗОВАНИЕ ==============

def main():
    OAUTH_TOKEN = ""
    #CHANNEL_ID = "510819602"  # lero
    #CHANNEL_ID = "109840796"  # demon
    CHANNEL_ID = "712034229"  # kashiri
    REWARD_COUNT = 10
    
    # Инициализация
    sender = TwitchRewardSender(OAUTH_TOKEN, CHANNEL_ID)

    for _ in range(0, REWARD_COUNT):
        if CHANNEL_ID == "510819602":
            sender.send_reward(reward_id='346cf41e-c202-4300-a2f6-4e0527a82063', title='хи-хи', cost=200)
            #sender.send_reward(reward_id='148c57a6-1c36-4834-80e4-5f3d92bb260b', title='LEROLEROLERO', cost=500)
        elif CHANNEL_ID == "109840796":
            sender.send_reward(reward_id='e00e1d4e-62cd-4502-9896-7756d41e938e', title='!Боже_мой', prompt='Да боже мой, да всем насрать', cost=300)
            #sender.send_reward(reward_id='8ac974de-1e97-44b1-803b-b325faa79c0c', title='!Где_враги', prompt='НУУУУ ГДЕ ВРАГИ ?', cost=300)
            #sender.send_reward(reward_id='05e51e18-62e3-4cd6-bd16-68df1b56a70f', title='Жопа_горит', prompt='я горю, жопа горит', cost=500)
            #sender.send_reward(reward_id='846f3e3c-755a-49d3-947d-bd7fd28c008b', title='Гомельский_пёсель', cost=666)
        elif CHANNEL_ID == "712034229":
            #sender.send_reward(reward_id='5db8136e-dc36-4e08-95e4-32a39e4a6f4d', title='бесплатно', prompt='юзать когда бесплатно', cost=1)
            sender.send_reward(reward_id='e3e8c1cb-0166-4435-a0aa-ea5fff40a63c', title='спинер)', cost=300)

        #time.sleep(0.1)

if __name__ == "__main__":
    main()