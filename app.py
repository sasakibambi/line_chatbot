import os
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.models import MessageEvent, TextSendMessage, TextMessage
import openai

app = Flask(__name__)

# 環境変数からAPIキーを取得
openai_api_key = os.getenv('OPENAI_API_KEY')
line_channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')

# 環境変数が取得できているかチェック
if not openai_api_key:
    raise ValueError("OPENAI_API_KEYが設定されていません。")
if not line_channel_access_token:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKENが設定されていません。")
if not line_channel_secret:
    raise ValueError("LINE_CHANNEL_SECRETが設定されていません。")

openai.api_key = openai_api_key
line_bot_api = MessagingApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

user_question_count = {}

@app.route("/", methods=['POST'])
def home():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    if len(user_message) > 250:
        reply_message = "ご質問は250文字以内でお願いします！"
    else:
        if user_id not in user_question_count:
            user_question_count[user_id] = 0

        if user_question_count[user_id] < 3:
            system_instruction = "以下の質問に対して、回答を日本語で250文字以内にまとめてください。"

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_message}
                ],
            )
            reply_message = response.choices[0].message['content']

            if len(reply_message) > 250:
                reply_message = reply_message[:250] + '...'

            user_question_count[user_id] += 1
        else:
            reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
