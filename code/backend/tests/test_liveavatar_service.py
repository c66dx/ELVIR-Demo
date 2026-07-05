import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config import settings
from app.services.liveavatar import LiveAvatarError, describe_liveavatar_config_gaps, start_liveavatar_session


class LiveAvatarServiceTestCase(unittest.TestCase):
    def test_describe_config_gaps_lists_missing_parts(self):
        template = SimpleNamespace(
            liveavatar_context_id="ctx-elvir-dinamico",
            liveavatar_avatar_id="avatar-default",
            liveavatar_voice_id="voice-default",
        )
        original = (
            settings.LIVEAVATAR_API_KEY,
            settings.LIVEAVATAR_CONTEXT_ID,
            settings.LIVEAVATAR_AVATAR_ID,
            settings.LIVEAVATAR_VOICE_ID,
        )
        try:
            settings.LIVEAVATAR_API_KEY = ""
            settings.LIVEAVATAR_CONTEXT_ID = ""
            settings.LIVEAVATAR_AVATAR_ID = ""
            settings.LIVEAVATAR_VOICE_ID = ""
            text = describe_liveavatar_config_gaps(template)
            self.assertIn("LIVEAVATAR_API_KEY", text)
            self.assertIn("marcador de demo", text.lower())
        finally:
            (
                settings.LIVEAVATAR_API_KEY,
                settings.LIVEAVATAR_CONTEXT_ID,
                settings.LIVEAVATAR_AVATAR_ID,
                settings.LIVEAVATAR_VOICE_ID,
            ) = original

    def _base_entities(self):
        job_role = SimpleNamespace(
            slug="operario",
            name="Operario",
            description="Desc",
            objetivo="Obj",
            competencias='["Puntualidad"]',
        )
        case = SimpleNamespace(slug="normal", prompt_instructions="Instrucciones", opening_text="Hola")
        template = SimpleNamespace(
            liveavatar_context_id="ctx-1",
            liveavatar_avatar_id="avatar-1",
            liveavatar_voice_id="voice-1",
        )
        return job_role, case, template

    def test_token_request_uses_configured_language(self):
        job_role, case, template = self._base_entities()
        original = (
            settings.LIVEAVATAR_API_KEY,
            settings.LIVEAVATAR_CONTEXT_ID,
            settings.LIVEAVATAR_AVATAR_ID,
            settings.LIVEAVATAR_VOICE_ID,
            settings.LIVEAVATAR_API_BASE,
            settings.LIVEAVATAR_LANGUAGE,
        )
        try:
            settings.LIVEAVATAR_API_KEY = "k"
            settings.LIVEAVATAR_CONTEXT_ID = "ctx-env"
            settings.LIVEAVATAR_AVATAR_ID = "avatar-env"
            settings.LIVEAVATAR_VOICE_ID = "voice-env"
            settings.LIVEAVATAR_API_BASE = "https://api.example.test/v1"
            settings.LIVEAVATAR_LANGUAGE = "en"

            token_resp = SimpleNamespace(
                status_code=200,
                json=lambda: {"data": {"session_token": "tok-1"}},
            )
            start_resp = SimpleNamespace(
                status_code=200,
                json=lambda: {
                    "data": {
                        "livekit_url": "wss://lk.example",
                        "livekit_client_token": "lk-1",
                    }
                },
            )
            mock_client = MagicMock()
            mock_client.post.side_effect = [token_resp, start_resp]
            mock_httpx_cm = MagicMock()
            mock_httpx_cm.__enter__.return_value = mock_client
            mock_httpx_cm.__exit__.return_value = False

            with patch("app.services.liveavatar.httpx.Client", return_value=mock_httpx_cm):
                start_liveavatar_session(job_role, case, template)

            token_call = mock_client.post.call_args_list[0]
            self.assertEqual(
                token_call.kwargs["json"]["avatar_persona"]["language"],
                "en",
            )
        finally:
            (
                settings.LIVEAVATAR_API_KEY,
                settings.LIVEAVATAR_CONTEXT_ID,
                settings.LIVEAVATAR_AVATAR_ID,
                settings.LIVEAVATAR_VOICE_ID,
                settings.LIVEAVATAR_API_BASE,
                settings.LIVEAVATAR_LANGUAGE,
            ) = original

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

            mock_client.post.return_value = patch_resp

            with patch("app.services.liveavatar.httpx.Client", return_value=mock_httpx_cm):
                with self.assertRaises(LiveAvatarError) as ctx:
                    start_liveavatar_session(job_role, case, template)

            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("prompt inválido", ctx.exception.message)
            mock_client.post.assert_called_once()
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
