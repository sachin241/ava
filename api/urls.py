from django.urls import path

from .views import command, complete_response, detect, emergency, health, read, repeat_response, stop_response, transcribe

urlpatterns = [
    path("health/", health, name="health"),
    path("vision/detect/", detect, name="detect"),
    path("response/complete/", complete_response, name="response-complete"),
    path("response/stop/", stop_response, name="response-stop"),
    path("response/repeat/", repeat_response, name="response-repeat"),
    path("emergency/", emergency, name="emergency"),
    path("interaction/read/", read, name="read"),
    path("interaction/transcribe/", transcribe, name="transcribe"),
    path("interaction/command/", command, name="command"),
]
