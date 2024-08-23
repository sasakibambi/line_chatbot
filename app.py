
import os
import traceback
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhook import MessageEvent
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
import openai

app = Flask(__name__)

# ログの設定
import logging
logging.basicConfig(level=logging.INFO)

# LINE API設定
configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# OpenAI APIキーを設定
openai.api_key = os.getenv('OPENAI_API_KEY')

# 質問回数を追跡するための変数
user_question_count = {}

def get_openai_response(user_message):
    system_instruction = "以下の質問に対して、日本語を使用するとても聡明で優しい女性の様に回答し250文字以内にまとめてください。"
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_message}
    ]
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply_message = response.choices[0].message['content'].strip()
        app.logger.info(f"OpenAIの応答: {reply_message}")
        
        # 返信メッセージの長さを制限
        if len(reply_message) > 250:
            reply_message = reply_message[:250] + '...'
        
        return reply_message
    except Exception as e:
        app.logger.error(f"OpenAI APIエラー: {e}, Traceback: {traceback.format_exc()}")
        return "申し訳ありませんが、現在対応できません。後ほどお試しください。"

@app.route("/callback", methods=['POST'])
def callback():
    try:
        # X-Line-Signatureヘッダー値を取得
        signature = request.headers['X-Line-Signature']
    
        # リクエストボディをテキストとして取得
        body = request.get_data(as_text=True)
        app.logger.info("リクエストボディ: " + body)
        
        # Webhookボディを処理
        handler.handle(body, signature)
        app.logger.info("Webhook処理成功")
    
    except InvalidSignatureError as e:
        app.logger.error(f"Invalid signature. Please check your channel access token/channel secret. Error: {e}, Traceback: {traceback.format_exc()}")
        abort(400)
    except Exception as e:
        app.logger.error(f"Webhook handlingエラー: {e}, Traceback: {traceback.format_exc()}")
        abort(500)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        
        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")
        
        # 質問回数を確認してから返信
        if user_id not in user_question_count:
            user_question_count[user_id] = 0
        
        if user_question_count[user_id] <= 3:
            reply_message = get_openai_response(user_message)
            app.logger.info(f"OpenAIからの応答を取得しました: {reply_message}")
            user_question_count[user_id] += 1
            
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                try:
                    app.logger.info("LINEにメッセージを送信します")
                    line_bot_api.reply_message_with_http_info(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_message)]
                        )
                    )
                    app.logger.info("メッセージ送信成功")
                except Exception as e:
                    app.logger.error(f"LINE Messaging APIエラー: {e}, Traceback: {traceback.format_exc()}")
                    raise
        else:
            reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                try:
                    app.logger.info("3問目以降のメッセージを送信します")
                    line_bot_api.reply_message_with_http_info(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_message)]
                        )
                    )
                    app.logger.info("メッセージ送信成功")
                except Exception as e:
                    app.logger.error(f"LINE Messaging APIエラー: {e}, Traceback: {traceback.format_exc()}")
                    raise
    except Exception as e:
        app.logger.error(f"メッセージ処理中のエラー: {e}, Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 5000))
        app.logger.info(f"サーバーを起動しています。ポート: {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        app.logger.error(f"サーバー起動エラー: {e}, Traceback: {traceback.format_exc()}")
