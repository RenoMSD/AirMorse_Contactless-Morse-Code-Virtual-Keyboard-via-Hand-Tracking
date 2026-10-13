import threading

from airmorse.vision.frames import FramePacket, LatestFrame


def test_coalesce_keeps_tokens_from_dropped_frames():
    hub = LatestFrame()
    assert hub.publish(FramePacket(token_times=[(8, 1.0)], fps=1)) is True
    assert hub.publish(FramePacket(token_times=[(12, 2.0)], fps=2)) is False
    packet = hub.take()
    assert packet is not None
    assert packet.token_times == [(8, 1.0), (12, 2.0)]
    assert packet.fps == 2
    assert hub.take() is None
    assert hub.publish(FramePacket(fps=3)) is True


def test_token_queue_is_bounded():
    hub = LatestFrame()
    first = FramePacket(token_times=[(8, float(i)) for i in range(30)])
    second = FramePacket(token_times=[(12, float(i)) for i in range(30, 40)], fps=3)
    hub.publish(first)
    hub.publish(second)
    packet = hub.take()
    assert packet is not None
    assert len(packet.token_times) == 32
    assert packet.token_times[0] == (8, 8.0)
    assert packet.token_times[-1] == (12, 39.0)


def test_publish_from_two_threads_keeps_a_bounded_queue():
    hub = LatestFrame()

    def push(start: float) -> None:
        for offset in range(50):
            hub.publish(FramePacket(token_times=[(8, start + offset)]))

    left = threading.Thread(target=push, args=(0,))
    right = threading.Thread(target=push, args=(1000,))
    left.start()
    right.start()
    left.join()
    right.join()
    packet = hub.take()
    assert packet is not None
    assert len(packet.token_times) == 32
