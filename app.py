from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage
import logging
import traceback

app = Flask(__name__)

# LINE Messaging APIの設定
LINE_CHANNEL_ACCESS_TOKEN = 'YOUR_CHANNEL_ACCESS_TOKEN'
LINE_CHANNEL_SECRET = 'YOUR_CHANNEL_SECRET'
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ユーザーの質問回数をカウントする辞書
user_question_count = {}

@app.route("/callback", methods=['POST'])
def callback():
    if 'x-line-signature' not in request.headers:
        abort(400)
    
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except Exception as e:
        app.logger.error(f"リクエスト処理中のエラー: {e}, Traceback: {traceback.format_exc()}")
        abort(500)
    
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    try:

@@ -6,78 +39,73 @@ def handle_message(event):
        
        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")
app.py
@@ -1,3 +1,36 @@
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage
import logging
import traceback

app = Flask(__name__)

# LINE Messaging APIの設定
LINE_CHANNEL_ACCESS_TOKEN = 'YOUR_CHANNEL_ACCESS_TOKEN'
LINE_CHANNEL_SECRET = 'YOUR_CHANNEL_SECRET'
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ユーザーの質問回数をカウントする辞書
user_question_count = {}

@app.route("/callback", methods=['POST'])
def callback():
    if 'x-line-signature' not in request.headers:
        abort(400)
    
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except Exception as e:
        app.logger.error(f"リクエスト処理中のエラー: {e}, Traceback: {traceback.format_exc()}")
        abort(500)
    
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    try:

@@ -6,78 +39,73 @@ def handle_message(event):
        
        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")
  try:
                app.logger.info("LINEに待機メッセージを送信します")
                line_bot_api.reply_message(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="少々お待ちください…！")]
                )
                app.logger.info("待機メッセージ送信成功")
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: {e}, Traceback: {traceback.format_exc()}")
                raise
            
            # 次に実際のプッシュメッセージを送信
            reply_message = get_openai_response(user_message)
              try:
                app.logger.info("LINEにプッシュメッセージを送信します")
                line_bot_api.push_message(
                    to=user_id,
                    messages=[TextMessage(text=reply_message)]
                )
                app.logger.info("プッシュメッセージ送信成功")
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: {e}, Traceback: {traceback.format_exc()}")
                raise
        else:
            if user_question_count[user_id] <= 3:
                reply_message = get_openai_response(user_message)
                app.logger.info(f"OpenAIからの応答を取得しました: {reply_message}")
                user_question_count[user_id] += 1
                 try:
                    app.logger.info("LINEにメッセージを送信します")
                    line_bot_api.reply_message(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_message)]
                    )
                    app.logger.info("メッセージ送信成功")
                except Exception as e:
                    app.logger.error(f"LINE Messaging APIエラー: {e}, Traceback: {traceback.format_exc()}")
                    raise
            else:
                reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"
                  try:
                    app.logger.info("3問目以降のメッセージを送信します")
                    line_bot_api.reply_message(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_message)]
                    )
                    app.logger.info("メッセージ送信成功")
                except Exception as e:
                    app.logger.error(f"LINE Messaging APIエラー: {e}, Traceback: {traceback.format_exc()}")
                    raise
    except Exception as e:
        app.logger.error(f"メッセージ処理中のエラー: {e}, Traceback: {traceback.format_exc()}")

def get_openai_response(user_message):
    # OpenAIからの応答を取得するための関数
    # 実際の実装を追加してください
    return "OpenAIからの応答"

if __name__ == "__main__":
    app.run(debug=True)