import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai

app = Flask(__name__)

# LINE Messaging APIの設定
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# ユーザーの質問回数をカウントする辞書
user_question_count = {}

def get_openai_response(user_message):
    # 聡明さと優しさを持ち合わせた女性として回答するためのプロンプトを作成
    prompt = (
        f"あなたは聡明さと優しさを持ち合わせた女性です。以下の質問に、"
        f"温かく、かつ知識に基づいて答えてください。\n\n"
        f"質問: {user_message}"
    )
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "あなたは聡明さと優しさを持ち合わせた女性です。"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150
    )
    return response.choices[0].message['content'].strip()

@app.route("/callback", methods=['POST'])
def callback():
    if 'x-line-signature' not in request.headers:
        app.logger.error("リクエストにx-line-signatureヘッダーが含まれていません。")
        abort(400)

    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("無効な署名です。")
        abort(400)
    except Exception as e:
        app.logger.error(f"リクエスト処理中のエラー: {e}")
        abort(500)

    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text

        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")

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

        if user_question_count[user_id] <= 3:
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

    except Exception as e:
        app.logger.error(f"メッセージ処理中のエラー: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
