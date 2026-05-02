from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash
from flask_login import current_user, login_required

from . import db
from .ai_assistant import generate_assistant_reply, get_chat_config, markdown_to_safe_html, clamp_text
from .models import ChatMessage

chat_bp = Blueprint("chat", __name__, url_prefix="/assistant")


@chat_bp.route("/")
@login_required
def assistant():
    messages = (
        ChatMessage.query.filter_by(user_id=current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(60)
        .all()
    )
    messages.reverse()
    rendered_messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "html": markdown_to_safe_html(msg.content),
            "created_at": msg.created_at,
        }
        for msg in messages
    ]
    return render_template("assistant.html", messages=rendered_messages, chat_config=get_chat_config())


@chat_bp.route("/api", methods=["POST"])
@login_required
def assistant_api():
    payload = request.get_json(silent=True) or {}
    user_message = clamp_text(payload.get("message", ""), get_chat_config()["input_max_chars"])
    if not user_message:
        return jsonify({"ok": False, "error": "Message is required."}), 400

    result = generate_assistant_reply(current_user.id, user_message)

    user_row = ChatMessage(user_id=current_user.id, role="user", content=user_message)
    bot_row = ChatMessage(user_id=current_user.id, role="assistant", content=result["markdown"])
    db.session.add(user_row)
    db.session.add(bot_row)
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "user": {
                "role": "user",
                "content": user_row.content,
                "html": markdown_to_safe_html(user_row.content),
            },
            "assistant": {
                "role": "assistant",
                "content": bot_row.content,
                "html": result["html"],
                "model": result["model"],
                "live": result["live"],
            },
        }
    )


@chat_bp.route("/clear", methods=["POST"])
@login_required
def clear_chat():
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("AI chat history cleared.", "info")
    return redirect(url_for("chat.assistant"))
