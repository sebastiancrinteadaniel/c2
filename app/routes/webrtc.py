import asyncio
import logging

from aiortc import RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.camera import get_camera_track
from app.config.camera import get_camera_settings
from app.services.detector import get_detector
from app.services.system_metrics import get_system_metrics

import json

router = APIRouter()
logger = logging.getLogger(__name__)
_peer_connections: set[RTCPeerConnection] = set()


class OfferBody(BaseModel):
    sdp: str
    type: str


@router.post("/api/offer")
async def handle_offer(body: OfferBody):
    offer = RTCSessionDescription(sdp=body.sdp, type=body.type)

    pc = RTCPeerConnection()
    _peer_connections.add(pc)

    @pc.on("connectionstatechange")
    async def on_state_change():
        state = pc.connectionState
        logger.info("[webrtc] Connection state -> %s", state)
        if state in ("failed", "closed", "disconnected"):
            await pc.close()
            _peer_connections.discard(pc)

    @pc.on("datachannel")
    def on_datachannel(channel):
        if channel.label == "detections":
            logger.info("[webrtc] Detection DataChannel opened")
            task = asyncio.create_task(_send_detections(channel))

            @channel.on("close")
            def on_close():
                logger.info("[webrtc] Detection DataChannel closed")
                task.cancel()

    camera = get_camera_track()
    pc.addTrack(camera)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    await _wait_for_ice(pc)
    patched_sdp = _inject_bandwidth(
        pc.localDescription.sdp,
        kbps=get_camera_settings().webrtc_video_kbps,
    )

    return {
        "sdp": patched_sdp,
        "type": pc.localDescription.type,
    }


def _inject_bandwidth(sdp: str, kbps: int) -> str:
    """
    Insert  b=AS:<kbps>  into every video m-section of an SDP string.
    This hints to the encoder that it can use up to <kbps> kbps - critical
    for getting decent quality on LAN where bandwidth is not the bottleneck.
    """
    lines = sdp.splitlines()
    patched: list[str] = []
    in_video = False
    bw_written = False

    for line in lines:
        if line.startswith("m=video"):
            in_video = True
            bw_written = False
            patched.append(line)
            continue
        elif line.startswith("m="):
            in_video = False
        if in_video and not bw_written and line.startswith("c="):
            patched.append(line)
            patched.append(f"b=AS:{kbps}")
            bw_written = True
            continue

        patched.append(line)

    return "\r\n".join(patched) + "\r\n"


async def _wait_for_ice(pc: RTCPeerConnection, timeout: float = 5.0) -> None:
    """Wait until ICE gathering is complete or timeout elapses."""
    loop = asyncio.get_event_loop()
    done = loop.create_future()

    @pc.on("icegatheringstatechange")
    def on_ice_gathering():
        if pc.iceGatheringState == "complete" and not done.done():
            done.set_result(None)

    if pc.iceGatheringState == "complete":
        return

    try:
        await asyncio.wait_for(done, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("[webrtc] ICE gathering timed out - sending partial candidates")


async def _send_detections(channel) -> None:
    """Polls the detector and sends results over the DataChannel."""
    last_metrics_push = 0.0
    while channel.readyState == "open":
        now = asyncio.get_running_loop().time()

        if now - last_metrics_push >= 5.0:
            try:
                channel.send(json.dumps({"system_metrics": get_system_metrics()}))
            except Exception:
                logger.exception("[webrtc] Metrics DataChannel send error")
            last_metrics_push = now

        dets = get_detector().latest_detections
        if dets:
            try:
                channel.send(json.dumps({"detections": dets}))
            except Exception:
                logger.exception("[webrtc] DataChannel send error")
        await asyncio.sleep(0.1)


async def close_all_connections() -> None:
    """Close all open peer connections (called on app shutdown)."""
    coros = [pc.close() for pc in _peer_connections]
    await asyncio.gather(*coros, return_exceptions=True)
    _peer_connections.clear()
