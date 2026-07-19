"""WebRTC 信令端点。

仅承担「撮合两个已登录浏览器建立 WebRTC 连接」的职责 —— 交换 SDP（offer/answer），
不转发任何业务/文件数据。文件经 DataChannel 在两个浏览器之间直连传输。

设计要点：
- 鉴权用「首帧 auth」而非 query token，避免 JWT 进入 nginx access log / 浏览器历史。
- 采用非 trickle ICE：offer / answer 各自裹好完整候选再发，因此**无需 candidate 中继**。
- 邀请码一次性：发起方 A 生成 offer → 服务端存 code→offer；接收方 B 凭码取 offer。
  B 输码即视为同意接收，杜绝被陌生人随意发起连接。
"""
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import select

from app.database import async_session_factory
from app.models.user import User
from app.utils.security import verify_token

router = APIRouter(prefix="/api/rtc")

# 在线用户：user_id -> {"ws": WebSocket, "username": str}
online: dict[int, dict] = {}
# 邀请码 -> {"from": user_id, "username": str, "offer": sdp}
invites: dict[str, dict] = {}

CODE_TTL_SECONDS = 120


async def _resolve_user(uid: int) -> User | None:
    async with async_session_factory() as db:
        res = await db.execute(select(User).where(User.id == uid))
        return res.scalar_one_or_none()


async def _broadcast_presence() -> None:
    payload = {
        "type": "presence",
        "users": [{"id": uid, "username": info["username"]} for uid, info in online.items()],
    }
    for info in list(online.values()):
        try:
            await info["ws"].send_json(payload)
        except Exception:
            # 单个连接发送失败不应影响其他人
            pass


def _gen_code() -> str:
    # 6 位大写字母数字，易口头转述；碰撞概率极低，且 invite 即用即弃
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 去掉易混淆字符
    return "".join(secrets.choice(alphabet) for _ in range(6))


@router.websocket("/signal")
async def signal(ws: WebSocket) -> None:
    # 先接受底层连接，再等第一帧做鉴权（避免 token 出现在 URL/日志里）
    await ws.accept()
    try:
        first = await ws.receive_json()
    except Exception:
        await ws.close(code=4400)
        return

    token = first.get("token") if isinstance(first, dict) else None
    try:
        payload = verify_token(token)
        assert payload.get("type") == "access"
        uid = int(payload["sub"])
    except (JWTError, AssertionError, TypeError, ValueError):
        await ws.send_json({"type": "auth_failed"})
        await ws.close(code=4401)
        return

    user = await _resolve_user(uid)
    if user is None:
        await ws.send_json({"type": "auth_failed"})
        await ws.close(code=4401)
        return

    online[uid] = {"ws": ws, "username": user.username}
    await ws.send_json({"type": "auth_ok", "me": {"id": uid, "username": user.username}})
    await _broadcast_presence()

    try:
        while True:
            msg = await ws.receive_json()
            t = msg.get("type")

            if t == "invite_create":
                code = _gen_code()
                invites[code] = {
                    "from": uid,
                    "username": user.username,
                    "offer": msg.get("offer"),
                }
                await ws.send_json({"type": "invite_created", "code": code})

            elif t == "invite_join":
                rec = invites.pop(msg.get("code"), None)
                if rec:
                    await ws.send_json({
                        "type": "offer",
                        "from": rec["from"],
                        "username": rec["username"],
                        "offer": rec["offer"],
                    })
                else:
                    await ws.send_json({"type": "invite_not_found"})

            elif t == "answer":
                target = online.get(int(msg.get("to", 0)))
                if target:
                    await target["ws"].send_json({
                        "type": "answer",
                        "from": uid,
                        "username": user.username,
                        "answer": msg.get("answer"),
                    })
                else:
                    await ws.send_json({"type": "peer_unavailable"})

            # 注：非 trickle 模式，无需处理 candidate 转发。
    except WebSocketDisconnect:
        pass
    finally:
        online.pop(uid, None)
        await _broadcast_presence()
