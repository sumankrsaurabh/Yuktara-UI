import pytest

from novaui.native.platform.sdl3 import PixelFrame, SDLEvent, SDL_EVENT_QUIT


def test_pixel_frame_accepts_tightly_packed_rgba():
    frame = PixelFrame(2, 2, bytes(16))
    assert frame.row_bytes == 8


def test_pixel_frame_accepts_padded_rows():
    frame = PixelFrame(1, 2, bytes(12), row_bytes=6)
    assert frame.row_bytes == 6


@pytest.mark.parametrize(
    "width,height,pixels,row_bytes",
    [
        (0, 1, b"", None),
        (1, 1, b"abc", None),
        (2, 1, bytes(8), 7),
        (1, 2, bytes(7), 4),
    ],
)
def test_pixel_frame_rejects_invalid_buffers(width, height, pixels, row_bytes):
    with pytest.raises(ValueError):
        PixelFrame(width, height, pixels, row_bytes)


def test_quit_event_model():
    event = SDLEvent(SDL_EVENT_QUIT, quit_requested=True)
    assert event.quit_requested
