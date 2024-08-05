from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError, LineBotApiError
import openai
import os

# OpenAI APIキーを設定
openai.api_key = os.getenv('OPENAI_API_KEY', 'sk-proj-0rWegtKf1k8b1H5jiy9qT3BlbkFJFH3IhU8ZAQVEftyw71Sc')

app = Flask(__name__)

# LINE APIのアクセストークンを設定
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET'))

# 質問回数を追跡するための変数
user_question_count = {}

def get_openai_response(user_message):
    system_instruction = "以下の質問に対して、回答を日本語で250文字以内にまとめてください。"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ]
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
    except LineBotApiError as e:
        app.logger.error(f"LineBotApiError: {e.status_code} {e.error.message}")
        abort(500)
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
    else:
        if user_id not in user_question_count:
            user_question_count[user_id] = 0

        if user_question_count[user_id] < 3:
            reply_message = get_openai_response(user_message)
            user_question_count[user_id] += 1
        else:
            reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"

    app.logger.info(f"返信内容: {reply_message}")  # 返信メッセージをログに記録

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
    except LineBotApiError as e:
        app.logger.error(f"LineBotApiError: {e.status_code} {e.error.message}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
