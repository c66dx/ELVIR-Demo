import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config import settings
from app.services.liveavatar import LiveAvatarError, start_liveavatar_session


class LiveAvatarServiceTestCase(unittest.TestCase):
    def _base_entities(self):
        job_role = SimpleNamespace(
            name="Operario",
            description="Desc",
            objetivo="Obj",
            competencias='["Puntualidad"]',
        )
        case = SimpleNamespace(prompt_instructions="Instrucciones", opening_text="Hola")
        template = SimpleNamespace(
            liveavatar_context_id="ctx-1",
            liveavatar_avatar_id="avatar-1",
            liveavatar_voice_id="voice-1",
        )
        return job_role, case, template

    def test_patch_error_includes_provider_detail(self):
        job_role, case, template = self._base_entities()
        original = (
            settings.LIVEAVATAR_API_KEY,
            settings.LIVEAVATAR_CONTEXT_ID,
            settings.LIVEAVATAR_AVATAR_ID,
            settings.LIVEAVATAR_VOICE_ID,
            settings.LIVEAVATAR_API_BASE,
        )
        try:
            settings.LIVEAVATAR_API_KEY = "k"
            settings.LIVEAVATAR_CONTEXT_ID = "ctx-env"
            settings.LIVEAVATAR_AVATAR_ID = "avatar-env"
            settings.LIVEAVATAR_VOICE_ID = "voice-env"
            settings.LIVEAVATAR_API_BASE = "https://api.example.test/v1"

            patch_resp = SimpleNamespace(
                status_code=422,
                text='{"message":"prompt inválido"}',
                json=lambda: {"message": "prompt inválido"},
            )
            mock_client = MagicMock()
            mock_httpx_cm = MagicMock()
            mock_httpx_cm.__enter__.return_value = mock_client
            mock_httpx_cm.__exit__.return_value = False

            with patch("app.services.liveavatar.get_prompt", return_value=SimpleNamespace(prompt="PROMPT", opening_text=None, name=None)),                 patch("app.services.liveavatar._patch_context", return_value=patch_resp),                 patch("app.services.liveavatar.httpx.Client", return_value=mock_httpx_cm):
                with self.assertRaises(LiveAvatarError) as ctx:
                    start_liveavatar_session(job_role, case, template)

            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("prompt inválido", ctx.exception.message)
            mock_client.post.assert_not_called()
        finally:
            (
                settings.LIVEAVATAR_API_KEY,
                settings.LIVEAVATAR_CONTEXT_ID,
                settings.LIVEAVATAR_AVATAR_ID,
                settings.LIVEAVATAR_VOICE_ID,
                settings.LIVEAVATAR_API_BASE,
            ) = original


if __name__ == "__main__":
    unittest.main()
