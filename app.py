from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging.models import TextMessage

app = Flask(__name__)

# LINE Messaging APIの設定
configuration = Configuration(access_token='YOUR_CHANNEL_ACCESS_TOKEN')
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler('YOUR_CHANNEL_SECRET')

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
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        app.logger.error(f"リクエスト処理中のエラー: {e}, Traceback: {traceback.format_exc()}")
        abort(500)
    
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text

        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")
        
        if user_id not in user_question_count:
            user_question_count[user_id] = 0
        
        if user_question_count[user_id] == 0:
            try:
                app.logger.info("LINEに待機メッセージを送信します")
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="少々お待ちください…！")]
                    )
                )
                app.logger.info("待機メッセージ送信成功")
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: {e}, Traceback: {traceback.format_exc()}")
                raise
            
            # 次に実際のプッシュメッセージを送信
            reply_message = get_openai_response(user_message)
            try:
                app.logger.info("LINEにプッシュメッセージを送信します")
                messaging_api.push_message(
                    user_id,
                    [TextMessage(text=reply_message)]
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
                    messaging_api.reply_message(
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
                try:
                    app.logger.info("3問目以降のメッセージを送信します")
                    messaging_api.reply_message(
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

def get_openai_response(user_message):
    # OpenAIからの応答を取得するための関数
    # 実際の実装を追加してください
    return "OpenAIからの応答"

if __name__ == "__main__":
    app.run(debug=True)
