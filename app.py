@handler.add(MessageEvent)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        
        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")
        
        # 質問回数を確認してから返信
        if user_id not in user_question_count:
            user_question_count[user_id] = 0
        
        # メッセージが再送信されたかどうか確認
        if event.delivery_context.is_redelivery:
            app.logger.info("メッセージが再送信されました。プッシュメッセージを使用します。")
            reply_message = get_openai_response(user_message)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
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
