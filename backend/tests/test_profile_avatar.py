import io

import pytest
from PIL import Image

from app.api.routes.profile import AVATAR_SIZE, _prepare_avatar_image
from app.core.exceptions import BadRequestException
from app.models.user import User


def test_prepare_avatar_resizes_and_strips_to_jpeg():
    source = io.BytesIO()
    Image.new("RGBA", (1200, 800), (20, 120, 220, 128)).save(source, format="PNG")

    normalized = _prepare_avatar_image(source.getvalue())

    with Image.open(io.BytesIO(normalized)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.width <= AVATAR_SIZE[0]
        assert image.height <= AVATAR_SIZE[1]


def test_prepare_avatar_rejects_non_image_bytes():
    with pytest.raises(BadRequestException, match="không hợp lệ"):
        _prepare_avatar_image(b"this is not an image")


def test_user_model_exposes_nullable_avatar_url():
    assert User.__table__.columns["avatar_url"].nullable is True
