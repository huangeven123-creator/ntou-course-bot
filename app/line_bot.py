import hmac
import hashlib
import base64
import requests
import re
from urllib.parse import parse_qs
from app import config, database, crawler

def verify_signature(body: bytes, signature: str) -> bool:
    """
    Verify the signature sent by LINE.
    """
    if not config.LINE_CHANNEL_SECRET:
        return True # Skip verification if not configured
    
    hash_val = hmac.new(
        config.LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash_val).decode('utf-8')
    return hmac.compare_digest(expected_signature, signature)

def send_reply_message(reply_token: str, messages: list):
    """
    Send a reply message back to the user.
    """
    if not config.LINE_CHANNEL_ACCESS_TOKEN:
        print("LINE_CHANNEL_ACCESS_TOKEN not configured. Message skipped:")
        print(messages)
        return
        
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": messages
    }
    
    resp = requests.post(url, json=payload, headers=headers)
    print(f"Reply Response Status: {resp.status_code}, Body: {resp.text}")

def push_notification(user_id: str, text: str):
    """
    Send a push message to a specific user (used for cron job alerts).
    """
    if not config.LINE_CHANNEL_ACCESS_TOKEN:
        print(f"LINE_CHANNEL_ACCESS_TOKEN not configured. Push to {user_id} skipped: {text}")
        return
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    
    resp = requests.post(url, json=payload, headers=headers)
    print(f"Push Response Status: {resp.status_code}, Body: {resp.text}")

def push_messages(user_id: str, messages: list):
    """
    Send push messages (any type) to a specific user.
    """
    if not config.LINE_CHANNEL_ACCESS_TOKEN:
        print(f"LINE_CHANNEL_ACCESS_TOKEN not configured. Push to {user_id} skipped.")
        return
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": user_id,
        "messages": messages
    }
    
    resp = requests.post(url, json=payload, headers=headers)
    print(f"Push Messages Response Status: {resp.status_code}, Body: {resp.text}")

def format_ntou_time(time_str: str) -> str:
    """
    Format NTOU time string like '306,307,308' to '星期三 第 6,7,8 節'.
    """
    if not time_str:
        return "無"
    parts = [p.strip() for p in time_str.split(",") if p.strip()]
    if not parts:
        return time_str
    
    day_map = {
        "1": "一",
        "2": "二",
        "3": "三",
        "4": "四",
        "5": "五",
        "6": "六",
        "7": "日"
    }
    
    days = {}
    for p in parts:
        if len(p) >= 2:
            day = p[0]
            period = p[1:]
            if day not in days:
                days[day] = []
            days[day].append(period)
            
    res = []
    for day, periods in days.items():
        day_name = day_map.get(day, day)
        periods_clean = [p.lstrip("0") for p in periods]
        res.append(f"星期{day_name} 第 {','.join(periods_clean)} 節")
        
    return " | ".join(res)

def format_ntou_classroom(classroom_str: str) -> str:
    if not classroom_str:
        return "無"
    parts = [p.strip() for p in classroom_str.split(",") if p.strip()]
    unique_parts = []
    for p in parts:
        if p not in unique_parts:
            unique_parts.append(p)
    return ",".join(unique_parts)

def create_course_flex_bubble(code, name, teacher, time_str, classroom, quota, max_quota, error=None):
    if error:
        error_msg = str(error) if error is not True else "目前無法取得校務系統名額資料，系統仍會持續為您監控！"
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"課號 {code}",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#111111"
                    },
                    {
                        "type": "text",
                        "text": error_msg,
                        "wrap": True,
                        "margin": "md",
                        "size": "sm",
                        "color": "#555555"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "postback",
                            "label": "取消監控",
                            "data": f"action=unsubscribe&code={code}"
                        }
                    }
                ]
            }
        }
        
    clean_time = format_ntou_time(time_str)
    clean_classroom = format_ntou_classroom(classroom)
    
    is_full = quota >= max_quota
    status_text = "已額滿" if is_full else f"有名額 (剩餘 {max_quota - quota} 個)"
    status_color = "#e11d48" if is_full else "#10b981"
    
    teacher_clean = re.sub(r'\(.*?\)', '', teacher).strip()
    
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": name,
                    "weight": "bold",
                    "size": "lg",
                    "wrap": True,
                    "color": "#1e3a8a"
                },
                {
                    "type": "text",
                    "text": f"課號 {code}",
                    "size": "xs",
                    "color": "#999999",
                    "margin": "xs"
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "教師",
                                    "color": "#888888",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": teacher_clean,
                                    "wrap": True,
                                    "color": "#333333",
                                    "size": "sm",
                                    "flex": 4
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "時間",
                                    "color": "#888888",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": f"{clean_time} ({clean_classroom})",
                                    "wrap": True,
                                    "color": "#333333",
                                    "size": "sm",
                                    "flex": 4
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "狀態",
                                    "color": "#888888",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": f"{quota} / {max_quota} 人 ({status_text})",
                                    "wrap": True,
                                    "weight": "bold",
                                    "color": status_color,
                                    "size": "sm",
                                    "flex": 4
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "取消監控",
                        "data": f"action=unsubscribe&code={code}",
                        "displayText": f"取消監控課號 {code}"
                    }
                }
            ],
            "flex": 0
        }
    }

async def handle_text_message(user_id: str, text: str, reply_token: str):
    """
    Process text messages sent by the user.
    """
    text_stripped = text.strip()
    
    # 1. Handle special list command
    if text_stripped in ["清單", "查詢清單", "查詢", "list", "subscriptions"]:
        subscribed_courses = database.get_user_subscriptions(user_id)
        if not subscribed_courses:
            msg = {
                "type": "text",
                "text": "您目前沒有訂閱任何課程的名額監控喔！🤖\n\n💡 只要輸入 4 到 12 碼的課程代號（例如 B33035PR），就可以開始監控名額！"
            }
            send_reply_message(reply_token, [msg])
        else:
            # Generate Flex Carousel for active subscriptions
            # Flex Carousel supports up to 10 bubbles
            bubbles = []
            for code in subscribed_courses[:10]:
                details = database.get_course_details(code)
                if details:
                    name = details.get("last_name", "未知課程")
                    teacher = details.get("last_teacher", "未知")
                    time_str = details.get("last_time", "無")
                    classroom = details.get("last_classroom", "無")
                    quota = details.get("last_quota", 0)
                    max_quota = details.get("last_max_quota", 0)
                    bubble = create_course_flex_bubble(
                        code, name, teacher, time_str, classroom, quota, max_quota
                    )
                else:
                    bubble = create_course_flex_bubble(
                        code, "加載中...", "未知", "無", "無", 0, 0, error="尚未取得課程資料"
                    )
                bubbles.append(bubble)
                
            flex_msg = {
                "type": "flex",
                "altText": "您的課程監控清單",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            }
            
            # If they have more than 10, send an additional text warning
            messages = [flex_msg]
            if len(subscribed_courses) > 10:
                warning_msg = {
                    "type": "text",
                    "text": f"💡 您目前共監控了 {len(subscribed_courses)} 門課程。上方僅顯示前 10 門，您可以輸入「清單」再次查詢或移除不需要的監控。"
                }
                messages.append(warning_msg)
                
            send_reply_message(reply_token, messages)
        return

    # 2. Extract ALL Course Codes (4 to 12 alphanumeric characters)
    # Exclude command-like words
    tokens = re.findall(r'[A-Za-z0-9]{4,12}', text_stripped)
    course_codes = [t.upper() for t in tokens if t.lower() not in ["list", "query", "help"]]
    
    if not course_codes:
        msg = {
            "type": "text",
            "text": "抱歉，我無法從您的輸入中辨識出有效的課號 🥺\n\n請輸入 4 到 12 碼的英數混合課程代號。\n\n💡 範例：B33035PR\n💡 也可以一次輸入多個課號喔（例如：B33035PR M670124V）"
        }
        send_reply_message(reply_token, [msg])
        return
        
    # Limit to maximum 5 course codes
    course_codes = course_codes[:5]
    
    # 3. Automatically subscribe the user to all of them
    for code in course_codes:
        database.subscribe_course(user_id, code)
        
    # 4. Query all in parallel and return details with a Flex Carousel
    try:
        scrape_results = await crawler.query_courses(course_codes)
        bubbles = []
        for code in course_codes:
            info = scrape_results.get(code, {})
            error = info.get("error")
            
            if error:
                # Fallback to DB
                details = database.get_course_details(code)
                if details and details.get("last_name"):
                    name = details.get("last_name")
                    teacher = details.get("last_teacher", "未知")
                    time_str = details.get("last_time", "無")
                    classroom = details.get("last_classroom", "無")
                    quota = details.get("last_quota", 0)
                    max_quota = details.get("last_max_quota", 0)
                    bubble = create_course_flex_bubble(
                        code, name, teacher, time_str, classroom, quota, max_quota
                    )
                else:
                    bubble = create_course_flex_bubble(
                        code, "未知課程", "未知", "無", "無", 0, 0, error=error
                    )
            else:
                name = info.get("name", "未知課程")
                teacher = info.get("teacher", "未知")
                time_str = info.get("time", "無")
                classroom = info.get("classroom", "無")
                quota = info.get("quota", 0)
                max_quota = info.get("max_quota", 0)
                
                # Update database course state
                database.update_course_state(
                    code, name, quota, max_quota,
                    teacher=teacher, time_str=time_str, classroom=classroom
                )
                
                bubble = create_course_flex_bubble(
                    code, name, teacher, time_str, classroom, quota, max_quota
                )
            bubbles.append(bubble)
            
        flex_msg = {
            "type": "flex",
            "altText": f"已開啟 {len(course_codes)} 門課程的監控",
            "contents": {
                "type": "carousel",
                "contents": bubbles
            }
        }
        send_reply_message(reply_token, [flex_msg])
        
    except Exception as e:
        print(f"Error processing text message subscriptions: {e}")
        # As fallback, show bubbles from database or simple text
        bubbles = []
        for code in course_codes:
            details = database.get_course_details(code)
            if details and details.get("last_name"):
                bubble = create_course_flex_bubble(
                    code, details["last_name"], details.get("last_teacher", "未知"),
                    details.get("last_time", "無"), details.get("last_classroom", "無"),
                    details.get("last_quota", 0), details.get("last_max_quota", 0)
                )
            else:
                bubble = create_course_flex_bubble(
                    code, "加載中...", "未知", "無", "無", 0, 0, error="即時查詢失敗，系統正持續在背景為您監控！"
                )
            bubbles.append(bubble)
            
        flex_msg = {
            "type": "flex",
            "altText": f"已開啟 {len(course_codes)} 門課程的監控",
            "contents": {
                "type": "carousel",
                "contents": bubbles
            }
        }
        send_reply_message(reply_token, [flex_msg])

async def handle_postback(user_id: str, data_str: str, reply_token: str):
    """
    Process postback clicks (Subscribe/Unsubscribe actions).
    """
    params = parse_qs(data_str)
    action = params.get("action", [None])[0]
    course_code = params.get("code", [None])[0]
    
    if not action or not course_code:
        msg = {"type": "text", "text": "無效的操作資料 🥺"}
        send_reply_message(reply_token, [msg])
        return
        
    course_code = course_code.upper()
    
    if action == "subscribe":
        # Save subscription
        database.subscribe_course(user_id, course_code)
        
        # Query current quota immediately to inform the user
        try:
            scrape_results = await crawler.query_courses([course_code])
            if course_code in scrape_results and not scrape_results[course_code].get("error"):
                info = scrape_results[course_code]
                name = info["name"]
                quota = info["quota"]
                max_quota = info["max_quota"]
                teacher = info.get("teacher", "未知")
                time_str = info.get("time", "無")
                classroom = info.get("classroom", "無")
                
                # Update baseline state in DB
                database.update_course_state(
                    course_code, name, quota, max_quota,
                    teacher=teacher, time_str=time_str, classroom=classroom
                )
                
                bubble = create_course_flex_bubble(
                    course_code, name, teacher, time_str, classroom, quota, max_quota
                )
                flex_msg = {
                    "type": "flex",
                    "altText": f"成功監控課程《{name}》",
                    "contents": bubble
                }
                send_reply_message(reply_token, [flex_msg])
            else:
                # Fallback to DB
                details = database.get_course_details(course_code)
                if details and details.get("last_name"):
                    bubble = create_course_flex_bubble(
                        course_code, details["last_name"], details.get("last_teacher", "未知"),
                        details.get("last_time", "無"), details.get("last_classroom", "無"),
                        details.get("last_quota", 0), details.get("last_max_quota", 0)
                    )
                else:
                    bubble = create_course_flex_bubble(
                        course_code, "未知課程", "未知", "無", "無", 0, 0, error="無法取得即時資料，但系統仍會持續為您監控！"
                    )
                flex_msg = {
                    "type": "flex",
                    "altText": f"成功監控課程 {course_code}",
                    "contents": bubble
                }
                send_reply_message(reply_token, [flex_msg])
        except Exception as e:
            print(f"Error checking course on subscription: {e}")
            bubble = create_course_flex_bubble(
                course_code, "未知課程", "未知", "無", "無", 0, 0, error="無法取得即時資料，但系統仍會持續為您監控！"
            )
            flex_msg = {
                "type": "flex",
                "altText": f"成功監控課程 {course_code}",
                "contents": bubble
            }
            send_reply_message(reply_token, [flex_msg])
        
    elif action == "unsubscribe":
        database.unsubscribe_course(user_id, course_code)
        msg = {
            "type": "text",
            "text": f"OK！已將課號 {course_code} 自您的監控清單中移除 🗑️"
        }
        send_reply_message(reply_token, [msg])

async def process_events(events: list):
    """
    Parse events payload from webhook.
    """
    for event in events:
        event_type = event.get("type")
        source = event.get("source", {})
        user_id = source.get("userId")
        reply_token = event.get("replyToken")
        
        if not user_id or not reply_token:
            continue
            
        if event_type == "follow":
            # Welcome Message
            msg = {
                "type": "text",
                "text": "哈囉！歡迎使用海大搶課名額監控通知機器人🤖\n\n請直接輸入您要監控的『課號』（4到12碼英數混合），我就會為您定時巡邏！\n\n💡 範例：輸入 B33035PR\n💡 隨時輸入「清單」可查詢您訂閱的所有課程。"
            }
            send_reply_message(reply_token, [msg])
            
        elif event_type == "message":
            msg_obj = event.get("message", {})
            msg_type = msg_obj.get("type")
            if msg_type == "text":
                text = msg_obj.get("text")
                await handle_text_message(user_id, text, reply_token)
                
        elif event_type == "postback":
            postback_obj = event.get("postback", {})
            data = postback_obj.get("data")
            await handle_postback(user_id, data, reply_token)
