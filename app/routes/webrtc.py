"""WebRTC signaling routes for browser video streaming."""

from __future__ import annotations

import logging
from typing import Set

from aiortc import RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.webrtc_camera import CameraStreamTrack


logger = logging.getLogger(__name__)
router = APIRouter()
pcs: Set[RTCPeerConnection] = set()


class OfferPayload(BaseModel):
    sdp: str
    type: str


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

        @channel.on("message")
        def on_message(message) -> None:
            if message == "ping":
                channel.send("pong")

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
