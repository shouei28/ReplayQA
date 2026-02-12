"""
Recorder API views. Business logic lives in services.recorder.
Saving a test uses core.models.Test (single test table).
"""

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Test
from services.recorder import (
    end_session, get_live_view_url, get_recorded_actions, start_recording,
    start_session, state, summarize_steps, toggle_recording,
)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """SessionAuthentication that skips CSRF checks for these API endpoints."""

    def enforce_csrf(self, request):
        return  # Skip CSRF validation


class RecorderStartView(APIView):
    """Start a recorder session with Browserbase."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            url = request.data.get("url")
            if not url:
                return Response(
                    {"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST
                )
            device = request.data.get("device", "desktop")
            browser = request.data.get("browser", "chrome")
            data = start_session(url=url, device=device, browser=browser)
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except (RuntimeError, Exception) as e:
            import traceback

            print(f"[RECORDER ERROR] Failed to start recorder session: {e}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to start recorder session: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecorderLiveViewView(APIView):
    """Get live view URL for recorder session."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, session_id: str):
        try:
            browserbase_session_id = request.query_params.get("browserbase_session_id")
            if not browserbase_session_id:
                return Response(
                    {"error": "browserbase_session_id query parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            live_view_url = get_live_view_url(browserbase_session_id)
            return Response({"live_view_url": live_view_url})
        except Exception as e:
            import traceback

            print(f"[RECORDER ERROR] Failed to get live view URL: {e}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to get live view URL: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecorderStartRecordingView(APIView):
    """Start recording user interactions in the browser."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, session_id: str):
        try:
            browserbase_session_id = request.data.get("browserbase_session_id")
            if not browserbase_session_id:
                return Response(
                    {"error": "browserbase_session_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            connect_url = request.data.get("connect_url")
            device = request.data.get("device", "desktop")
            slot_browser = request.data.get("browser", "chrome")
            initial_url = request.data.get("url")
            start_recording(
                session_id=session_id,
                browserbase_session_id=browserbase_session_id,
                connect_url=connect_url,
                device=device,
                slot_browser=slot_browser,
                initial_url=initial_url,
            )
            return Response({"success": True, "message": "Recording started"})
        except Exception as e:
            import traceback

            print(f"[RECORDER ERROR] Failed to start recording: {e}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to start recording: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecorderToggleRecordingView(APIView):
    """Toggle recording on/off."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, session_id: str):
        try:
            enabled = request.data.get("enabled", True)
            result = toggle_recording(session_id, enabled)
            if "error" in result:
                return Response(
                    {"error": result["error"]},
                    status=result.get("status", status.HTTP_404_NOT_FOUND),
                )
            return Response(result)
        except Exception as e:
            import traceback

            print(f"[RECORDER ERROR] Failed to toggle recording: {e}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to toggle recording: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecorderGetRecordedActionsView(APIView):
    """Get recorded actions from the queue."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, session_id: str):
        try:
            result = get_recorded_actions(session_id)
            return Response(result)
        except Exception as e:
            import traceback

            print(f"[RECORDER ERROR] Failed to get recorded actions: {e}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to get recorded actions: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecorderEndView(APIView):
    """End a recorder session."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, session_id: str):
        try:
            browserbase_session_id = request.data.get("browserbase_session_id")
            device = request.data.get("device", "desktop")
            browser = request.data.get("browser", "chrome")
            end_session(
                session_id=session_id,
                browserbase_session_id=browserbase_session_id,
                device=device,
                browser=browser,
            )
            return Response({"success": True, "message": "Session ended successfully"})
        except Exception as e:
            import traceback

            print(f"[RECORDER ERROR] Failed to end session: {e}")
            print(traceback.format_exc())
            return Response(
                {"error": f"Failed to end session: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecorderSaveTestView(APIView):
    """
    Save a recorded test into core.Test (single test table).
    Uses summarize_steps (Gemini) for description; steps stored as JSON.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = request.data
        name = (data.get("name") or "").strip()
        expected_behavior = (data.get("expected_behavior") or "").strip()
        url = (data.get("url") or "").strip()
        stagehand_steps = data.get("steps", data.get("stagehand_steps", []))
        if not isinstance(stagehand_steps, list):
            stagehand_steps = []

        if not name:
            return Response(
                {"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not expected_behavior:
            return Response(
                {"error": "expected_behavior is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not url:
            return Response(
                {"error": "url is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(stagehand_steps) < 1:
            return Response(
                {"error": "At least one step is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        description = summarize_steps(
            steps=stagehand_steps,
            url=url,
            expected_behavior=expected_behavior,
        )

        test = Test.objects.create(
            user=request.user,
            test_name=name,
            description=description or name,
            url=url,
            steps=stagehand_steps,
            expected_behavior=expected_behavior,
        )

        return Response(
            {
                "id": str(test.id),
                "test_name": test.test_name,
                "description": test.description,
                "url": test.url,
                "steps": test.steps,
                "expected_behavior": test.expected_behavior,
                "created_at": test.created_at.isoformat(),
                "updated_at": test.updated_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )
