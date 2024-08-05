from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os

# Set the OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY', 'sk-proj-0rWegtKf1k8b1H5jiy9qT3BlbkFJFH3IhU8ZAQVEftyw71Sc')

app = Flask(__name__)

# Set the LINE API access token and secret
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN', 'NmCgpqV6XfBzGenkoKXeZH5SVB/+WDArTAehA6jC6S7pYGdA4UOpjgt14nQ6t+X8/3+skVNUXR9h9Mp2ouYZGMmhgAJQ/6fvYU3kCUhfnp8ar2gptSyUcP5aagVBo2he6nSk+J2UTU90JNI4NPc03wdB04t89/1O/w1cDnyilFU='))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET', 'eb994f30fef1a6cc80a0a3f82508c758'))

# 質問回数を追跡するための変数
user_question_count = {}

@app.route("/", methods=['POST'])
def home():
    try:
        # get X-Line-Signature header value
        signature = request.headers['X-Line-Signature']

        # get request body as text
        body = request.get_data(as_text=True)
        app.logger.info("Request body: " + body)  # Log the request body

        # handle webhook body
        handler.handle(body, signature)

    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        app.logger.error(f"Error: {e}")
        abort(500)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    app.logger.info(f"Received message from {user_id}: {user_message}")  # Log the received message

    # Check the length of the message
    if len(user_message) > 250:
        reply_message = "ご質問は250文字以内でお願いします！"
    else:
        if user_id not in user_question_count:
            user_question_count[user_id] = 0

        if user_question_count[user_id] < 3:
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

                # Limit the length of the reply message
                if len(reply_message) > 250:
                    reply_message = reply_message[:250] + '...'

                user_question_count[user_id] += 1
            except Exception as e:
                app.logger.error(f"OpenAI API error: {e}")
                reply_message = f"回答を生成する際にエラーが発生しました。詳細: {e}"

        else:
            reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"

    app.logger.info(f"Replying with: {reply_message}")  # Log the reply message

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
