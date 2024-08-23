
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import logging

app = Flask(__name__)

# LINE Messaging APIの設定
line_bot_api = LineBotApi('CHANNEL_ACCESS_TOKEN')  # 正しいアクセストークンを設定
handler = WebhookHandler('CHANNEL_SECRET')         # 正しいチャネルシークレットを設定

# OpenAI APIキーの設定
openai.api_key = 'OPENAI_API_KEY'  # 正しいOpenAI APIキーを設定

# ユーザーの質問回数をカウントする辞書
user_question_count = {}

def get_openai_response(user_message):
    # OpenAI APIからの応答を取得するためのコード
    try:
        response = openai.Completion.create(
            engine="davinci",
            prompt=user_message,
            max_tokens=150
        )
        return response.choices[0].text.strip()
    except Exception as e:
        app.logger.error(f"OpenAI APIエラー: {e}")
        return "申し訳ありませんが、応答を取得できませんでした。"

@app.route("/callback", methods=['POST'])
def callback():
    if 'x-line-signature' not in request.headers:
        app.logger.error("リクエストにx-line-signatureヘッダーが含まれていません。")
        abort(400)

    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)

    app.logger.info(f"Received body: {body}")
    app.logger.info(f"Received signature: {signature}")

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
    # 開発サーバーを 0.0.0.0 で起動する
    app.run(host='0.0.0.0', port=5000)
