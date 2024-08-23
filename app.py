import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import time

app = Flask(__name__)

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