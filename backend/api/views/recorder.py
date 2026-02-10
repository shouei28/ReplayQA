"""
Recorder API views. Business logic lives in services.recorder.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication

from services.recorder import (
    start_session,
    end_session,
    get_live_view_url,
    start_recording,
    get_recorded_actions,
    toggle_recording,
)
from services.recorder import state


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """SessionAuthentication that skips CSRF checks for these API endpoints."""

    def enforce_csrf(self, request):
        return  # Skip CSRF validation


class RecorderStartView(APIView):
    """Start a recorder session with Browserbase."""
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        try:
            url = request.data.get("url")
            if not url:
                return Response({"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST)
            device = request.data.get("device", "desktop")
            browser = request.data.get("browser", "chrome")
            data = start_session(url=url, device=device, browser=browser)
            return Response(data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
    Save a recorder test: summarise steps (Gemini) for description, then create Job.
    Summarization is an internal step of the save process.
    """
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workspace_user = getattr(request.user, "workspace_profile", None)
        if not workspace_user:
            return Response({"detail": "WorkspaceUser not found"}, status=404)

        data = request.data
        name = (data.get("name") or "").strip()
        expected_behavior = (data.get("expected_behavior") or "").strip()
        url = (data.get("url") or "").strip()
        stagehand_steps = data.get("steps", data.get("stagehand_steps", []))
        if not isinstance(stagehand_steps, list):
            stagehand_steps = []

        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not expected_behavior:
            return Response({"error": "expected_behavior is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not url:
            return Response({"error": "url is required"}, status=status.HTTP_400_BAD_REQUEST)
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
        steps_text = steps_to_text(stagehand_steps)

        devices = data.get("devices", ["desktop"])
        browsers = data.get("browsers", ["chrome"])

        # Optional credentials (for login steps); encode for storage
        username_encrypted = None
        password_encrypted = None
        if data.get("username"):
            raw = data["username"]
            if isinstance(raw, str):
                username_encrypted = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
            else:
                username_encrypted = raw
        if data.get("password"):
            raw = data["password"]
            if isinstance(raw, str):
                password_encrypted = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
            else:
                password_encrypted = raw

        project = None
        project_id = data.get("project_id")
        if project_id is not None:
            try:
                project = Project.objects.get(id=project_id, user=workspace_user)
            except Project.DoesNotExist:
                pass

        job = Job.objects.create(
            user=workspace_user,
            name=name,
            description=description or name,
            url=url,
            task=name,
            steps=steps_text,
            expected_behavior=expected_behavior,
            devices=devices,
            browsers=browsers,
            stagehand_steps=stagehand_steps,
            project=project,
            username=username_encrypted,
            password=password_encrypted,
        )

        return Response(
            {
                "id": str(job.id),
                "name": job.name,
                "description": job.description,
                "url": job.url,
                "task": job.task,
                "steps": job.steps,
                "expected_behavior": job.expected_behavior,
                "devices": job.devices,
                "browsers": job.browsers,
                "stagehand_steps": job.stagehand_steps or [],
                "username": job.username,
                "password": job.password,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )

