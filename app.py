import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import time

app = Flask(__name__)

# LINE API設定
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
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

        # 返信メッセージの長さを制限
        if len(reply_message) > 250:
            reply_message = reply_message[:250] + '...'

        return reply_message
    except Exception as e:
        app.logger.error(f"OpenAI APIエラー: {e}")
        return f"回答を生成する際にエラーが発生しました。詳細: {e}"

@app.route("/", methods=['POST'])
def home():
    try:
        # X-Line-Signatureヘッダー値を取得
        signature = request.headers['X-Line-Signature']

        # リクエストボディをテキストとして取得
        body = request.get_data(as_text=True)
        app.logger.info("リクエストボディ: " + body)  # リクエストボディをログに記録

        # Webhookボディを処理
        handler.handle(body, signature)

    except InvalidSignatureError:
        app.logger.error("無効な署名です。チャンネルアクセストークンまたはチャンネルシークレットを確認してください。")
        abort(400)
    except Exception as e:
        app.logger.error(f"エラー: {e}")
        abort(500)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")  # 受信したメッセージをログに記録

    # メッセージの長さを確認
    if len(user_message) > 250:
        reply_message = "ご質問は250文字以内でお願いします！"
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_message)
            )
        except LineBotApiError as e:
            app.logger.error(f"LINE Messaging APIエラー: {e}")
        return

    # 質問回数を確認してから返信
    if user_id not in user_question_count:
        user_question_count[user_id] = 0

    if user_question_count[user_id] < 4:
        # まずはリプライトークンが有効なうちに「少々お待ちください」というメッセージを送信
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="少々お待ちください...")
            )
        except LineBotApiError as e:
            app.logger.error(f"LINE Messaging APIエラー: {e}")
            return
        
        # OpenAIからの応答を取得
        reply_message = get_openai_response(user_message)
        user_question_count[user_id] += 1

        # メッセージを再送信するためにプッシュメッセージを使用
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text=reply_message)
            )
        except LineBotApiError as e:
            app.logger.error(f"LINE Messaging APIエラー: {e}")
    else:
        reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_message)
            )
        except LineBotApiError as e:
            app.logger.error(f"LINE Messaging APIエラー: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
