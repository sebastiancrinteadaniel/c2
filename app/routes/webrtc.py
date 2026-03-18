"""WebRTC signaling routes for browser video streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from aiortc import RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.healthcare_verification import get_healthcare_session
from app.services.system_metrics import get_system_metrics
from app.services.webrtc_camera import CameraStreamTrack


logger = logging.getLogger(__name__)
router = APIRouter()
pcs: Set[RTCPeerConnection] = set()


class OfferPayload(BaseModel):
    sdp: str
    type: str
    page: str | None = None


@router.post("/offer")
async def offer(payload: OfferPayload):
    """Negotiate a WebRTC connection and return SDP answer."""
    try:
        remote_offer = RTCSessionDescription(sdp=payload.sdp, type=payload.type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid WebRTC offer payload") from exc

    pc = RTCPeerConnection()
    pcs.add(pc)
    camera_track = CameraStreamTrack()
    pc.addTrack(camera_track)
    is_healthcare_page = (payload.page or "").strip().lower() == "healthcare"

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        logger.info("[webrtc] connection state -> %s", pc.connectionState)
        if pc.connectionState in {"failed", "closed", "disconnected"}:
            camera_track.stop()
            pcs.discard(pc)
            await pc.close()

    @pc.on("datachannel")
    def on_datachannel(channel) -> None:
        logger.info("[webrtc] datachannel opened: %s", channel.label)

        async def push_stats() -> None:
            while True:
                if pc.connectionState in {"failed", "closed", "disconnected"}:
                    break

                if channel.readyState == "open":
                    stats = get_system_metrics()
                    payload = {
                        "type": "stats",
                        "cpu_percent": stats.get("cpu_percent"),
                        "ram_percent": stats.get("ram_percent"),
                        "uptime_seconds": stats.get("uptime_seconds"),
                        "fps": getattr(camera_track, "current_fps", 0.0),
                        "detections": getattr(camera_track, "latest_detections", []),
                        "detector_ready": getattr(camera_track.yolo_processor, "ready", False),
                        "detector_status": getattr(camera_track.yolo_processor, "status_message", "unknown"),
                    }
                    if is_healthcare_page:
                        payload["healthcare"] = get_healthcare_session().snapshot()
                    try:
                        channel.send(json.dumps(payload))
                    except Exception:
                        break

                if channel.readyState == "closed":
                    break

                await asyncio.sleep(1)

        stats_task = asyncio.create_task(push_stats())

        @channel.on("close")
        def on_close() -> None:
            if not stats_task.done():
                stats_task.cancel()

        @channel.on("message")
        def on_message(message) -> None:
            if message == "ping":
                channel.send("pong")
                return

    await pc.setRemoteDescription(remote_offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }


async def close_all_peer_connections() -> None:
    """Close all active peer connections."""
    for pc in list(pcs):
        await pc.close()
        pcs.discard(pc)
